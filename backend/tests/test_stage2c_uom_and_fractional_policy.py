"""Stage 2C focused tests for UoM conversion rollovers and fractional quantity policy."""

from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.routes.categories import get_audit_service
from app.api.routes.products import (
    get_fractional_policy_checker,
    get_inventory_initializer,
)
from app.db.session import get_db
from app.main import app
from app.models.uom_conversion import UomConversion
from app.schemas.product import ProductCreate, ProductUpdate, UomConversionCreate
from app.services.product_service import (
    ProductConflictError,
    ProductValidationError,
    product_service,
)
from tests.test_stage2b_product_management import (
    FakeAuditService,
    FakeFractionalChecker,
    FakeInventoryInitializer,
    sqlite_session_factory,  # noqa: F401
)


def test_uom_validation_zero_negative_and_excess_precision_rejected(sqlite_session_factory):
    inv = FakeInventoryInitializer()
    audit = FakeAuditService()

    def override_db():
        db = sqlite_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_inventory_initializer] = lambda: inv
    app.dependency_overrides[get_audit_service] = lambda: audit
    try:
        client = TestClient(app)
        prod = client.post(
            "/api/v1/products",
            json={"stock_code": "UOM-VAL-1", "description": "Olive Oil", "base_uom": "liter"},
        ).json()
        pid = prod["id"]

        for bad_factor in ("0", "0.000000", "-1.500000", "1.1234567"):
            resp = client.post(
                f"/api/v1/products/{pid}/uom-conversions",
                json={"uom_code": "drum", "conversion_to_base": bad_factor},
            )
            assert resp.status_code == 422, f"Expected 422 for factor={bad_factor}"
    finally:
        app.dependency_overrides.clear()


def test_uom_rollover_point_in_time_half_open_and_rollback_safety(sqlite_session_factory, monkeypatch):
    inv = FakeInventoryInitializer()
    audit_ok = FakeAuditService()

    with sqlite_session_factory() as db:
        prod = product_service.create_product(
            db,
            ProductCreate(
                stock_code="UOM-HIST-1",
                description="Cooking Oil",
                base_uom="liter",
                allow_fractional_qty=True,
            ),
            inventory_initializer=inv,
            audit_service=audit_ok,
        )
        pid = prod.id

        t1 = datetime(2026, 11, 27, 10, 0, 0)
        t2 = datetime(2026, 11, 27, 12, 0, 0)

        monkeypatch.setattr("app.services.product_service._capture_server_timestamp", lambda s, p: t1)
        c1 = product_service.rollover_uom_conversion(
            db,
            pid,
            UomConversionCreate(uom_code="can", conversion_to_base=Decimal("5.000000")),
            audit_service=audit_ok,
            idempotency_key="uom-key-1",
        )
        assert c1.is_active is True

        monkeypatch.setattr("app.services.product_service._capture_server_timestamp", lambda s, p: t2)
        c2 = product_service.rollover_uom_conversion(
            db,
            pid,
            UomConversionCreate(uom_code="can", conversion_to_base=Decimal("10.000000")),
            audit_service=audit_ok,
            idempotency_key="uom-key-2",
        )
        assert c2.is_active is True

        # Half-open [t1, t2) vs [t2, NULL) verification
        assert product_service.convert_product_quantity_to_base(
            db, pid, "2", uom_code="can", at_timestamp=t1
        ) == Decimal("10.0000")
        assert product_service.convert_product_quantity_to_base(
            db, pid, "2", uom_code="can", at_timestamp=t2 - timedelta(microseconds=1)
        ) == Decimal("10.0000")
        assert product_service.convert_product_quantity_to_base(
            db, pid, "2", uom_code="can", at_timestamp=t2
        ) == Decimal("20.0000")
        assert product_service.convert_product_quantity_to_base(
            db, pid, "2", uom_code="can"
        ) == Decimal("20.0000")

        # Duplicate idempotency_key -> 409 Conflict and prior active row c2 remains active!
        t3 = datetime(2026, 11, 27, 13, 0, 0)
        monkeypatch.setattr("app.services.product_service._capture_server_timestamp", lambda s, p: t3)
        with pytest.raises(ProductConflictError, match="Duplicate UoM rollover"):
            product_service.rollover_uom_conversion(
                db,
                pid,
                UomConversionCreate(uom_code="can", conversion_to_base=Decimal("15.000000")),
                audit_service=audit_ok,
                idempotency_key="uom-key-2",
            )

        # Tier 1 audit failure rolls back closing of c2 and creation of c3
        with pytest.raises(RuntimeError, match="Simulated Tier 1"):
            product_service.rollover_uom_conversion(
                db,
                pid,
                UomConversionCreate(uom_code="can", conversion_to_base=Decimal("15.000000")),
                audit_service=FakeAuditService(fail_tier1=True),
            )

        # Overlapping timestamp (< max(closed.effective_to) == t2) rejected with 409
        t_overlap = datetime(2026, 11, 27, 11, 0, 0)
        monkeypatch.setattr("app.services.product_service._capture_server_timestamp", lambda s, p: t_overlap)
        with pytest.raises(ProductConflictError, match="overlaps"):
            product_service.rollover_uom_conversion(
                db,
                pid,
                UomConversionCreate(uom_code="can", conversion_to_base=Decimal("15.000000")),
                audit_service=audit_ok,
            )

    with sqlite_session_factory() as db_verify:
        rows = list(
            db_verify.execute(
                select(UomConversion).where(UomConversion.product_id == pid).order_by(UomConversion.id.asc())
            ).scalars()
        )
        assert len(rows) == 2
        assert rows[0].is_active is False and rows[0].effective_to == t2
        assert rows[1].is_active is True and rows[1].effective_from == t2 and rows[1].effective_to is None


def test_uom_concurrent_flush_integrity_error_maps_to_conflict(sqlite_session_factory, monkeypatch):
    inv = FakeInventoryInitializer()
    audit_ok = FakeAuditService()

    with sqlite_session_factory() as db:
        prod = product_service.create_product(
            db,
            ProductCreate(stock_code="UOM-RACE", description="Race Test", base_uom="unit"),
            inventory_initializer=inv,
            audit_service=audit_ok,
        )
        pid = prod.id

    with sqlite_session_factory() as db:
        orig_flush = db.flush
        calls = {"n": 0}

        def simulated_race_flush(*args, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise IntegrityError("INSERT", {}, Exception("Duplicate entry for uq_uom_one_active"))
            return orig_flush(*args, **kwargs)

        monkeypatch.setattr(db, "flush", simulated_race_flush)
        with pytest.raises(ProductConflictError, match="Concurrent UoM conversion conflict"):
            product_service.rollover_uom_conversion(
                db,
                pid,
                UomConversionCreate(uom_code="box", conversion_to_base=Decimal("12.000000")),
                audit_service=audit_ok,
            )


def test_product_level_fractional_validation_and_policy_transitions(sqlite_session_factory):
    inv = FakeInventoryInitializer()
    audit_ok = FakeAuditService()

    with sqlite_session_factory() as db:
        whole_prod = product_service.create_product(
            db,
            ProductCreate(stock_code="WHOLE-1", description="Laptop", allow_fractional_qty=False),
            inventory_initializer=inv,
            audit_service=audit_ok,
        )
        frac_prod = product_service.create_product(
            db,
            ProductCreate(stock_code="FRAC-2", description="Fabric", base_uom="meter", allow_fractional_qty=True),
            inventory_initializer=inv,
            audit_service=audit_ok,
        )
        frac_id = frac_prod.id
        product_service.rollover_uom_conversion(
            db,
            frac_id,
            UomConversionCreate(uom_code="bolt", conversion_to_base=Decimal("2.500000")),
            audit_service=audit_ok,
        )

        # Whole product validation
        assert product_service.validate_product_quantity(db, whole_prod.id, "3") == Decimal("3")
        with pytest.raises(ProductValidationError):
            product_service.validate_product_quantity(db, whole_prod.id, "1.5")

        # Fractional product bounds & conversion representability
        assert product_service.validate_product_quantity(db, frac_id, "0.0001") == Decimal("0.0001")
        assert product_service.validate_product_quantity(db, frac_id, "9999999999.9999") == Decimal(
            "9999999999.9999"
        )
        assert product_service.convert_product_quantity_to_base(
            db, frac_id, "0.2500", uom_code="bolt"
        ) == Decimal("0.6250")

        for invalid in ("0.00009", "1.12345", "10000000000"):
            with pytest.raises(ProductValidationError):
                product_service.validate_product_quantity(db, frac_id, invalid)

        # True -> False rejected when open commitments exist
        with pytest.raises(ProductConflictError, match="outstanding commitments"):
            product_service.update_product(
                db,
                frac_id,
                ProductUpdate(
                    description="Fabric",
                    allow_fractional_qty=False,
                    current_unit_price=Decimal("25.00"),
                ),
                audit_service=audit_ok,
                fractional_checker=FakeFractionalChecker(has_inv=False, has_commitments=True),
            )

        # True -> False rolled back cleanly if Tier 2 audit fails
        with pytest.raises(RuntimeError, match="Simulated Tier 2"):
            product_service.update_product(
                db,
                frac_id,
                ProductUpdate(
                    description="Fabric",
                    allow_fractional_qty=False,
                    current_unit_price=Decimal("25.00"),
                ),
                audit_service=FakeAuditService(fail_tier2=True),
                fractional_checker=FakeFractionalChecker(has_inv=False, has_commitments=False),
            )

    with sqlite_session_factory() as db_check:
        assert product_service.get_product(db_check, frac_id).allow_fractional_qty is True

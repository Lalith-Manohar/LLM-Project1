"""Stage 2C.1 focused tests for fractional-policy locking and narrowed IntegrityError handling."""

from decimal import Decimal
import pytest
from sqlalchemy import event
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.uom_conversion import UomConversion
from app.schemas.product import ProductCreate, ProductUpdate, UomConversionCreate
from app.services.contracts import FractionalPolicyCheckerProtocol
from app.services.product_service import (
    FractionalCheckerUnavailableError,
    ProductConflictError,
    _is_duplicate_key_integrity_error,
    product_service,
)
from tests.test_stage2b_product_management import (
    FakeAuditService,
    FakeFractionalChecker,
    FakeInventoryInitializer,
    sqlite_session_factory,  # noqa: F401
)


class _DriverError(Exception):
    """Minimal DBAPI error double with MySQL-style (errno, msg) args or sqlite_errorcode."""

    def __init__(self, *args, sqlite_errorcode: int | None = None):
        super().__init__(*args)
        if sqlite_errorcode is not None:
            self.sqlite_errorcode = sqlite_errorcode


def test_update_product_locks_product_before_checker_and_skips_lock_on_normal_updates(
    sqlite_session_factory,
):
    inv = FakeInventoryInitializer()
    audit_ok = FakeAuditService()

    with sqlite_session_factory() as db:
        prod = product_service.create_product(
            db,
            ProductCreate(
                stock_code="LOCK-1",
                description="Locked Fractional SKU",
                allow_fractional_qty=True,
                current_unit_price=Decimal("20.00"),
            ),
            inventory_initializer=inv,
            audit_service=audit_ok,
        )
        pid = prod.id

    events_order: list[str] = []

    class SpyChecker:
        def has_fractional_inventory_or_commitments(
            self, session: Session, *, product_id: int
        ) -> tuple[bool, bool]:
            assert session.in_transaction() is True
            events_order.append(f"checker:{product_id}")
            return False, False

    with sqlite_session_factory() as db:
        orig_execute = db.execute

        def spy_execute(statement, *args, **kwargs):
            compiled_mysql = str(statement.compile(dialect=mysql.dialect()))
            if "FOR UPDATE" in compiled_mysql and "FROM products" in compiled_mysql:
                events_order.append("lock_products_for_update")
            return orig_execute(statement, *args, **kwargs)

        db.execute = spy_execute  # type: ignore[method-assign]

        # 1. Disabling allow_fractional_qty MUST lock Product FOR UPDATE before calling checker
        updated = product_service.update_product(
            db,
            pid,
            ProductUpdate(
                description="Locked Fractional SKU",
                allow_fractional_qty=False,
                current_unit_price=Decimal("25.00"),
            ),
            audit_service=audit_ok,
            fractional_checker=SpyChecker(),
        )
        assert updated.allow_fractional_qty is False
        assert events_order == ["lock_products_for_update", f"checker:{pid}"]

        # 2. Ordinary update without allow_fractional_qty=False must NOT acquire FOR UPDATE lock
        events_order.clear()
        ordinary = product_service.update_product(
            db,
            pid,
            ProductUpdate(
                description="Ordinary Price Update",
                current_unit_price=Decimal("30.00"),
            ),
            audit_service=audit_ok,
        )
        assert ordinary.description == "Ordinary Price Update"
        assert events_order == []


def test_fractional_checker_failure_and_protocol_contract_preserved(sqlite_session_factory):
    inv = FakeInventoryInitializer()
    audit_ok = FakeAuditService()

    with sqlite_session_factory() as db:
        prod = product_service.create_product(
            db,
            ProductCreate(
                stock_code="LOCK-FAIL-1",
                description="Checker Failure SKU",
                allow_fractional_qty=True,
                current_unit_price=Decimal("15.00"),
            ),
            inventory_initializer=inv,
            audit_service=audit_ok,
        )
        pid = prod.id

    class FailingChecker:
        def has_fractional_inventory_or_commitments(
            self, session: Session, *, product_id: int
        ) -> tuple[bool, bool]:
            raise RuntimeError("M09 database check failed")

    with sqlite_session_factory() as db:
        with pytest.raises(RuntimeError, match="M09 database check failed"):
            product_service.update_product(
                db,
                pid,
                ProductUpdate(
                    description="Should Rollback",
                    allow_fractional_qty=False,
                    current_unit_price=Decimal("99.00"),
                ),
                audit_service=audit_ok,
                fractional_checker=FailingChecker(),
            )

        with pytest.raises(FractionalCheckerUnavailableError):
            product_service.update_product(
                db,
                pid,
                ProductUpdate(
                    description="Missing Checker",
                    allow_fractional_qty=False,
                    current_unit_price=Decimal("99.00"),
                ),
                audit_service=audit_ok,
                fractional_checker=None,
            )

        with pytest.raises(ProductConflictError):
            product_service.update_product(
                db,
                pid,
                ProductUpdate(
                    description="Conflicting Inventory",
                    allow_fractional_qty=False,
                    current_unit_price=Decimal("99.00"),
                ),
                audit_service=audit_ok,
                fractional_checker=FakeFractionalChecker(has_inv=True),
            )

    with sqlite_session_factory() as db_verify:
        refetched = product_service.get_product(db_verify, pid)
        assert refetched.allow_fractional_qty is True
        assert refetched.description == "Checker Failure SKU"

    doc = FractionalPolicyCheckerProtocol.__doc__ or ""
    assert "FOR UPDATE" in doc
    assert "parent-before-child" in doc


def test_duplicate_key_classifier_distinguishes_1062_from_other_integrity_errors():
    dup_mysql = IntegrityError("INSERT", {}, _DriverError(1062, "Duplicate entry for key 'uq_uom_one_active'"))
    assert _is_duplicate_key_integrity_error(dup_mysql, expected_constraints=("uq_uom_one_active",)) is True

    not_null_mysql = IntegrityError("INSERT", {}, _DriverError(1048, "Column 'uom_code' cannot be null"))
    check_mysql = IntegrityError("INSERT", {}, _DriverError(3819, "Check constraint 'chk_uom_factor_pos' is violated"))
    fk_mysql = IntegrityError("INSERT", {}, _DriverError(1452, "Cannot add or update a child row: a foreign key constraint fails"))
    assert _is_duplicate_key_integrity_error(not_null_mysql, expected_constraints=("uq_uom_one_active",)) is False
    assert _is_duplicate_key_integrity_error(check_mysql, expected_constraints=("uq_uom_one_active",)) is False
    assert _is_duplicate_key_integrity_error(fk_mysql, expected_constraints=("uq_uom_one_active",)) is False

    dup_sqlite = IntegrityError("INSERT", {}, _DriverError("UNIQUE constraint failed", sqlite_errorcode=2067))
    not_null_sqlite = IntegrityError("INSERT", {}, _DriverError("NOT NULL constraint failed", sqlite_errorcode=1299))
    check_sqlite = IntegrityError("INSERT", {}, _DriverError("CHECK constraint failed", sqlite_errorcode=275))
    fk_sqlite = IntegrityError("INSERT", {}, _DriverError("FOREIGN KEY constraint failed", sqlite_errorcode=787))
    assert _is_duplicate_key_integrity_error(dup_sqlite, expected_constraints=("uq_uom_one_active",)) is True
    assert _is_duplicate_key_integrity_error(not_null_sqlite, expected_constraints=("uq_uom_one_active",)) is False
    assert _is_duplicate_key_integrity_error(check_sqlite, expected_constraints=("uq_uom_one_active",)) is False
    assert _is_duplicate_key_integrity_error(fk_sqlite, expected_constraints=("uq_uom_one_active",)) is False


@pytest.mark.parametrize(
    "errno,msg",
    [
        (1048, "Column 'uom_code' cannot be null"),
        (3819, "Check constraint 'chk_uom_factor_pos' is violated"),
        (1452, "Cannot add or update a child row: a foreign key constraint fails"),
    ],
)
def test_rollover_does_not_mask_unexpected_integrity_errors_and_rolls_back(
    sqlite_session_factory,
    monkeypatch,
    errno,
    msg,
):
    inv = FakeInventoryInitializer()
    audit_ok = FakeAuditService()

    with sqlite_session_factory() as db:
        prod = product_service.create_product(
            db,
            ProductCreate(stock_code=f"ERR-{errno}", description="Integrity Test", base_uom="unit"),
            inventory_initializer=inv,
            audit_service=audit_ok,
        )
        pid = prod.id
        c1 = product_service.rollover_uom_conversion(
            db,
            pid,
            UomConversionCreate(uom_code="box", conversion_to_base=Decimal("12.000000")),
            audit_service=audit_ok,
        )
        c1_id = c1.id

    # Simulate unexpected IntegrityError on inserting replacement conversion -> must NOT become 409
    with sqlite_session_factory() as db:
        orig_flush = db.flush
        flush_count = {"n": 0}

        def failing_second_flush(*args, **kwargs):
            flush_count["n"] += 1
            if flush_count["n"] == 2:
                raise IntegrityError("INSERT", {}, _DriverError(errno, msg))
            return orig_flush(*args, **kwargs)

        monkeypatch.setattr(db, "flush", failing_second_flush)
        with pytest.raises(IntegrityError):
            product_service.rollover_uom_conversion(
                db,
                pid,
                UomConversionCreate(uom_code="box", conversion_to_base=Decimal("24.000000")),
                audit_service=audit_ok,
            )

    # Prior active conversion c1 must remain active (closure rolled back!)
    with sqlite_session_factory() as db_verify:
        row = db_verify.get(UomConversion, c1_id)
        assert row is not None
        assert row.is_active is True
        assert row.effective_to is None
        assert len(product_service.list_uom_conversions(db_verify, pid)) == 1

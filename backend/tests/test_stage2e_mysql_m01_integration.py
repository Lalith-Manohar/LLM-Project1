"""Live MySQL 8.0.16+ M01 integration tests (executed ONLY when TEST_DATABASE_URL is set)."""

from datetime import timedelta
from decimal import Decimal
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.mysql_compat import ensure_mysql_min_version
from app.models import AuditLog, AuditOutbox, Inventory, Product, UomConversion
from app.schemas.category import CategoryCreate
from app.schemas.product import ProductCreate, ProductUpdate, UomConversionCreate
from app.services.category_service import category_service
from app.services.contracts import AuditEventPayload
from app.services.product_service import ProductConflictError, product_service

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DB_URL = os.getenv("TEST_DATABASE_URL") or settings.TEST_DATABASE_URL

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="TEST_DATABASE_URL is not configured; live MySQL 8.0.16+ M01 integration tests skipped.",
)


class _MySqlTestInitializer:
    def __init__(self, *, fail: bool = False):
        self.fail = fail

    def initialize_product_inventory(self, session: Session, *, product_id: int) -> Inventory:
        if self.fail:
            raise RuntimeError("Simulated M09 initializer failure on MySQL")
        row = Inventory(product_id=product_id)
        session.add(row)
        session.flush()
        return row


class _MySqlTestAuditService:
    def __init__(self, *, fail_tier1: bool = False, fail_tier2: bool = False):
        self.fail_tier1 = fail_tier1
        self.fail_tier2 = fail_tier2

    def record_tier1_event(self, session: Session, event: AuditEventPayload) -> AuditLog:
        if self.fail_tier1:
            raise RuntimeError("Simulated Tier 1 audit failure on MySQL")
        row = AuditLog(
            module=event.module,
            action=event.action,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            outcome=event.outcome,
            audit_tier="TIER_1_FAIL_CLOSED",
            action_source=event.action_source,
            selected_workspace=event.selected_workspace,
            operator_ref=event.operator_ref,
            correlation_id=event.correlation_id,
            idempotency_key=event.idempotency_key,
            before_values=event.before_values,
            after_values=event.after_values,
        )
        session.add(row)
        session.flush()
        return row

    def record_tier2_event(self, session: Session, event: AuditEventPayload) -> AuditOutbox:
        if self.fail_tier2:
            raise RuntimeError("Simulated Tier 2 outbox failure on MySQL")
        row = AuditOutbox(
            idempotency_key=event.idempotency_key or "fallback-key",
            correlation_id=event.correlation_id,
            payload={"action": event.action, "entity_id": event.entity_id},
            status="pending",
        )
        session.add(row)
        session.flush()
        return row


class _MySqlTestFractionalChecker:
    def has_fractional_inventory_or_commitments(
        self, session: Session, *, product_id: int
    ) -> tuple[bool, bool]:
        assert session.in_transaction() is True
        return False, False


@pytest.fixture()
def mysql_session_factory():
    safe_url = settings.get_test_database_url(TEST_DB_URL)
    engine = create_engine(safe_url, future=True)
    with engine.connect() as conn:
        ensure_mysql_min_version(conn)

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", safe_url)

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield factory, engine
    finally:
        command.downgrade(cfg, "base")
        engine.dispose()


def test_mysql_category_product_and_atomic_rollbacks(mysql_session_factory):
    factory, _ = mysql_session_factory
    inv_ok = _MySqlTestInitializer()
    audit_ok = _MySqlTestAuditService()

    with factory() as db:
        cat = category_service.create_category(
            db,
            CategoryCreate(name="MySQL Category", description="Live test"),
            audit_service=audit_ok,
        )
        prod = product_service.create_product(
            db,
            ProductCreate(
                stock_code="mysql-sku-1",
                description="Live MySQL Product",
                category_id=cat.id,
                current_unit_price=Decimal("299.95"),
            ),
            inventory_initializer=inv_ok,
            audit_service=audit_ok,
        )
        assert prod.stock_code == "MYSQL-SKU-1"
        assert prod.allow_fractional_qty is False

        # Rollback when M09 initializer fails
        with pytest.raises(RuntimeError, match="Simulated M09"):
            product_service.create_product(
                db,
                ProductCreate(stock_code="MYSQL-FAIL-INV", description="Should Rollback"),
                inventory_initializer=_MySqlTestInitializer(fail=True),
                audit_service=audit_ok,
            )

        # Rollback when Tier 2 outbox fails
        with pytest.raises(RuntimeError, match="Simulated Tier 2"):
            product_service.create_product(
                db,
                ProductCreate(stock_code="MYSQL-FAIL-AUD", description="Should Rollback"),
                inventory_initializer=inv_ok,
                audit_service=_MySqlTestAuditService(fail_tier2=True),
            )

        assert db.query(Product).count() == 1
        assert db.query(Inventory).count() == 1
        assert db.query(AuditOutbox).count() == 2


def test_mysql_uom_now6_virtual_unique_and_tier1_rollback(mysql_session_factory):
    factory, _ = mysql_session_factory
    inv_ok = _MySqlTestInitializer()
    audit_ok = _MySqlTestAuditService()

    with factory() as db:
        prod = product_service.create_product(
            db,
            ProductCreate(
                stock_code="MYSQL-UOM-1",
                description="MySQL UoM SKU",
                base_uom="liter",
                allow_fractional_qty=True,
            ),
            inventory_initializer=inv_ok,
            audit_service=audit_ok,
        )
        c1 = product_service.rollover_uom_conversion(
            db,
            prod.id,
            UomConversionCreate(uom_code="drum", conversion_to_base=Decimal("20.000000")),
            audit_service=audit_ok,
        )
        c2 = product_service.rollover_uom_conversion(
            db,
            prod.id,
            UomConversionCreate(uom_code="drum", conversion_to_base=Decimal("25.000000")),
            audit_service=audit_ok,
        )
        assert c2.effective_from > c1.effective_from
        assert product_service.convert_product_quantity_to_base(
            db, prod.id, "2", uom_code="drum", at_timestamp=c2.effective_from - timedelta(microseconds=1)
        ) == Decimal("40.0000")
        assert product_service.convert_product_quantity_to_base(
            db, prod.id, "2", uom_code="drum", at_timestamp=c2.effective_from
        ) == Decimal("50.0000")

        # Tier 1 audit failure rolls back rollover cleanly
        with pytest.raises(RuntimeError, match="Simulated Tier 1"):
            product_service.rollover_uom_conversion(
                db,
                prod.id,
                UomConversionCreate(uom_code="drum", conversion_to_base=Decimal("30.000000")),
                audit_service=_MySqlTestAuditService(fail_tier1=True),
            )
        db.refresh(c2)
        assert c2.is_active is True

        # Direct duplicate active insert hits VIRTUAL uq_uom_one_active
        with pytest.raises(IntegrityError):
            db.add(
                UomConversion(
                    product_id=prod.id,
                    uom_code="drum",
                    conversion_to_base=Decimal("40.000000"),
                    is_active=True,
                )
            )
            db.flush()
        db.rollback()


def test_mysql_check_constraints_and_for_update_fractional_transition(mysql_session_factory):
    factory, _ = mysql_session_factory
    inv_ok = _MySqlTestInitializer()
    audit_ok = _MySqlTestAuditService()

    with factory() as db:
        prod = product_service.create_product(
            db,
            ProductCreate(
                stock_code="MYSQL-FRAC-1",
                description="MySQL Fractional SKU",
                allow_fractional_qty=True,
                current_unit_price=Decimal("10.00"),
            ),
            inventory_initializer=inv_ok,
            audit_service=audit_ok,
        )
        updated = product_service.update_product(
            db,
            prod.id,
            ProductUpdate(
                description="MySQL Fractional SKU",
                allow_fractional_qty=False,
                current_unit_price=Decimal("12.50"),
            ),
            audit_service=audit_ok,
            fractional_checker=_MySqlTestFractionalChecker(),
        )
        assert updated.allow_fractional_qty is False

        # Enforced MySQL 8.0.16+ CHECK constraint on negative price
        with pytest.raises(IntegrityError):
            db.execute(
                text(
                    "INSERT INTO products (stock_code, description, current_unit_price) "
                    "VALUES ('BAD-PRICE', 'Invalid', -5.00)"
                )
            )
            db.flush()
        db.rollback()

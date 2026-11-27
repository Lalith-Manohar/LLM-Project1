"""Live MySQL 8.0.16+ Stage 1 integration tests (executed ONLY when TEST_DATABASE_URL is set)."""

import os
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.config import require_destructive_mysql_test_url, settings
from app.db.mysql_compat import ensure_mysql_min_version
from app.models import AuditOutbox, Category, Inventory, Product, UomConversion

BACKEND_DIR = Path(__file__).resolve().parent.parent
TEST_DB_URL = os.getenv("TEST_DATABASE_URL") or settings.TEST_DATABASE_URL

pytestmark = pytest.mark.skipif(
    not TEST_DB_URL,
    reason="TEST_DATABASE_URL is not configured; live MySQL 8.0.16+ integration tests not run.",
)


def _alembic_config(db_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def test_mysql_alembic_upgrade_downgrade_and_schema_invariants():
    safe_test_url = require_destructive_mysql_test_url(TEST_DB_URL)
    engine = create_engine(safe_test_url, future=True)
    with engine.connect() as conn:
        ensure_mysql_min_version(conn)

    cfg = _alembic_config(safe_test_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    inspector = inspect(engine)
    assert set(inspector.get_table_names()) >= {
        "categories",
        "products",
        "uom_conversions",
        "inventory",
        "audit_logs",
        "audit_outbox",
    }

    Session = sessionmaker(bind=engine, future=True)
    with Session.begin() as session:
        cat = Category(name="TestCategory")
        session.add(cat)
        session.flush()

        prod = Product(
            stock_code="SKU-STAGE1",
            description="Stage 1 Test Product",
            category_id=cat.id,
            current_unit_price=Decimal("149.50"),
        )
        session.add(prod)
        session.flush()
        assert prod.allow_fractional_qty is False

        inv = Inventory(product_id=prod.id)
        session.add(inv)
        session.flush()

        session.add(
            UomConversion(
                product_id=prod.id,
                uom_code="box",
                conversion_to_base=Decimal("12.000000"),
                is_active=True,
            )
        )
        session.flush()

        # Duplicate active UoM conversion must fail uq_uom_one_active
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(
                    UomConversion(
                        product_id=prod.id,
                        uom_code="box",
                        conversion_to_base=Decimal("24.000000"),
                        is_active=True,
                    )
                )
                session.flush()

        # Negative price CHECK constraint must hold on MySQL >= 8.0.16
        with pytest.raises(IntegrityError):
            with session.begin_nested():
                session.add(
                    Product(
                        stock_code="SKU-NEG",
                        description="Invalid price",
                        current_unit_price=Decimal("-1.00"),
                    )
                )
                session.flush()

        # AuditOutbox retry_count <= max_retries CHECK constraint
        outbox = AuditOutbox(
            idempotency_key="outbox-test-1",
            correlation_id="corr-test-1",
            payload={"action": "PRODUCT_CREATED"},
            retry_count=0,
            max_retries=5,
        )
        session.add(outbox)
        session.flush()

    # Verify rollback atomicity when inventory insert fails
    with pytest.raises(IntegrityError):
        with Session.begin() as session:
            bad_prod = Product(stock_code="SKU-ROLLBACK", description="Rollback check")
            session.add(bad_prod)
            session.flush()
            session.execute(
                text("INSERT INTO inventory (product_id, current_quantity) VALUES (:pid, -1.0000)"),
                {"pid": bad_prod.id},
            )

    with Session() as session:
        assert session.query(Product).filter_by(stock_code="SKU-ROLLBACK").first() is None

    command.downgrade(cfg, "base")
    engine.dispose()

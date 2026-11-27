"""Stage 1 unit, metadata, MySQL DDL compilation, and validation tests (no live DB required)."""

import io
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.core.config import Settings
from app.db.mysql_compat import ensure_mysql_min_version, parse_mysql_version
from app.db.session import get_db, get_engine, get_session_factory, reset_engine, session_scope
from app.models import (
    AuditLog,
    AuditOutbox,
    Base,
    Category,
    Inventory,
    Product,
    UomConversion,
)
from app.services.contracts import (
    AuditEventPayload,
    AuditServiceProtocol,
    InventoryInitializerProtocol,
)
from app.services.quantity_validation import (
    FractionalPolicyConflictError,
    QuantityValidationError,
    compute_exact_base_quantity,
    validate_disable_fractional_qty,
    validate_quantity_for_product,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent


def test_settings_database_url_and_test_url_isolation():
    cfg = Settings(
        DB_HOST="db.internal",
        DB_PORT=3307,
        DB_USER="app_user",
        DB_PASSWORD="secret_pw",
        DB_NAME="nexora_db",
        TEST_DATABASE_URL=None,
    )
    url = cfg.get_database_url()
    assert url.drivername == "mysql+pymysql"
    assert url.host == "db.internal"
    assert url.port == 3307
    assert url.database == "nexora_db"
    assert url.query["charset"] == "utf8mb4"
    # str(URL) masks passwords by default so credentials are never leaked in logs.
    assert "secret_pw" not in str(url)
    assert "secret_pw" in cfg.sqlalchemy_database_uri
    assert cfg.TEST_DATABASE_URL is None

    # Safeguard: refuse missing, DB-less, or matching development DB_NAME URLs
    with pytest.raises(RuntimeError, match="not configured"):
        cfg.get_test_database_url()
    with pytest.raises(RuntimeError, match="Unsafe TEST_DATABASE_URL"):
        cfg.get_test_database_url("mysql+pymysql://u:p@localhost:3306/nexora_db?charset=utf8mb4")
    with pytest.raises(RuntimeError, match="Unsafe TEST_DATABASE_URL"):
        cfg.get_test_database_url("mysql+pymysql://u:p@127.0.0.1:3307/NEXORA_DB")
    with pytest.raises(ValueError, match="dedicated test database name"):
        cfg.get_test_database_url("mysql+pymysql://u:p@localhost:3306")
    with pytest.raises(ValueError, match="MySQL driver required"):
        cfg.get_test_database_url("sqlite:///:memory:")
    for unsafe_name in (
        "nexora_prod",
        "staging_db",
        "nexora_production_test",
        "nexora_staging_test",
        "nexora_prod_test",
        "nexora_live_test",
        "nexora_stage_test",
        "nexora_prod1_test",
    ):
        with pytest.raises(RuntimeError, match="production-like database name"):
            cfg.get_test_database_url(f"mysql+pymysql://u:p@localhost:3306/{unsafe_name}")

    for safe_name in (
        "nexora_test_db",
        "m01_integration_test",
        "product_test_db",
        "delivery_test_db",
    ):
        safe_url = f"mysql+pymysql://u:p@localhost:3306/{safe_name}?charset=utf8mb4"
        assert cfg.get_test_database_url(safe_url) == safe_url

    # ORM created_at server_default alignment with migration CURRENT_TIMESTAMP
    assert str(Category.__table__.c.created_at.server_default.arg) == "CURRENT_TIMESTAMP"
    assert str(Product.__table__.c.created_at.server_default.arg) == "CURRENT_TIMESTAMP"


def test_lazy_engine_and_session_lifecycle(monkeypatch):
    reset_engine()
    mock_session = MagicMock()
    mock_factory = MagicMock(return_value=mock_session)
    monkeypatch.setattr("app.db.session.get_session_factory", lambda database_url=None: mock_factory)

    # Normal commit flow
    with session_scope() as session:
        assert session is mock_session
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()
    mock_session.close.assert_called_once()

    # Rollback flow on exception
    mock_session.reset_mock()
    with pytest.raises(RuntimeError, match="boom"):
        with session_scope():
            raise RuntimeError("boom")
    mock_session.commit.assert_not_called()
    mock_session.rollback.assert_called_once()
    mock_session.close.assert_called_once()

    # FastAPI get_db generator closes session cleanly
    mock_session.reset_mock()
    gen = get_db()
    assert next(gen) is mock_session
    with pytest.raises(StopIteration):
        next(gen)
    mock_session.close.assert_called_once()

    # Engine creation is lazy (no live socket connected by create_engine alone)
    engine = get_engine("mysql+pymysql://u:p@localhost:3306/nexora_db?charset=utf8mb4")
    assert engine.dialect.name == "mysql"
    engine.dispose()
    reset_engine()


def test_metadata_registers_exact_stage1_tables_only():
    expected_tables = {
        "categories",
        "products",
        "uom_conversions",
        "inventory",
        "audit_logs",
        "audit_outbox",
    }
    assert set(Base.metadata.tables.keys()) == expected_tables
    assert "suppliers" not in Base.metadata.tables
    assert "supplier_products" not in Base.metadata.tables


def test_product_category_and_inventory_schema_details():
    products_tbl = Product.__table__
    assert products_tbl.c.allow_fractional_qty.nullable is False
    assert products_tbl.c.allow_fractional_qty.default.arg is False
    assert str(products_tbl.c.allow_fractional_qty.server_default.arg) == "0"
    assert products_tbl.c.current_unit_price.type.precision == 10
    assert products_tbl.c.current_unit_price.type.scale == 2
    assert str(products_tbl.c.currency_code.server_default.arg) == "'INR'"

    prod_uniques = {c.name for c in products_tbl.constraints if c.__class__.__name__ == "UniqueConstraint"}
    prod_checks = {c.name for c in products_tbl.constraints if c.__class__.__name__ == "CheckConstraint"}
    assert "uq_products_stock_code" in prod_uniques
    assert "chk_products_price_nonneg" in prod_checks

    prod_fks = list(products_tbl.foreign_keys)
    assert len(prod_fks) == 1
    assert prod_fks[0].name == "fk_products_category"
    assert prod_fks[0].ondelete == "RESTRICT"
    assert prod_fks[0].column.table is Category.__table__

    inv_tbl = Inventory.__table__
    assert inv_tbl.c.current_quantity.type.precision == 14
    assert inv_tbl.c.current_quantity.type.scale == 4
    assert inv_tbl.c.safety_factor.type.precision == 4
    assert inv_tbl.c.safety_factor.type.scale == 2
    inv_checks = {c.name for c in inv_tbl.constraints if c.__class__.__name__ == "CheckConstraint"}
    assert inv_checks == {
        "chk_inv_phys_nonneg",
        "chk_inv_res_nonneg",
        "chk_inv_avail_nonneg",
        "chk_inv_min_stock",
        "chk_inv_safety_factor",
    }
    inv_fks = list(inv_tbl.foreign_keys)
    assert len(inv_fks) == 1
    assert inv_fks[0].name == "fk_inventory_product"
    assert inv_fks[0].ondelete == "RESTRICT"


def test_uom_virtual_columns_and_audit_constraints():
    uom_tbl = UomConversion.__table__
    assert uom_tbl.c.conversion_to_base.type.precision == 12
    assert uom_tbl.c.conversion_to_base.type.scale == 6
    assert uom_tbl.c.active_product_id.computed is not None
    assert uom_tbl.c.active_product_id.computed.persisted is False
    assert uom_tbl.c.active_uom_code.computed is not None
    assert uom_tbl.c.active_uom_code.computed.persisted is False

    ddl = str(CreateTable(uom_tbl).compile(dialect=mysql.dialect()))
    assert "GENERATED ALWAYS AS (IF(is_active = TRUE, product_id, NULL)) VIRTUAL" in ddl
    assert "GENERATED ALWAYS AS (IF(is_active = TRUE, uom_code, NULL)) VIRTUAL" in ddl
    assert "CONSTRAINT uq_uom_one_active UNIQUE (active_product_id, active_uom_code)" in ddl
    assert "CONSTRAINT chk_uom_factor_pos CHECK (conversion_to_base > 0.000000)" in ddl

    audit_uniques = {
        c.name for c in AuditLog.__table__.constraints if c.__class__.__name__ == "UniqueConstraint"
    }
    outbox_uniques = {
        c.name for c in AuditOutbox.__table__.constraints if c.__class__.__name__ == "UniqueConstraint"
    }
    outbox_checks = {
        c.name for c in AuditOutbox.__table__.constraints if c.__class__.__name__ == "CheckConstraint"
    }
    assert "uq_audit_idempotency" in audit_uniques
    assert "uq_outbox_idempotency" in outbox_uniques
    assert "chk_outbox_retry" in outbox_checks


def test_fractional_quantity_validation_rules():
    # Whole numbers only when allow_fractional_qty=False
    assert validate_quantity_for_product("5", allow_fractional_qty=False) == Decimal("5")
    assert validate_quantity_for_product(Decimal("5.0000"), allow_fractional_qty=False) == Decimal("5")

    with pytest.raises(QuantityValidationError):
        validate_quantity_for_product("1.5", allow_fractional_qty=False)
    with pytest.raises(QuantityValidationError):
        validate_quantity_for_product("0", allow_fractional_qty=False)
    with pytest.raises(QuantityValidationError):
        validate_quantity_for_product(1.5, allow_fractional_qty=True)  # floats prohibited

    # Up to 4 decimal places and min 0.0001 when allow_fractional_qty=True
    assert validate_quantity_for_product("0.0001", allow_fractional_qty=True) == Decimal("0.0001")
    assert validate_quantity_for_product("12.3456", allow_fractional_qty=True) == Decimal("12.3456")

    with pytest.raises(QuantityValidationError):
        validate_quantity_for_product("0.00009", allow_fractional_qty=True)
    with pytest.raises(QuantityValidationError):
        validate_quantity_for_product("1.12345", allow_fractional_qty=True)

    # DECIMAL(14, 4) maximum boundary enforcement
    assert validate_quantity_for_product("9999999999.9999", allow_fractional_qty=True) == Decimal(
        "9999999999.9999"
    )
    assert validate_quantity_for_product("9999999999", allow_fractional_qty=False) == Decimal("9999999999")
    with pytest.raises(QuantityValidationError, match="DECIMAL\\(14, 4\\)"):
        validate_quantity_for_product("10000000000", allow_fractional_qty=False)
    with pytest.raises(QuantityValidationError, match="DECIMAL\\(14, 4\\)"):
        validate_quantity_for_product("9999999999.99999", allow_fractional_qty=True)

    # Exact base conversion validation quantized to 4 decimals without silent rounding
    exact_int_conv = compute_exact_base_quantity("2", "12.500000", allow_fractional_qty=False)
    assert exact_int_conv == Decimal("25.0000")
    assert exact_int_conv.as_tuple().exponent == -4

    exact_frac_conv = compute_exact_base_quantity("0.2500", "2.500000", allow_fractional_qty=True)
    assert exact_frac_conv == Decimal("0.6250")
    assert exact_frac_conv.as_tuple().exponent == -4

    with pytest.raises(QuantityValidationError):
        # 0.0001 * 0.5 = 0.00005 (5 decimal places -> cannot fit DECIMAL(14,4) cleanly)
        compute_exact_base_quantity("0.0001", "0.500000", allow_fractional_qty=True)
    with pytest.raises(QuantityValidationError, match="DECIMAL\\(14, 4\\)"):
        compute_exact_base_quantity("9999999999", "2.000000", allow_fractional_qty=False)

    # Disabling allow_fractional_qty with fractional inventory or open commitments -> conflict (409)
    validate_disable_fractional_qty(
        has_fractional_inventory=False,
        has_fractional_open_commitments=False,
    )
    with pytest.raises(FractionalPolicyConflictError):
        validate_disable_fractional_qty(
            has_fractional_inventory=True,
            has_fractional_open_commitments=False,
        )


def test_mysql_min_version_compatibility_checks():
    assert parse_mysql_version("8.0.16") == (8, 0, 16)
    assert parse_mysql_version("8.4.2-LTS") == (8, 4, 2)

    conn_ok = MagicMock()
    conn_ok.dialect.name = "mysql"
    conn_ok.execute.return_value.scalar_one.return_value = "8.0.36"
    assert ensure_mysql_min_version(conn_ok) == (8, 0, 36)

    conn_old = MagicMock()
    conn_old.dialect.name = "mysql"
    conn_old.execute.return_value.scalar_one.return_value = "8.0.15"
    with pytest.raises(RuntimeError, match="8.0.16"):
        ensure_mysql_min_version(conn_old)

    conn_maria = MagicMock()
    conn_maria.dialect.name = "mysql"
    conn_maria.execute.return_value.scalar_one.return_value = "10.11.6-MariaDB"
    with pytest.raises(RuntimeError, match="MySQL >= 8.0.16"):
        ensure_mysql_min_version(conn_maria)


def test_alembic_offline_sql_generation_matches_stage1_scope():
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    alembic_cfg.set_main_option(
        "sqlalchemy.url",
        "mysql+pymysql://user:pw@localhost:3306/nexora_test_db?charset=utf8mb4",
    )

    script = ScriptDirectory.from_config(alembic_cfg)
    assert script.get_heads() == ["0001_stage1_foundation"]

    sql_buffer = io.StringIO()
    alembic_cfg.output_buffer = sql_buffer
    command.upgrade(alembic_cfg, "head", sql=True)
    generated_sql = sql_buffer.getvalue()

    for table in ("categories", "audit_logs", "audit_outbox", "products", "uom_conversions", "inventory"):
        assert f"CREATE TABLE {table}" in generated_sql
    assert "CREATE TABLE suppliers" not in generated_sql
    assert "CREATE TABLE supplier_products" not in generated_sql
    assert "allow_fractional_qty" in generated_sql


def test_service_contract_protocols_exposed():
    assert hasattr(InventoryInitializerProtocol, "initialize_product_inventory")
    assert hasattr(AuditServiceProtocol, "record_tier1_event")
    assert hasattr(AuditServiceProtocol, "record_tier2_event")
    payload = AuditEventPayload(
        module="M01",
        action="PRODUCT_CREATED",
        entity_type="product",
        entity_id="1",
        outcome="SUCCESS",
        action_source="UI",
        correlation_id="corr-123",
    )
    assert payload.module == "M01"

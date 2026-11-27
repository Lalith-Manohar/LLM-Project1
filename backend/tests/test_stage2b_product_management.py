"""Stage 2B unit and FastAPI integration tests for M01 Product Management & UoM Rollover."""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.categories import get_audit_service
from app.api.routes.products import (
    get_fractional_policy_checker,
    get_inventory_initializer,
)
from app.db.session import get_db
from app.main import app
from app.models.audit import AuditLog, AuditOutbox
from app.models.category import Category
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.uom_conversion import UomConversion
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    UomConversionCreate,
)
from app.services.contracts import AuditEventPayload
from app.services.product_service import product_service
from app.services.quantity_validation import (
    QuantityValidationError,
    compute_exact_base_quantity,
    validate_quantity_for_product,
)


class FakeInventoryInitializer:
    """Test double for M09 InventoryInitializerProtocol."""

    def __init__(self, *, fail_on_init: bool = False):
        self.fail_on_init = fail_on_init
        self.initialized_product_ids: list[int] = []

    def initialize_product_inventory(self, session: Session, *, product_id: int) -> Inventory:
        if self.fail_on_init:
            raise RuntimeError("Simulated M09 inventory initialization failure")
        row = Inventory(product_id=product_id)
        session.add(row)
        session.flush()
        self.initialized_product_ids.append(product_id)
        return row


class FakeFractionalChecker:
    """Test double for M09/M05 FractionalPolicyCheckerProtocol."""

    def __init__(self, *, has_inv: bool = False, has_commitments: bool = False):
        self.has_inv = has_inv
        self.has_commitments = has_commitments

    def has_fractional_inventory_or_commitments(
        self, session: Session, *, product_id: int
    ) -> tuple[bool, bool]:
        return self.has_inv, self.has_commitments


class FakeAuditService:
    """Test double for SYS-02 AuditServiceProtocol (Tier 1 + Tier 2)."""

    def __init__(self, *, fail_tier1: bool = False, fail_tier2: bool = False):
        self.fail_tier1 = fail_tier1
        self.fail_tier2 = fail_tier2
        self.tier1_events: list[AuditEventPayload] = []
        self.tier2_events: list[AuditEventPayload] = []

    def record_tier1_event(self, session: Session, event: AuditEventPayload) -> AuditLog:
        if self.fail_tier1:
            raise RuntimeError("Simulated Tier 1 audit failure")
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
        self.tier1_events.append(event)
        return row

    def record_tier2_event(self, session: Session, event: AuditEventPayload) -> AuditOutbox:
        if self.fail_tier2:
            raise RuntimeError("Simulated Tier 2 outbox persistence failure")
        row = AuditOutbox(
            idempotency_key=event.idempotency_key or f"t2-{len(self.tier2_events) + 1}",
            correlation_id=event.correlation_id,
            payload={
                "module": event.module,
                "action": event.action,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "before_values": event.before_values,
                "after_values": event.after_values,
            },
            status="pending",
        )
        session.add(row)
        session.flush()
        self.tier2_events.append(event)
        return row


@pytest.fixture()
def sqlite_session_factory():
    """Isolated SQLite in-memory DB for Stage 2B M01 service & API tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _do_connect(dbapi_connection, _connection_record):
        dbapi_connection.isolation_level = None

    @event.listens_for(engine, "begin")
    def _do_begin(conn):
        conn.exec_driver_sql("BEGIN")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) NOT NULL UNIQUE,
                    description VARCHAR(255),
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    selected_workspace VARCHAR(32),
                    action_source VARCHAR(16) NOT NULL DEFAULT 'UI',
                    operator_ref VARCHAR(64),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stock_code VARCHAR(50) NOT NULL UNIQUE,
                    description VARCHAR(255) NOT NULL,
                    category_id INTEGER REFERENCES categories(id),
                    base_uom VARCHAR(32) NOT NULL DEFAULT 'unit',
                    allow_fractional_qty BOOLEAN NOT NULL DEFAULT 0,
                    current_unit_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                    currency_code CHAR(3) NOT NULL DEFAULT 'INR',
                    lifecycle_stage VARCHAR(32) NOT NULL DEFAULT 'Introduction',
                    is_uci_baseline BOOLEAN NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    selected_workspace VARCHAR(32),
                    action_source VARCHAR(16) NOT NULL DEFAULT 'UI',
                    operator_ref VARCHAR(64),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE uom_conversions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL REFERENCES products(id),
                    uom_code VARCHAR(32) NOT NULL,
                    conversion_to_base NUMERIC(12, 6) NOT NULL,
                    effective_from DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    effective_to DATETIME,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    active_product_id INTEGER,
                    active_uom_code VARCHAR(32),
                    selected_workspace VARCHAR(32),
                    action_source VARCHAR(16) NOT NULL DEFAULT 'UI',
                    operator_ref VARCHAR(64),
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL UNIQUE REFERENCES products(id),
                    current_quantity NUMERIC(14, 4) NOT NULL DEFAULT 0.0000,
                    reserved_quantity NUMERIC(14, 4) NOT NULL DEFAULT 0.0000,
                    minimum_stock NUMERIC(14, 4) NOT NULL DEFAULT 10.0000,
                    safety_factor NUMERIC(4, 2) NOT NULL DEFAULT 1.20,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    module VARCHAR(64) NOT NULL,
                    action VARCHAR(64) NOT NULL,
                    entity_type VARCHAR(64) NOT NULL,
                    entity_id VARCHAR(64),
                    outcome VARCHAR(16) NOT NULL,
                    audit_tier VARCHAR(32) NOT NULL,
                    action_source VARCHAR(16) NOT NULL,
                    selected_workspace VARCHAR(32),
                    operator_ref VARCHAR(64),
                    correlation_id VARCHAR(64) NOT NULL,
                    idempotency_key VARCHAR(128) UNIQUE,
                    before_values JSON,
                    after_values JSON,
                    error_summary VARCHAR(500)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE audit_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
                    correlation_id VARCHAR(64) NOT NULL,
                    payload JSON NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 5,
                    next_retry_at DATETIME,
                    status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    last_error TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture()
def api_client(sqlite_session_factory):
    fake_inv = FakeInventoryInitializer()
    fake_audit = FakeAuditService()
    fake_checker = FakeFractionalChecker()

    def override_db():
        db = sqlite_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_inventory_initializer] = lambda: fake_inv
    app.dependency_overrides[get_audit_service] = lambda: fake_audit
    app.dependency_overrides[get_fractional_policy_checker] = lambda: fake_checker
    try:
        yield TestClient(app), fake_inv, fake_audit, fake_checker, sqlite_session_factory
    finally:
        app.dependency_overrides.clear()


def test_product_crud_category_validation_and_filtering(api_client):
    client, fake_inv, fake_audit, _, factory = api_client

    with factory.begin() as db:
        active_cat = Category(name="Home", is_active=True)
        inactive_cat = Category(name="Archived", is_active=False)
        db.add_all([active_cat, inactive_cat])
        db.flush()
        active_cat_id = active_cat.id
        inactive_cat_id = inactive_cat.id

    # Create product with lowercase stock_code -> normalized uppercase + atomic inventory
    r1 = client.post(
        "/api/v1/products",
        json={
            "stock_code": " 85123a ",
            "description": "White Hanging Heart",
            "category_id": active_cat_id,
            "current_unit_price": "199.50",
            "is_uci_baseline": True,
            "operator_ref": "mgr-1",
        },
        headers={"X-NEXORA-Workspace": "Store Manager (Admin)", "X-Correlation-ID": "p-corr-1"},
    )
    assert r1.status_code == 201
    p1 = r1.json()
    assert p1["stock_code"] == "85123A"
    assert p1["currency_code"] == "INR"
    assert p1["allow_fractional_qty"] is False
    assert p1["selected_workspace"] == "store_manager"
    assert p1["id"] in fake_inv.initialized_product_ids

    # Duplicate SKU -> 409
    dup = client.post(
        "/api/v1/products",
        json={"stock_code": "85123A", "description": "Duplicate"},
    )
    assert dup.status_code == 409

    # Nonexistent category -> 404; inactive category -> 409
    assert (
        client.post(
            "/api/v1/products",
            json={"stock_code": "SKU-404", "description": "Bad Cat", "category_id": 9999},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/products",
            json={
                "stock_code": "SKU-INACT",
                "description": "Inactive Cat",
                "category_id": inactive_cat_id,
            },
        ).status_code
        == 409
    )

    # Create second product for list/sort/filter
    r2 = client.post(
        "/api/v1/products",
        json={
            "stock_code": "SKU-002",
            "description": "Ceramic Mug",
            "current_unit_price": "49.00",
            "allow_fractional_qty": True,
        },
    )
    assert r2.status_code == 201
    p2 = r2.json()

    # GET by ID & 404
    assert client.get(f"/api/v1/products/{p1['id']}").status_code == 200
    assert client.get("/api/v1/products/99999").status_code == 404

    # List with search, price range, sort_by=current_unit_price desc, invalid sort -> 422
    lst = client.get("/api/v1/products?sort_by=current_unit_price&sort_dir=desc&page=1&page_size=1")
    assert lst.status_code == 200
    assert lst.json()["total"] == 2
    assert lst.json()["total_pages"] == 2
    assert lst.json()["items"][0]["stock_code"] == "85123A"

    assert client.get("/api/v1/products?sort_by=invalid_col").status_code == 422
    assert client.get("/api/v1/products?min_price=500&max_price=100").status_code == 422
    assert client.get("/api/v1/products?search=mug").json()["total"] == 1

    # PUT update preserves workspace/operator_ref when omitted; base_uom change blocked (409) since inventory exists
    upd = client.put(
        f"/api/v1/products/{p1['id']}",
        json={
            "description": "Updated Heart",
            "category_id": active_cat_id,
            "current_unit_price": "249.00",
        },
        headers={"X-Correlation-ID": "p-corr-1"},
    )
    assert upd.status_code == 200
    assert upd.json()["selected_workspace"] == "store_manager"
    assert upd.json()["operator_ref"] == "mgr-1"

    base_uom_change = client.put(
        f"/api/v1/products/{p1['id']}",
        json={
            "description": "Updated Heart",
            "category_id": active_cat_id,
            "base_uom": "box",
            "current_unit_price": "249.00",
        },
    )
    assert base_uom_change.status_code == 409

    # Status toggle + idempotency
    deact = client.patch(f"/api/v1/products/{p2['id']}/status", json={"is_active": False})
    assert deact.status_code == 200
    assert deact.json()["is_active"] is False
    same = client.patch(f"/api/v1/products/{p2['id']}/status", json={"is_active": False})
    assert same.status_code == 200

    # Distinct idempotency keys even when correlation_id is reused
    corr1_events = [e for e in fake_audit.tier2_events if e.correlation_id == "p-corr-1"]
    assert len(corr1_events) == 2
    assert len({e.idempotency_key for e in corr1_events}) == 2


def test_fractional_policy_toggle_dependencies_and_bounds(sqlite_session_factory):
    inv = FakeInventoryInitializer()
    audit = FakeAuditService()

    # Exact DECIMAL(14,4) boundary checks via Stage 1 quantity_validation
    assert validate_quantity_for_product("9999999999.9999", allow_fractional_qty=True) == Decimal("9999999999.9999")
    assert compute_exact_base_quantity("0.2500", "2.500000", allow_fractional_qty=True) == Decimal("0.6250")
    with pytest.raises(QuantityValidationError):
        validate_quantity_for_product("10000000000", allow_fractional_qty=False)
    with pytest.raises(QuantityValidationError):
        compute_exact_base_quantity("0.0001", "0.500000", allow_fractional_qty=True)

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
        p = client.post(
            "/api/v1/products",
            json={"stock_code": "FRAC-1", "description": "Bulk Sugar", "allow_fractional_qty": True},
        ).json()

        # Without M09 FractionalPolicyCheckerProtocol configured -> 503 (never silently bypassed)
        resp_503 = client.put(
            f"/api/v1/products/{p['id']}",
            json={"description": "Bulk Sugar", "allow_fractional_qty": False, "current_unit_price": "10.00"},
        )
        assert resp_503.status_code == 503

        # With fractional inventory -> 409 Conflict
        app.dependency_overrides[get_fractional_policy_checker] = lambda: FakeFractionalChecker(has_inv=True)
        resp_409 = client.put(
            f"/api/v1/products/{p['id']}",
            json={"description": "Bulk Sugar", "allow_fractional_qty": False, "current_unit_price": "10.00"},
        )
        assert resp_409.status_code == 409

        # With zero fractional inventory & commitments -> 200 OK
        app.dependency_overrides[get_fractional_policy_checker] = lambda: FakeFractionalChecker(
            has_inv=False, has_commitments=False
        )
        resp_200 = client.put(
            f"/api/v1/products/{p['id']}",
            json={"description": "Bulk Sugar", "allow_fractional_qty": False, "current_unit_price": "10.00"},
        )
        assert resp_200.status_code == 200
        assert resp_200.json()["allow_fractional_qty"] is False
    finally:
        app.dependency_overrides.clear()


def test_uom_rollover_immediate_server_time_and_tier1_audit(api_client):
    client, _, fake_audit, _, _ = api_client

    p = client.post(
        "/api/v1/products",
        json={"stock_code": "UOM-1", "description": "Bottled Oil", "base_uom": "unit"},
    ).json()

    # Caller-supplied effective_from / effective_to MUST be rejected with 422
    bad_ts = client.post(
        f"/api/v1/products/{p['id']}/uom-conversions",
        json={
            "uom_code": "case",
            "conversion_to_base": "12.000000",
            "effective_from": "2026-12-01T00:00:00",
        },
    )
    assert bad_ts.status_code == 422

    # Same uom_code as base_uom -> 422
    same_uom = client.post(
        f"/api/v1/products/{p['id']}/uom-conversions",
        json={"uom_code": "unit", "conversion_to_base": "1.000000"},
    )
    assert same_uom.status_code == 422

    # First conversion + immediate rollover
    c1 = client.post(
        f"/api/v1/products/{p['id']}/uom-conversions",
        json={"uom_code": "case", "conversion_to_base": "12.000000"},
    )
    assert c1.status_code == 201
    assert c1.json()["is_active"] is True
    assert c1.json()["effective_to"] is None

    c2 = client.post(
        f"/api/v1/products/{p['id']}/uom-conversions",
        json={"uom_code": "case", "conversion_to_base": "24.000000"},
    )
    assert c2.status_code == 201
    assert c2.json()["is_active"] is True

    history = client.get(f"/api/v1/products/{p['id']}/uom-conversions").json()
    assert len(history) == 2
    active_rows = [row for row in history if row["is_active"]]
    closed_rows = [row for row in history if not row["is_active"]]
    assert len(active_rows) == 1
    assert Decimal(active_rows[0]["conversion_to_base"]) == Decimal("24.000000")
    assert len(closed_rows) == 1
    assert closed_rows[0]["effective_to"] == active_rows[0]["effective_from"]
    assert len(fake_audit.tier1_events) == 2


def test_rollbacks_and_transaction_ownership(sqlite_session_factory):
    # 1. Inventory initializer failure rolls back product creation completely
    with sqlite_session_factory() as db:
        with pytest.raises(RuntimeError, match="Simulated M09"):
            product_service.create_product(
                db,
                ProductCreate(stock_code="FAIL-INV", description="Should Rollback"),
                inventory_initializer=FakeInventoryInitializer(fail_on_init=True),
                audit_service=FakeAuditService(),
            )
    with sqlite_session_factory() as db:
        assert db.execute(select(Product)).scalars().all() == []
        assert db.execute(select(Inventory)).scalars().all() == []
        assert db.execute(select(AuditOutbox)).scalars().all() == []

    # 2. Tier 2 audit failure rolls back BOTH product and initial inventory row
    with sqlite_session_factory() as db:
        with pytest.raises(RuntimeError, match="Simulated Tier 2"):
            product_service.create_product(
                db,
                ProductCreate(stock_code="FAIL-AUD", description="Should Rollback"),
                inventory_initializer=FakeInventoryInitializer(),
                audit_service=FakeAuditService(fail_tier2=True),
            )
    with sqlite_session_factory() as db:
        assert db.execute(select(Product)).scalars().all() == []
        assert db.execute(select(Inventory)).scalars().all() == []

    # 3. Autobegin SELECT session commits standalone call; commit=False respects caller transaction
    inv_ok = FakeInventoryInitializer()
    audit_ok = FakeAuditService()
    db_auto = sqlite_session_factory()
    try:
        _ = db_auto.execute(select(Product)).scalars().all()
        assert db_auto.in_transaction() is True
        p = product_service.create_product(
            db_auto,
            ProductCreate(stock_code="AUTO-1", description="Autobegin Commit"),
            inventory_initializer=inv_ok,
            audit_service=audit_ok,
        )
        p_id = p.id
    finally:
        db_auto.close()

    with sqlite_session_factory() as db_verify:
        assert product_service.get_product(db_verify, p_id).stock_code == "AUTO-1"

    # Caller-owned outer transaction with commit=False rolls back if caller aborts
    db_caller = sqlite_session_factory()
    try:
        with pytest.raises(RuntimeError, match="caller abort"):
            with db_caller.begin():
                product_service.update_product(
                    db_caller,
                    p_id,
                    ProductUpdate(description="Caller Rolled Back", current_unit_price=Decimal("5.00")),
                    audit_service=audit_ok,
                    commit=False,
                )
                raise RuntimeError("caller abort")
    finally:
        db_caller.close()

    with sqlite_session_factory() as db_verify2:
        assert product_service.get_product(db_verify2, p_id).description == "Autobegin Commit"

    # 4. Tier 1 failure on UoM rollover leaves prior conversion untouched
    with sqlite_session_factory() as db:
        with pytest.raises(RuntimeError, match="Simulated Tier 1"):
            product_service.rollover_uom_conversion(
                db,
                p_id,
                UomConversionCreate(uom_code="pack", conversion_to_base=Decimal("6.000000")),
                audit_service=FakeAuditService(fail_tier1=True),
            )
    with sqlite_session_factory() as db:
        assert db.execute(select(UomConversion)).scalars().all() == []


def test_missing_m09_or_sys02_returns_503(sqlite_session_factory):
    def override_db():
        db = sqlite_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        resp = client.post("/api/v1/products", json={"stock_code": "X1", "description": "No M09"})
        assert resp.status_code == 503
        assert "M09" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()

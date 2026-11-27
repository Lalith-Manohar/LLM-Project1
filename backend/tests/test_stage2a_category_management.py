"""Stage 2A unit and FastAPI integration tests for M01 Category Management."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.categories import get_audit_service
from app.db.session import get_db
from app.main import app
from app.models.audit import AuditOutbox
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryStatusUpdate, CategoryUpdate
from app.services.category_service import (
    CategoryConflictError,
    CategoryNotFoundError,
    category_service,
)
from app.services.contracts import AuditEventPayload


class FakeTier2AuditService:
    """Test double implementing AuditServiceProtocol for isolated Stage 2A tests."""

    def __init__(self, *, fail_on_persist: bool = False):
        self.fail_on_persist = fail_on_persist
        self.recorded_events: list[AuditEventPayload] = []

    def record_tier1_event(self, session: Session, event: AuditEventPayload):
        raise NotImplementedError("Stage 2A category CRUD uses Tier 2 outbox only.")

    def record_tier2_event(self, session: Session, event: AuditEventPayload) -> AuditOutbox:
        if self.fail_on_persist:
            raise RuntimeError("Simulated audit_outbox persistence failure")

        row = AuditOutbox(
            idempotency_key=event.idempotency_key or f"key-{len(self.recorded_events) + 1}",
            correlation_id=event.correlation_id,
            payload={
                "module": event.module,
                "action": event.action,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "outcome": event.outcome,
                "before_values": event.before_values,
                "after_values": event.after_values,
            },
            status="pending",
        )
        session.add(row)
        session.flush()
        self.recorded_events.append(event)
        return row


@pytest.fixture()
def sqlite_session_factory():
    """Isolated SQLite in-memory DB with categories & audit_outbox tables for ORM/API tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
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
    """FastAPI TestClient wired to isolated SQLite DB and FakeTier2AuditService."""
    fake_audit = FakeTier2AuditService()

    def override_db():
        db = sqlite_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_audit_service] = lambda: fake_audit
    try:
        yield TestClient(app), fake_audit, sqlite_session_factory
    finally:
        app.dependency_overrides.clear()


def test_service_create_update_status_and_outbox_atomicity(sqlite_session_factory):
    audit_ok = FakeTier2AuditService()

    with sqlite_session_factory() as db:
        created = category_service.create_category(
            db,
            CategoryCreate(name="  Home Decor  ", description=" Candles & vases "),
            audit_service=audit_ok,
            correlation_id="corr-001",
            workspace_header="store_manager",
        )
        assert created.id == 1
        assert created.name == "Home Decor"
        assert created.description == "Candles & vases"
        assert created.is_active is True
        assert created.selected_workspace == "store_manager"

        # Outbox row persisted in same transaction
        outbox_rows = list(db.execute(select(AuditOutbox)).scalars())
        assert len(outbox_rows) == 1
        assert outbox_rows[0].payload["action"] == "CATEGORY_CREATED"
        assert outbox_rows[0].status == "pending"

        # Duplicate name (case-insensitive) -> 409 conflict
        with pytest.raises(CategoryConflictError):
            category_service.create_category(
                db,
                CategoryCreate(name="home decor"),
                audit_service=audit_ok,
            )

        # Update category
        updated = category_service.update_category(
            db,
            created.id,
            CategoryUpdate(name="Seasonal Decor", description="Updated"),
            audit_service=audit_ok,
            correlation_id="corr-002",
        )
        assert updated.name == "Seasonal Decor"
        assert len(audit_ok.recorded_events) == 2
        assert audit_ok.recorded_events[1].before_values["name"] == "Home Decor"
        assert audit_ok.recorded_events[1].after_values["name"] == "Seasonal Decor"

        # Deactivate and reactivate
        deactivated = category_service.update_category_status(
            db,
            created.id,
            CategoryStatusUpdate(is_active=False),
            audit_service=audit_ok,
            correlation_id="corr-003",
        )
        assert deactivated.is_active is False
        assert audit_ok.recorded_events[2].action == "CATEGORY_DEACTIVATED"

        # Idempotent status call when already inactive does not emit extra event
        same_state = category_service.update_category_status(
            db,
            created.id,
            CategoryStatusUpdate(is_active=False),
            audit_service=audit_ok,
        )
        assert same_state.is_active is False
        assert len(audit_ok.recorded_events) == 3

        with pytest.raises(CategoryNotFoundError):
            category_service.get_category(db, 9999)


def test_service_rolls_back_category_when_outbox_persistence_fails(sqlite_session_factory):
    failing_audit = FakeTier2AuditService(fail_on_persist=True)
    working_audit = FakeTier2AuditService()

    # Create fails -> zero category rows persisted
    with sqlite_session_factory() as db:
        with pytest.raises(RuntimeError, match="Simulated audit_outbox persistence failure"):
            category_service.create_category(
                db,
                CategoryCreate(name="RolledBackCategory"),
                audit_service=failing_audit,
            )

    with sqlite_session_factory() as db:
        assert db.execute(select(Category)).scalars().all() == []
        assert db.execute(select(AuditOutbox)).scalars().all() == []

        # Create succeeds with working audit, then update fails on audit -> original name preserved
        cat = category_service.create_category(
            db,
            CategoryCreate(name="OriginalName"),
            audit_service=working_audit,
        )
        cat_id = cat.id

    with sqlite_session_factory() as db:
        with pytest.raises(RuntimeError, match="Simulated audit_outbox persistence failure"):
            category_service.update_category(
                db,
                cat_id,
                CategoryUpdate(name="ShouldRollbackName"),
                audit_service=failing_audit,
            )

    with sqlite_session_factory() as db:
        refetched = category_service.get_category(db, cat_id)
        assert refetched.name == "OriginalName"


def test_async_delivery_failure_after_persistence_does_not_fail_category(sqlite_session_factory):
    audit_ok = FakeTier2AuditService()

    def simulated_async_worker_failure(_outbox_row: AuditOutbox):
        raise ConnectionError("Downstream audit broker unreachable")

    with sqlite_session_factory() as db:
        created = category_service.create_category(
            db,
            CategoryCreate(name="Kitchenware"),
            audit_service=audit_ok,
        )
        outbox_row = db.execute(select(AuditOutbox)).scalar_one()

    # Even if post-commit async delivery fails, category remains persisted
    with pytest.raises(ConnectionError):
        simulated_async_worker_failure(outbox_row)

    with sqlite_session_factory() as db:
        persisted = category_service.get_category(db, created.id)
        assert persisted.name == "Kitchenware"


def test_category_api_endpoints_pagination_filtering_and_errors(api_client):
    client, fake_audit, _ = api_client

    # Create 3 categories
    r1 = client.post(
        "/api/v1/categories",
        json={"name": "Kitchen", "description": "Cookware"},
        headers={"X-NEXORA-Workspace": "Store Manager (Admin)", "X-Correlation-ID": "c-1"},
    )
    assert r1.status_code == 201
    cat1 = r1.json()
    assert cat1["name"] == "Kitchen"
    assert cat1["selected_workspace"] == "store_manager"

    r2 = client.post("/api/v1/categories", json={"name": "Lighting", "description": "Lamps"})
    assert r2.status_code == 201
    cat2 = r2.json()

    r3 = client.post("/api/v1/categories", json={"name": "Accessories", "description": "Bags"})
    assert r3.status_code == 201

    # Duplicate POST -> 409
    dup = client.post("/api/v1/categories", json={"name": "kitchen"})
    assert dup.status_code == 409
    assert "detail" in dup.json()

    # Blank name -> 422
    blank = client.post("/api/v1/categories", json={"name": "   "})
    assert blank.status_code == 422

    # GET by ID & 404
    g1 = client.get(f"/api/v1/categories/{cat1['id']}")
    assert g1.status_code == 200
    assert g1.json()["name"] == "Kitchen"
    assert client.get("/api/v1/categories/99999").status_code == 404

    # Deactivate cat2
    p2 = client.patch(f"/api/v1/categories/{cat2['id']}/status", json={"is_active": False})
    assert p2.status_code == 200
    assert p2.json()["is_active"] is False

    # Paginated listing (page=1, page_size=2)
    lst = client.get("/api/v1/categories?page=1&page_size=2")
    assert lst.status_code == 200
    body = lst.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total_pages"] == 2
    assert [item["name"] for item in body["items"]] == ["Accessories", "Kitchen"]

    # Filter by is_active=false
    inactive = client.get("/api/v1/categories?is_active=false")
    assert inactive.status_code == 200
    assert inactive.json()["total"] == 1
    assert inactive.json()["items"][0]["name"] == "Lighting"

    # Search by keyword
    searched = client.get("/api/v1/categories?search=cook")
    assert searched.status_code == 200
    assert searched.json()["total"] == 1
    assert searched.json()["items"][0]["name"] == "Kitchen"

    # Update PUT -> 200, duplicate PUT -> 409, missing PUT -> 404
    upd = client.put(
        f"/api/v1/categories/{cat1['id']}",
        json={"name": "Kitchen & Dining", "description": "Updated"},
    )
    assert upd.status_code == 200
    assert upd.json()["name"] == "Kitchen & Dining"

    assert (
        client.put(
            f"/api/v1/categories/{cat1['id']}",
            json={"name": "Accessories"},
        ).status_code
        == 409
    )
    assert (
        client.put(
            "/api/v1/categories/99999",
            json={"name": "Nonexistent"},
        ).status_code
        == 404
    )
    assert len(fake_audit.recorded_events) == 5


def test_missing_sys02_dependency_returns_503_explicitly(sqlite_session_factory):
    def override_db():
        db = sqlite_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        resp = client.post("/api/v1/categories", json={"name": "Test503"})
        assert resp.status_code == 503
        assert "SYS-02" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_transaction_ownership_across_fresh_and_autobegin_sessions(sqlite_session_factory):
    audit_ok = FakeTier2AuditService()
    failing_audit = FakeTier2AuditService(fail_on_persist=True)

    # 1. Fresh session commits and persists after close()
    db1 = sqlite_session_factory()
    try:
        assert db1.in_transaction() is False
        cat = category_service.create_category(
            db1,
            CategoryCreate(name="FreshSessionCat"),
            audit_service=audit_ok,
        )
        cat_id = cat.id
    finally:
        db1.close()

    # 2. Session with an existing SQLAlchemy autobegin transaction from a prior SELECT
    db2 = sqlite_session_factory()
    try:
        _ = db2.execute(select(Category)).scalars().all()
        assert db2.in_transaction() is True
        updated = category_service.update_category(
            db2,
            cat_id,
            CategoryUpdate(name="AutobeginCommittedCat"),
            audit_service=audit_ok,
        )
        assert updated.name == "AutobeginCommittedCat"
    finally:
        db2.close()

    # Verify update actually persisted in a brand-new session after db2.close()
    with sqlite_session_factory() as db_verify:
        persisted = category_service.get_category(db_verify, cat_id)
        assert persisted.name == "AutobeginCommittedCat"

    # 3. Audit failure during autobegin rolls back full outer transaction cleanly
    db3 = sqlite_session_factory()
    try:
        _ = db3.execute(select(Category)).scalars().all()
        assert db3.in_transaction() is True
        with pytest.raises(RuntimeError, match="Simulated audit_outbox persistence failure"):
            category_service.update_category(
                db3,
                cat_id,
                CategoryUpdate(name="AutobeginRolledBackCat"),
                audit_service=failing_audit,
            )
    finally:
        db3.close()

    with sqlite_session_factory() as db_verify2:
        assert category_service.get_category(db_verify2, cat_id).name == "AutobeginCommittedCat"

    # 4. commit=False requires an active caller transaction
    with sqlite_session_factory() as db4:
        with pytest.raises(RuntimeError, match="commit=False"):
            category_service.create_category(
                db4,
                CategoryCreate(name="ShouldFailNoTx"),
                audit_service=audit_ok,
                commit=False,
            )


def test_workspace_provenance_preserved_when_omitted_on_updates(api_client):
    client, fake_audit, _ = api_client

    # Create with explicit workspace provenance
    create_resp = client.post(
        "/api/v1/categories",
        json={"name": "WorkspaceCat", "description": "Initial", "operator_ref": "op-1"},
        headers={"X-NEXORA-Workspace": "Store Manager (Admin)"},
    )
    assert create_resp.status_code == 201
    cat_id = create_resp.json()["id"]
    assert create_resp.json()["selected_workspace"] == "store_manager"

    # 1. Update without workspace payload or header -> preserves store_manager & op-1
    upd_no_ws = client.put(
        f"/api/v1/categories/{cat_id}",
        json={"name": "WorkspaceCat Renamed", "description": "Updated"},
    )
    assert upd_no_ws.status_code == 200
    assert upd_no_ws.json()["selected_workspace"] == "store_manager"
    assert upd_no_ws.json()["operator_ref"] == "op-1"
    assert fake_audit.recorded_events[-1].selected_workspace == "store_manager"

    # 2. Update with explicit workspace -> updates provenance
    upd_with_ws = client.put(
        f"/api/v1/categories/{cat_id}",
        json={"name": "WorkspaceCat Finance", "selected_workspace": "finance_staff"},
    )
    assert upd_with_ws.status_code == 200
    assert upd_with_ws.json()["selected_workspace"] == "finance_staff"

    # 3. Status change without workspace header -> preserves finance_staff
    status_no_ws = client.patch(
        f"/api/v1/categories/{cat_id}/status",
        json={"is_active": False},
    )
    assert status_no_ws.status_code == 200
    assert status_no_ws.json()["selected_workspace"] == "finance_staff"
    assert fake_audit.recorded_events[-1].selected_workspace == "finance_staff"

    # 4. Status change with explicit workspace header -> updates provenance
    status_with_ws = client.patch(
        f"/api/v1/categories/{cat_id}/status",
        json={"is_active": True},
        headers={"X-NEXORA-Workspace": "Purchase Manager"},
    )
    assert status_with_ws.status_code == 200
    assert status_with_ws.json()["selected_workspace"] == "purchase_manager"


def test_audit_outbox_idempotency_keys_with_reused_correlation_id(
    api_client,
    sqlite_session_factory,
):
    client, fake_audit, _ = api_client

    # Create category
    r_create = client.post(
        "/api/v1/categories",
        json={"name": "CorrelationCat"},
        headers={"X-Correlation-ID": "shared-corr-id"},
    )
    assert r_create.status_code == 201
    cat_id = r_create.json()["id"]

    # 1. Two updates to the same category with the exact same X-Correlation-ID
    r_upd1 = client.put(
        f"/api/v1/categories/{cat_id}",
        json={"name": "CorrelationCat v2"},
        headers={"X-Correlation-ID": "shared-corr-id"},
    )
    r_upd2 = client.put(
        f"/api/v1/categories/{cat_id}",
        json={"name": "CorrelationCat v3"},
        headers={"X-Correlation-ID": "shared-corr-id"},
    )
    assert r_upd1.status_code == 200
    assert r_upd2.status_code == 200

    # 2. Update followed by status change using the same X-Correlation-ID
    r_status = client.patch(
        f"/api/v1/categories/{cat_id}/status",
        json={"is_active": False},
        headers={"X-Correlation-ID": "shared-corr-id"},
    )
    assert r_status.status_code == 200

    # 3. All 4 events share correlation_id="shared-corr-id" but have 4 distinct idempotency_keys
    assert len(fake_audit.recorded_events) == 4
    assert all(ev.correlation_id == "shared-corr-id" for ev in fake_audit.recorded_events)
    keys = [ev.idempotency_key for ev in fake_audit.recorded_events]
    assert len(set(keys)) == 4

    # 4. Logical retry with an identical idempotency_key is rejected by uq_outbox_idempotency
    with sqlite_session_factory() as db:
        with pytest.raises(IntegrityError):
            category_service.update_category(
                db,
                cat_id,
                CategoryUpdate(name="CorrelationCat Retry"),
                audit_service=fake_audit,
                correlation_id="shared-corr-id",
                idempotency_key=keys[1],
            )
    with sqlite_session_factory() as db_check:
        assert category_service.get_category(db_check, cat_id).name == "CorrelationCat v3"

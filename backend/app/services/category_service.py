"""M01 Category Management service layer with Tier 2 transactional audit outbox."""

from contextlib import contextmanager
import math
from typing import Any, Iterator, Optional
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import (
    CategoryCreate,
    CategoryStatusUpdate,
    CategoryUpdate,
)
from app.services.contracts import AuditEventPayload, AuditServiceProtocol


class CategoryNotFoundError(LookupError):
    """Raised when a requested category ID does not exist (maps to HTTP 404)."""


class CategoryConflictError(ValueError):
    """Raised when a category operation violates uniqueness (maps to HTTP 409)."""


class CategoryValidationError(ValueError):
    """Raised on invalid category service inputs (maps to HTTP 422)."""


@contextmanager
def _transaction(session: Session, *, commit: bool = True) -> Iterator[None]:
    """Explicit transaction ownership contract compatible with get_db() and autobegin.

    - commit=True (default for standalone service/API calls):
      - If no transaction is active, opens and commits `session.begin()`.
      - If an outer transaction is already active (e.g. SQLAlchemy autobegin from a prior
        SELECT on get_db()), runs inside a savepoint and commits the outer transaction on
        success (rolling back the full outer transaction on error) so writes never silently
        stay uncommitted when get_db() closes the session.
    - commit=False (for multi-step orchestrators managing an outer `with session.begin():`):
      - Runs inside a savepoint and leaves outer commit/rollback to the caller.
    """
    if not commit:
        if not session.in_transaction():
            raise RuntimeError("commit=False requires an active caller-managed transaction.")
        with session.begin_nested():
            yield
        return

    if not session.in_transaction():
        with session.begin():
            yield
        return

    try:
        with session.begin_nested():
            yield
        session.commit()
    except Exception:
        session.rollback()
        raise


def _category_snapshot(category: Category) -> dict[str, Any]:
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "is_active": category.is_active,
    }


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class CategoryService:
    """Business service for M01 product categories."""

    def create_category(
        self,
        session: Session,
        payload: CategoryCreate,
        *,
        audit_service: AuditServiceProtocol,
        correlation_id: Optional[str] = None,
        workspace_header: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        commit: bool = True,
    ) -> Category:
        """Create a new category and persist its Tier 2 audit outbox event atomically."""
        corr_id = (correlation_id or "").strip() or f"req-{uuid.uuid4().hex[:12]}"
        selected_ws = payload.selected_workspace or workspace_header

        with _transaction(session, commit=commit):
            existing = session.execute(
                select(Category.id).where(func.lower(Category.name) == payload.name.lower())
            ).scalar_one_or_none()
            if existing is not None:
                raise CategoryConflictError(
                    f"Category with name '{payload.name}' already exists."
                )

            category = Category(
                name=payload.name,
                description=payload.description,
                is_active=True,
                selected_workspace=selected_ws,
                action_source=payload.action_source,
                operator_ref=payload.operator_ref,
            )
            session.add(category)
            try:
                session.flush()
            except IntegrityError as exc:
                raise CategoryConflictError(
                    f"Category with name '{payload.name}' already exists."
                ) from exc

            event_key = idempotency_key or f"cat-create-{category.id}-{corr_id}-{uuid.uuid4().hex[:12]}"
            event = AuditEventPayload(
                module="M01",
                action="CATEGORY_CREATED",
                entity_type="category",
                entity_id=str(category.id),
                outcome="SUCCESS",
                action_source=payload.action_source,
                selected_workspace=selected_ws,
                operator_ref=payload.operator_ref,
                correlation_id=corr_id,
                idempotency_key=event_key,
                before_values=None,
                after_values=_category_snapshot(category),
            )
            audit_service.record_tier2_event(session, event)

        session.refresh(category)
        return category

    def get_category(self, session: Session, category_id: int) -> Category:
        """Retrieve a single category by primary key or raise CategoryNotFoundError."""
        category = session.get(Category, category_id)
        if category is None:
            raise CategoryNotFoundError(f"Category {category_id} was not found.")
        return category

    def list_categories(
        self,
        session: Session,
        *,
        page: int = 1,
        page_size: int = 25,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> tuple[list[Category], int, int, int, int]:
        """List categories with deterministic sorting, search, status filter, and pagination."""
        if page < 1:
            raise CategoryValidationError("page must be greater than or equal to 1.")
        if page_size < 1 or page_size > 100:
            raise CategoryValidationError("page_size must be between 1 and 100.")

        stmt = select(Category)
        count_stmt = select(func.count()).select_from(Category)

        if is_active is not None:
            stmt = stmt.where(Category.is_active == is_active)
            count_stmt = count_stmt.where(Category.is_active == is_active)

        if search is not None and search.strip():
            escaped = f"%{_escape_like(search.strip())}%"
            search_filter = or_(
                Category.name.ilike(escaped, escape="\\"),
                Category.description.ilike(escaped, escape="\\"),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total = int(session.execute(count_stmt).scalar_one())
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        rows = list(
            session.execute(
                stmt.order_by(Category.name.asc(), Category.id.asc())
                .offset(offset)
                .limit(page_size)
            ).scalars()
        )
        return rows, total, page, page_size, total_pages

    def update_category(
        self,
        session: Session,
        category_id: int,
        payload: CategoryUpdate,
        *,
        audit_service: AuditServiceProtocol,
        correlation_id: Optional[str] = None,
        workspace_header: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        commit: bool = True,
    ) -> Category:
        """Update category name/description and persist Tier 2 audit outbox atomically."""
        corr_id = (correlation_id or "").strip() or f"req-{uuid.uuid4().hex[:12]}"
        explicit_ws = payload.selected_workspace or workspace_header

        with _transaction(session, commit=commit):
            category = session.get(Category, category_id)
            if category is None:
                raise CategoryNotFoundError(f"Category {category_id} was not found.")

            duplicate = session.execute(
                select(Category.id).where(
                    func.lower(Category.name) == payload.name.lower(),
                    Category.id != category_id,
                )
            ).scalar_one_or_none()
            if duplicate is not None:
                raise CategoryConflictError(
                    f"Category with name '{payload.name}' already exists."
                )

            before_snapshot = _category_snapshot(category)
            category.name = payload.name
            category.description = payload.description
            if explicit_ws is not None:
                category.selected_workspace = explicit_ws
            category.action_source = payload.action_source
            if payload.operator_ref is not None:
                category.operator_ref = payload.operator_ref

            try:
                session.flush()
            except IntegrityError as exc:
                raise CategoryConflictError(
                    f"Category with name '{payload.name}' already exists."
                ) from exc

            event_key = idempotency_key or f"cat-update-{category.id}-{corr_id}-{uuid.uuid4().hex[:12]}"
            event = AuditEventPayload(
                module="M01",
                action="CATEGORY_UPDATED",
                entity_type="category",
                entity_id=str(category.id),
                outcome="SUCCESS",
                action_source=payload.action_source,
                selected_workspace=category.selected_workspace,
                operator_ref=category.operator_ref,
                correlation_id=corr_id,
                idempotency_key=event_key,
                before_values=before_snapshot,
                after_values=_category_snapshot(category),
            )
            audit_service.record_tier2_event(session, event)

        session.refresh(category)
        return category

    def update_category_status(
        self,
        session: Session,
        category_id: int,
        payload: CategoryStatusUpdate,
        *,
        audit_service: AuditServiceProtocol,
        correlation_id: Optional[str] = None,
        workspace_header: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        commit: bool = True,
    ) -> Category:
        """Soft-activate or soft-deactivate a category with Tier 2 audit outbox persistence."""
        corr_id = (correlation_id or "").strip() or f"req-{uuid.uuid4().hex[:12]}"
        explicit_ws = payload.selected_workspace or workspace_header

        with _transaction(session, commit=commit):
            category = session.get(Category, category_id)
            if category is None:
                raise CategoryNotFoundError(f"Category {category_id} was not found.")

            if category.is_active == payload.is_active:
                return category

            before_snapshot = _category_snapshot(category)
            category.is_active = payload.is_active
            if explicit_ws is not None:
                category.selected_workspace = explicit_ws
            category.action_source = payload.action_source
            if payload.operator_ref is not None:
                category.operator_ref = payload.operator_ref
            session.flush()

            action = "CATEGORY_REACTIVATED" if payload.is_active else "CATEGORY_DEACTIVATED"
            event_key = idempotency_key or f"cat-status-{category.id}-{corr_id}-{uuid.uuid4().hex[:12]}"
            event = AuditEventPayload(
                module="M01",
                action=action,
                entity_type="category",
                entity_id=str(category.id),
                outcome="SUCCESS",
                action_source=payload.action_source,
                selected_workspace=category.selected_workspace,
                operator_ref=category.operator_ref,
                correlation_id=corr_id,
                idempotency_key=event_key,
                before_values=before_snapshot,
                after_values=_category_snapshot(category),
            )
            audit_service.record_tier2_event(session, event)

        session.refresh(category)
        return category


category_service = CategoryService()

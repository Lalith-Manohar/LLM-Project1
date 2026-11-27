"""M01 Product Management & UoM Conversion service layer."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math
from typing import Any, Iterator, Optional
import uuid

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.uom_conversion import UomConversion
from app.schemas.product import (
    ProductCreate,
    ProductStatusUpdate,
    ProductUpdate,
    UomConversionCreate,
)
from app.services.contracts import (
    AuditEventPayload,
    AuditServiceProtocol,
    FractionalPolicyCheckerProtocol,
    InventoryInitializerProtocol,
)
from app.services.quantity_validation import (
    FractionalPolicyConflictError,
    QuantityValidationError,
    compute_exact_base_quantity,
    validate_disable_fractional_qty,
    validate_quantity_for_product,
)

ALLOWED_PRODUCT_SORT_FIELDS = {
    "stock_code": Product.stock_code,
    "description": Product.description,
    "current_unit_price": Product.current_unit_price,
    "created_at": Product.created_at,
}


class ProductNotFoundError(LookupError):
    """Raised when a requested product ID does not exist (maps to HTTP 404)."""


class ProductCategoryNotFoundError(LookupError):
    """Raised when a referenced category ID does not exist (maps to HTTP 404)."""


class ProductConflictError(ValueError):
    """Raised on duplicate SKU, inactive category, base_uom lock, or fractional conflict (409)."""


class ProductValidationError(ValueError):
    """Raised on invalid query/sort/filter/UoM parameters (maps to HTTP 422)."""


class FractionalCheckerUnavailableError(RuntimeError):
    """Raised when disabling allow_fractional_qty without M09/M05 checker configured (maps to 503)."""


@contextmanager
def _transaction(session: Session, *, commit: bool = True) -> Iterator[None]:
    """Transaction ownership contract matching Stage 2A CategoryService."""
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


def _product_snapshot(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "stock_code": product.stock_code,
        "description": product.description,
        "category_id": product.category_id,
        "base_uom": product.base_uom,
        "allow_fractional_qty": product.allow_fractional_qty,
        "current_unit_price": str(product.current_unit_price),
        "currency_code": product.currency_code,
        "is_active": product.is_active,
    }


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


_MYSQL_ER_DUP_ENTRY = 1062
_SQLITE_CONSTRAINT_UNIQUE = 2067


def _is_duplicate_key_integrity_error(
    exc: IntegrityError,
    *,
    expected_constraints: tuple[str, ...],
) -> bool:
    """Return True only for duplicate-key / unique-constraint violations; never mask NOT NULL/CHECK/FK."""
    orig = getattr(exc, "orig", None)
    if orig is None:
        return False

    args = getattr(orig, "args", ())
    if args and isinstance(args[0], int):
        # PyMySQL / MySQLdb structured errno: only 1062 (ER_DUP_ENTRY) is a duplicate-key conflict.
        if args[0] != _MYSQL_ER_DUP_ENTRY:
            return False
        msg = str(args[1]) if len(args) > 1 else str(orig)
        if any(name in msg for name in expected_constraints):
            return True
        # MySQL may omit or truncate constraint names in some configurations; 1062 is still duplicate-key.
        return "duplicate entry" in msg.lower()

    sqlite_code = getattr(orig, "sqlite_errorcode", None)
    if isinstance(sqlite_code, int):
        return sqlite_code == _SQLITE_CONSTRAINT_UNIQUE

    msg_lower = str(orig).lower()
    if any(token in msg_lower for token in ("not null", "check constraint", "foreign key")):
        return False
    return "unique constraint failed" in msg_lower or any(
        name.lower() in msg_lower for name in expected_constraints
    )


def _validate_category_reference(session: Session, category_id: Optional[int]) -> None:
    if category_id is None:
        return
    category = session.get(Category, category_id)
    if category is None:
        raise ProductCategoryNotFoundError(f"Referenced category {category_id} does not exist.")
    if not category.is_active:
        raise ProductConflictError(f"Referenced category {category_id} is inactive.")


def _has_product_references(session: Session, product_id: int) -> bool:
    """Check Schema v2.9 Section 6.14 dependent tables present in Stage 1 metadata."""
    has_uom = (
        session.execute(
            select(UomConversion.id).where(UomConversion.product_id == product_id).limit(1)
        ).scalar_one_or_none()
        is not None
    )
    if has_uom:
        return True
    has_inv = (
        session.execute(
            select(Inventory.id).where(Inventory.product_id == product_id).limit(1)
        ).scalar_one_or_none()
        is not None
    )
    return has_inv


def _capture_server_timestamp(session: Session, prior_active: Optional[UomConversion]) -> datetime:
    """Capture a single transaction timestamp (NOW(6) on MySQL, UTC microsecond fallback on SQLite)."""
    dialect_name = session.bind.dialect.name if session.bind is not None else ""
    if dialect_name == "mysql":
        tx_now = session.execute(text("SELECT NOW(6)")).scalar_one()
    else:
        tx_now = datetime.now(timezone.utc).replace(tzinfo=None)
        if prior_active is not None and tx_now <= prior_active.effective_from:
            tx_now = prior_active.effective_from + timedelta(microseconds=1)
    return tx_now


class ProductService:
    """Business service for M01 Product Management and UoM Conversions."""

    def create_product(
        self,
        session: Session,
        payload: ProductCreate,
        *,
        inventory_initializer: InventoryInitializerProtocol,
        audit_service: AuditServiceProtocol,
        correlation_id: Optional[str] = None,
        workspace_header: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        commit: bool = True,
    ) -> Product:
        """Create product + atomic initial M09 inventory row + Tier 2 audit outbox."""
        corr_id = (correlation_id or "").strip() or f"req-{uuid.uuid4().hex[:12]}"
        selected_ws = payload.selected_workspace or workspace_header

        with _transaction(session, commit=commit):
            _validate_category_reference(session, payload.category_id)

            existing = session.execute(
                select(Product.id).where(func.lower(Product.stock_code) == payload.stock_code.lower())
            ).scalar_one_or_none()
            if existing is not None:
                raise ProductConflictError(
                    f"Product with stock_code '{payload.stock_code}' already exists."
                )

            product = Product(
                stock_code=payload.stock_code,
                description=payload.description,
                category_id=payload.category_id,
                base_uom=payload.base_uom,
                allow_fractional_qty=payload.allow_fractional_qty,
                current_unit_price=payload.current_unit_price,
                currency_code=payload.currency_code,
                is_uci_baseline=payload.is_uci_baseline,
                is_active=True,
                selected_workspace=selected_ws,
                action_source=payload.action_source,
                operator_ref=payload.operator_ref,
            )
            session.add(product)
            try:
                session.flush()
            except IntegrityError as exc:
                raise ProductConflictError(
                    f"Product with stock_code '{payload.stock_code}' already exists."
                ) from exc

            # Atomic M09 onboarding inside the same SQLAlchemy transaction
            inventory_initializer.initialize_product_inventory(session, product_id=product.id)

            event_key = idempotency_key or f"prod-create-{product.id}-{corr_id}-{uuid.uuid4().hex[:12]}"
            audit_service.record_tier2_event(
                session,
                AuditEventPayload(
                    module="M01",
                    action="PRODUCT_CREATED",
                    entity_type="product",
                    entity_id=str(product.id),
                    outcome="SUCCESS",
                    action_source=payload.action_source,
                    selected_workspace=selected_ws,
                    operator_ref=payload.operator_ref,
                    correlation_id=corr_id,
                    idempotency_key=event_key,
                    before_values=None,
                    after_values=_product_snapshot(product),
                ),
            )

        session.refresh(product)
        return product

    def get_product(self, session: Session, product_id: int) -> Product:
        """Retrieve a single product by ID or raise ProductNotFoundError."""
        product = session.get(Product, product_id)
        if product is None:
            raise ProductNotFoundError(f"Product {product_id} was not found.")
        return product

    def list_products(
        self,
        session: Session,
        *,
        page: int = 1,
        page_size: int = 25,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        is_uci_baseline: Optional[bool] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        sort_by: str = "stock_code",
        sort_dir: str = "asc",
    ) -> tuple[list[Product], int, int, int, int]:
        """List products with allowlisted sorting, search, filtering, and pagination."""
        if page < 1:
            raise ProductValidationError("page must be greater than or equal to 1.")
        if page_size < 1 or page_size > 100:
            raise ProductValidationError("page_size must be between 1 and 100.")
        if sort_by not in ALLOWED_PRODUCT_SORT_FIELDS:
            raise ProductValidationError(
                f"Invalid sort_by '{sort_by}'. Allowed: {', '.join(sorted(ALLOWED_PRODUCT_SORT_FIELDS))}."
            )
        sort_dir_norm = sort_dir.lower()
        if sort_dir_norm not in ("asc", "desc"):
            raise ProductValidationError("sort_dir must be 'asc' or 'desc'.")
        if min_price is not None and max_price is not None and min_price > max_price:
            raise ProductValidationError("min_price cannot exceed max_price.")

        stmt = select(Product)
        count_stmt = select(func.count()).select_from(Product)

        conditions = []
        if category_id is not None:
            conditions.append(Product.category_id == category_id)
        if is_active is not None:
            conditions.append(Product.is_active == is_active)
        if is_uci_baseline is not None:
            conditions.append(Product.is_uci_baseline == is_uci_baseline)
        if min_price is not None:
            conditions.append(Product.current_unit_price >= min_price)
        if max_price is not None:
            conditions.append(Product.current_unit_price <= max_price)
        if search is not None and search.strip():
            escaped = f"%{_escape_like(search.strip())}%"
            conditions.append(
                or_(
                    Product.stock_code.ilike(escaped, escape="\\"),
                    Product.description.ilike(escaped, escape="\\"),
                )
            )

        for cond in conditions:
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        total = int(session.execute(count_stmt).scalar_one())
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        sort_col = ALLOWED_PRODUCT_SORT_FIELDS[sort_by]
        primary_order = sort_col.asc() if sort_dir_norm == "asc" else sort_col.desc()
        rows = list(
            session.execute(
                stmt.order_by(primary_order, Product.id.asc())
                .offset(offset)
                .limit(page_size)
            ).scalars()
        )
        return rows, total, page, page_size, total_pages

    def update_product(
        self,
        session: Session,
        product_id: int,
        payload: ProductUpdate,
        *,
        audit_service: AuditServiceProtocol,
        fractional_checker: Optional[FractionalPolicyCheckerProtocol] = None,
        correlation_id: Optional[str] = None,
        workspace_header: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        commit: bool = True,
    ) -> Product:
        """Update product details enforcing category validity, base_uom lock, and fractional policy."""
        corr_id = (correlation_id or "").strip() or f"req-{uuid.uuid4().hex[:12]}"
        explicit_ws = payload.selected_workspace or workspace_header

        with _transaction(session, commit=commit):
            if payload.allow_fractional_qty is False:
                # Acquire row-level lock on Product BEFORE checking fractional inventory/commitments.
                product = session.execute(
                    select(Product)
                    .where(Product.id == product_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                ).scalar_one_or_none()
            else:
                product = session.get(Product, product_id)
            if product is None:
                raise ProductNotFoundError(f"Product {product_id} was not found.")

            _validate_category_reference(session, payload.category_id)

            if payload.base_uom is not None and payload.base_uom != product.base_uom:
                if _has_product_references(session, product_id):
                    raise ProductConflictError(
                        f"products.base_uom cannot be modified once product {product_id} is referenced."
                    )

            if (
                payload.allow_fractional_qty is False
                and product.allow_fractional_qty is True
            ):
                if fractional_checker is None:
                    raise FractionalCheckerUnavailableError(
                        "M09/M05 FractionalPolicyCheckerProtocol is required to disable allow_fractional_qty."
                    )
                has_frac_inv, has_frac_commit = (
                    fractional_checker.has_fractional_inventory_or_commitments(
                        session,
                        product_id=product_id,
                    )
                )
                try:
                    validate_disable_fractional_qty(
                        has_fractional_inventory=has_frac_inv,
                        has_fractional_open_commitments=has_frac_commit,
                    )
                except FractionalPolicyConflictError as exc:
                    raise ProductConflictError(str(exc)) from exc

            before_snapshot = _product_snapshot(product)
            product.description = payload.description
            product.category_id = payload.category_id
            if payload.base_uom is not None:
                product.base_uom = payload.base_uom
            if payload.allow_fractional_qty is not None:
                product.allow_fractional_qty = payload.allow_fractional_qty
            product.current_unit_price = payload.current_unit_price
            if explicit_ws is not None:
                product.selected_workspace = explicit_ws
            product.action_source = payload.action_source
            if payload.operator_ref is not None:
                product.operator_ref = payload.operator_ref

            session.flush()

            event_key = idempotency_key or f"prod-update-{product.id}-{corr_id}-{uuid.uuid4().hex[:12]}"
            audit_service.record_tier2_event(
                session,
                AuditEventPayload(
                    module="M01",
                    action="PRODUCT_UPDATED",
                    entity_type="product",
                    entity_id=str(product.id),
                    outcome="SUCCESS",
                    action_source=payload.action_source,
                    selected_workspace=product.selected_workspace,
                    operator_ref=product.operator_ref,
                    correlation_id=corr_id,
                    idempotency_key=event_key,
                    before_values=before_snapshot,
                    after_values=_product_snapshot(product),
                ),
            )

        session.refresh(product)
        return product

    def update_product_status(
        self,
        session: Session,
        product_id: int,
        payload: ProductStatusUpdate,
        *,
        audit_service: AuditServiceProtocol,
        correlation_id: Optional[str] = None,
        workspace_header: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        commit: bool = True,
    ) -> Product:
        """Soft-activate or soft-deactivate a product with Tier 2 audit outbox persistence."""
        corr_id = (correlation_id or "").strip() or f"req-{uuid.uuid4().hex[:12]}"
        explicit_ws = payload.selected_workspace or workspace_header

        with _transaction(session, commit=commit):
            product = session.get(Product, product_id)
            if product is None:
                raise ProductNotFoundError(f"Product {product_id} was not found.")

            if payload.is_active and product.lifecycle_stage == "Discontinued":
                raise ProductConflictError(
                    "Discontinued products cannot be reactivated via status toggle (DDR-08)."
                )

            if product.is_active == payload.is_active:
                return product

            before_snapshot = _product_snapshot(product)
            product.is_active = payload.is_active
            if explicit_ws is not None:
                product.selected_workspace = explicit_ws
            product.action_source = payload.action_source
            if payload.operator_ref is not None:
                product.operator_ref = payload.operator_ref
            session.flush()

            action = "PRODUCT_REACTIVATED" if payload.is_active else "PRODUCT_DEACTIVATED"
            event_key = idempotency_key or f"prod-status-{product.id}-{corr_id}-{uuid.uuid4().hex[:12]}"
            audit_service.record_tier2_event(
                session,
                AuditEventPayload(
                    module="M01",
                    action=action,
                    entity_type="product",
                    entity_id=str(product.id),
                    outcome="SUCCESS",
                    action_source=payload.action_source,
                    selected_workspace=product.selected_workspace,
                    operator_ref=product.operator_ref,
                    correlation_id=corr_id,
                    idempotency_key=event_key,
                    before_values=before_snapshot,
                    after_values=_product_snapshot(product),
                ),
            )

        session.refresh(product)
        return product

    def list_uom_conversions(self, session: Session, product_id: int) -> list[UomConversion]:
        """List all effective-dated UoM conversions for a product."""
        product = session.get(Product, product_id)
        if product is None:
            raise ProductNotFoundError(f"Product {product_id} was not found.")
        return list(
            session.execute(
                select(UomConversion)
                .where(UomConversion.product_id == product_id)
                .order_by(UomConversion.uom_code.asc(), UomConversion.effective_from.desc())
            ).scalars()
        )

    def rollover_uom_conversion(
        self,
        session: Session,
        product_id: int,
        payload: UomConversionCreate,
        *,
        audit_service: AuditServiceProtocol,
        correlation_id: Optional[str] = None,
        workspace_header: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        commit: bool = True,
    ) -> UomConversion:
        """Immediate half-open [tx_now, NULL) UoM conversion rollover with Tier 1 fail-closed audit."""
        corr_id = (correlation_id or "").strip() or f"req-{uuid.uuid4().hex[:12]}"
        selected_ws = payload.selected_workspace or workspace_header

        with _transaction(session, commit=commit):
            product = session.execute(
                select(Product).where(Product.id == product_id).with_for_update()
            ).scalar_one_or_none()
            if product is None:
                raise ProductNotFoundError(f"Product {product_id} was not found.")

            if payload.uom_code.lower() == product.base_uom.lower():
                raise ProductValidationError(
                    f"uom_code '{payload.uom_code}' cannot match base_uom '{product.base_uom}'."
                )

            existing_rows = list(
                session.execute(
                    select(UomConversion)
                    .where(
                        UomConversion.product_id == product_id,
                        UomConversion.uom_code == payload.uom_code,
                    )
                    .order_by(UomConversion.id.asc())
                    .with_for_update()
                ).scalars()
            )
            prior_active = next((row for row in existing_rows if row.is_active), None)
            tx_now = _capture_server_timestamp(session, prior_active)

            closed_ends = [
                row.effective_to
                for row in existing_rows
                if not row.is_active and row.effective_to is not None
            ]
            if closed_ends and tx_now < max(closed_ends):
                raise ProductConflictError(
                    "UoM rollover timestamp overlaps an existing closed conversion window."
                )

            if prior_active is not None:
                if tx_now <= prior_active.effective_from:
                    raise ProductConflictError(
                        "Concurrent UoM rollover timestamp conflict; retry rollover."
                    )
                before_snapshot = {
                    "id": prior_active.id,
                    "uom_code": prior_active.uom_code,
                    "conversion_to_base": str(prior_active.conversion_to_base),
                    "is_active": True,
                }
                prior_active.effective_to = tx_now
                prior_active.is_active = False
                session.flush()
            else:
                before_snapshot = None

            new_conv = UomConversion(
                product_id=product_id,
                uom_code=payload.uom_code,
                conversion_to_base=payload.conversion_to_base,
                effective_from=tx_now,
                effective_to=None,
                is_active=True,
                selected_workspace=selected_ws,
                action_source=payload.action_source,
                operator_ref=payload.operator_ref,
            )
            session.add(new_conv)
            try:
                session.flush()
            except IntegrityError as exc:
                if _is_duplicate_key_integrity_error(
                    exc,
                    expected_constraints=("uq_uom_one_active", "uq_uom_product_code_eff"),
                ):
                    raise ProductConflictError(
                        f"Concurrent UoM conversion conflict for product {product_id} and uom_code '{payload.uom_code}'."
                    ) from exc
                raise

            event_key = idempotency_key or f"uom-rollover-{new_conv.id}-{corr_id}-{uuid.uuid4().hex[:12]}"
            try:
                audit_service.record_tier1_event(
                    session,
                    AuditEventPayload(
                        module="M01",
                        action="UOM_CONVERSION_UPDATED",
                        entity_type="uom_conversion",
                        entity_id=str(new_conv.id),
                        outcome="SUCCESS",
                        action_source=payload.action_source,
                        selected_workspace=selected_ws,
                        operator_ref=payload.operator_ref,
                        correlation_id=corr_id,
                        idempotency_key=event_key,
                        before_values=before_snapshot,
                        after_values={
                            "id": new_conv.id,
                            "product_id": product_id,
                            "uom_code": new_conv.uom_code,
                            "conversion_to_base": str(new_conv.conversion_to_base),
                            "is_active": True,
                        },
                    ),
                )
            except IntegrityError as exc:
                if _is_duplicate_key_integrity_error(
                    exc,
                    expected_constraints=("uq_audit_idempotency",),
                ):
                    raise ProductConflictError(
                        f"Duplicate UoM rollover audit idempotency key '{event_key}'."
                    ) from exc
                raise

        session.refresh(new_conv)
        return new_conv

    def validate_product_quantity(
        self,
        session: Session,
        product_id: int,
        quantity: Any,
    ) -> Decimal:
        """Validate a commercial quantity against the product's allow_fractional_qty policy."""
        product = self.get_product(session, product_id)
        try:
            return validate_quantity_for_product(
                quantity,
                allow_fractional_qty=product.allow_fractional_qty,
            )
        except QuantityValidationError as exc:
            raise ProductValidationError(str(exc)) from exc

    def convert_product_quantity_to_base(
        self,
        session: Session,
        product_id: int,
        quantity: Any,
        *,
        uom_code: Optional[str] = None,
        at_timestamp: Optional[datetime] = None,
    ) -> Decimal:
        """Convert a product quantity to base_uom using active or point-in-time [from, to) rule."""
        product = self.get_product(session, product_id)
        if uom_code is None or uom_code.strip().lower() == product.base_uom.lower():
            factor = Decimal("1.000000")
        else:
            code = uom_code.strip()
            if at_timestamp is None:
                conv = session.execute(
                    select(UomConversion).where(
                        UomConversion.product_id == product_id,
                        UomConversion.uom_code == code,
                        UomConversion.is_active.is_(True),
                    )
                ).scalar_one_or_none()
            else:
                conv = session.execute(
                    select(UomConversion).where(
                        UomConversion.product_id == product_id,
                        UomConversion.uom_code == code,
                        UomConversion.effective_from <= at_timestamp,
                        or_(
                            UomConversion.effective_to.is_(None),
                            at_timestamp < UomConversion.effective_to,
                        ),
                    )
                ).scalar_one_or_none()
            if conv is None:
                raise ProductNotFoundError(
                    f"No UoM conversion found for product {product_id} and uom_code '{code}'."
                )
            factor = conv.conversion_to_base

        try:
            return compute_exact_base_quantity(
                quantity,
                factor,
                allow_fractional_qty=product.allow_fractional_qty,
            )
        except QuantityValidationError as exc:
            raise ProductValidationError(str(exc)) from exc


product_service = ProductService()

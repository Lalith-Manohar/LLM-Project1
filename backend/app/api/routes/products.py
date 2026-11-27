"""M01 Product Management & UoM Conversion FastAPI routes (/api/v1/products)."""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api.routes.categories import _normalize_workspace_header, get_audit_service
from app.db.session import get_db
from app.schemas.product import (
    PaginatedProductResponse,
    ProductCreate,
    ProductResponse,
    ProductStatusUpdate,
    ProductUpdate,
    UomConversionCreate,
    UomConversionResponse,
)
from app.services.contracts import (
    AuditServiceProtocol,
    FractionalPolicyCheckerProtocol,
    InventoryInitializerProtocol,
)
from app.services.product_service import (
    FractionalCheckerUnavailableError,
    ProductCategoryNotFoundError,
    ProductConflictError,
    ProductNotFoundError,
    ProductValidationError,
    product_service,
)

router = APIRouter(prefix="/products", tags=["Products"])


def get_inventory_initializer() -> InventoryInitializerProtocol:
    """Dependency placeholder for M09 InventoryInitializerProtocol until M09 is wired."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="M09 inventory initializer is not yet configured.",
    )


def get_fractional_policy_checker() -> Optional[FractionalPolicyCheckerProtocol]:
    """Optional dependency placeholder for M09/M05 fractional balance/commitment checks."""
    return None


@router.get(
    "",
    response_model=PaginatedProductResponse,
    summary="List products",
)
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    category_id: Optional[int] = Query(default=None, ge=1),
    is_active: Optional[bool] = Query(default=None),
    is_uci_baseline: Optional[bool] = Query(default=None),
    min_price: Optional[Decimal] = Query(default=None, ge=Decimal("0.00")),
    max_price: Optional[Decimal] = Query(default=None, ge=Decimal("0.00")),
    sort_by: str = Query(default="stock_code"),
    sort_dir: str = Query(default="asc"),
    db: Session = Depends(get_db),
) -> PaginatedProductResponse:
    try:
        items, total, cur_page, cur_size, total_pages = product_service.list_products(
            db,
            page=page,
            page_size=page_size,
            search=search,
            category_id=category_id,
            is_active=is_active,
            is_uci_baseline=is_uci_baseline,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except ProductValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))

    return PaginatedProductResponse(
        items=[ProductResponse.model_validate(item) for item in items],
        total=total,
        page=cur_page,
        page_size=cur_size,
        total_pages=total_pages,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
)
def get_product(
    product_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> ProductResponse:
    try:
        product = product_service.get_product(db, product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return ProductResponse.model_validate(product)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product with atomic initial inventory",
)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    inventory_initializer: InventoryInitializerProtocol = Depends(get_inventory_initializer),
    audit_service: AuditServiceProtocol = Depends(get_audit_service),
    x_nexora_workspace: Optional[str] = Header(default=None),
    x_correlation_id: Optional[str] = Header(default=None),
) -> ProductResponse:
    try:
        product = product_service.create_product(
            db,
            payload,
            inventory_initializer=inventory_initializer,
            audit_service=audit_service,
            correlation_id=x_correlation_id,
            workspace_header=_normalize_workspace_header(x_nexora_workspace),
        )
    except ProductCategoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ProductConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ProductValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return ProductResponse.model_validate(product)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update product details",
)
def update_product(
    payload: ProductUpdate,
    product_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    audit_service: AuditServiceProtocol = Depends(get_audit_service),
    fractional_checker: Optional[FractionalPolicyCheckerProtocol] = Depends(
        get_fractional_policy_checker
    ),
    x_nexora_workspace: Optional[str] = Header(default=None),
    x_correlation_id: Optional[str] = Header(default=None),
) -> ProductResponse:
    try:
        product = product_service.update_product(
            db,
            product_id,
            payload,
            audit_service=audit_service,
            fractional_checker=fractional_checker,
            correlation_id=x_correlation_id,
            workspace_header=_normalize_workspace_header(x_nexora_workspace),
        )
    except (ProductNotFoundError, ProductCategoryNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ProductConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ProductValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    except FractionalCheckerUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return ProductResponse.model_validate(product)


@router.patch(
    "/{product_id}/status",
    response_model=ProductResponse,
    summary="Activate or deactivate product",
)
def update_product_status(
    payload: ProductStatusUpdate,
    product_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    audit_service: AuditServiceProtocol = Depends(get_audit_service),
    x_nexora_workspace: Optional[str] = Header(default=None),
    x_correlation_id: Optional[str] = Header(default=None),
) -> ProductResponse:
    try:
        product = product_service.update_product_status(
            db,
            product_id,
            payload,
            audit_service=audit_service,
            correlation_id=x_correlation_id,
            workspace_header=_normalize_workspace_header(x_nexora_workspace),
        )
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ProductConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ProductValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return ProductResponse.model_validate(product)


@router.get(
    "/{product_id}/uom-conversions",
    response_model=list[UomConversionResponse],
    summary="List UoM conversions for a product",
)
def list_uom_conversions(
    product_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> list[UomConversionResponse]:
    try:
        rows = product_service.list_uom_conversions(db, product_id)
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return [UomConversionResponse.model_validate(row) for row in rows]


@router.post(
    "/{product_id}/uom-conversions",
    response_model=UomConversionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or immediately roll over a product UoM conversion",
)
def rollover_uom_conversion(
    payload: UomConversionCreate,
    product_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    audit_service: AuditServiceProtocol = Depends(get_audit_service),
    x_nexora_workspace: Optional[str] = Header(default=None),
    x_correlation_id: Optional[str] = Header(default=None),
) -> UomConversionResponse:
    try:
        conv = product_service.rollover_uom_conversion(
            db,
            product_id,
            payload,
            audit_service=audit_service,
            correlation_id=x_correlation_id,
            workspace_header=_normalize_workspace_header(x_nexora_workspace),
        )
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except ProductConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ProductValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return UomConversionResponse.model_validate(conv)

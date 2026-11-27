"""M01 Category Management FastAPI routes (/api/v1/categories)."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.db.base import WORKSPACE_VALUES
from app.db.session import get_db
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryStatusUpdate,
    CategoryUpdate,
    PaginatedCategoryResponse,
)
from app.services.category_service import (
    CategoryConflictError,
    CategoryNotFoundError,
    CategoryValidationError,
    category_service,
)
from app.services.contracts import AuditServiceProtocol

router = APIRouter(prefix="/categories", tags=["Categories"])

_WORKSPACE_MAP = {
    "store manager (admin)": "store_manager",
    "store_manager": "store_manager",
    "inventory staff": "inventory_staff",
    "inventory_staff": "inventory_staff",
    "purchase manager": "purchase_manager",
    "purchase_manager": "purchase_manager",
    "finance staff": "finance_staff",
    "finance_staff": "finance_staff",
}


def get_audit_service() -> AuditServiceProtocol:
    """Dependency placeholder for SYS-02 AuditServiceProtocol until SYS-02 is wired."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="SYS-02 audit service is not yet configured.",
    )


def _normalize_workspace_header(raw_header: Optional[str]) -> Optional[str]:
    if not raw_header:
        return None
    normalized = _WORKSPACE_MAP.get(raw_header.strip().lower())
    return normalized if normalized in WORKSPACE_VALUES else None


@router.get(
    "",
    response_model=PaginatedCategoryResponse,
    summary="List product categories",
)
def list_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    db: Session = Depends(get_db),
) -> PaginatedCategoryResponse:
    try:
        items, total, cur_page, cur_size, total_pages = category_service.list_categories(
            db,
            page=page,
            page_size=page_size,
            search=search,
            is_active=is_active,
        )
    except CategoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))

    return PaginatedCategoryResponse(
        items=[CategoryResponse.model_validate(item) for item in items],
        total=total,
        page=cur_page,
        page_size=cur_size,
        total_pages=total_pages,
    )


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Get category by ID",
)
def get_category(
    category_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
) -> CategoryResponse:
    try:
        category = category_service.get_category(db, category_id)
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return CategoryResponse.model_validate(category)


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create product category",
)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    audit_service: AuditServiceProtocol = Depends(get_audit_service),
    x_nexora_workspace: Optional[str] = Header(default=None),
    x_correlation_id: Optional[str] = Header(default=None),
) -> CategoryResponse:
    try:
        category = category_service.create_category(
            db,
            payload,
            audit_service=audit_service,
            correlation_id=x_correlation_id,
            workspace_header=_normalize_workspace_header(x_nexora_workspace),
        )
    except CategoryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except CategoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return CategoryResponse.model_validate(category)


@router.put(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Update product category",
)
def update_category(
    payload: CategoryUpdate,
    category_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    audit_service: AuditServiceProtocol = Depends(get_audit_service),
    x_nexora_workspace: Optional[str] = Header(default=None),
    x_correlation_id: Optional[str] = Header(default=None),
) -> CategoryResponse:
    try:
        category = category_service.update_category(
            db,
            category_id,
            payload,
            audit_service=audit_service,
            correlation_id=x_correlation_id,
            workspace_header=_normalize_workspace_header(x_nexora_workspace),
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except CategoryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except CategoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return CategoryResponse.model_validate(category)


@router.patch(
    "/{category_id}/status",
    response_model=CategoryResponse,
    summary="Activate or deactivate product category",
)
def update_category_status(
    payload: CategoryStatusUpdate,
    category_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    audit_service: AuditServiceProtocol = Depends(get_audit_service),
    x_nexora_workspace: Optional[str] = Header(default=None),
    x_correlation_id: Optional[str] = Header(default=None),
) -> CategoryResponse:
    try:
        category = category_service.update_category_status(
            db,
            category_id,
            payload,
            audit_service=audit_service,
            correlation_id=x_correlation_id,
            workspace_header=_normalize_workspace_header(x_nexora_workspace),
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except CategoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return CategoryResponse.model_validate(category)

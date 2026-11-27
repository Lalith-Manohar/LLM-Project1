"""FastAPI Routes for M08 — Product Lifecycle Intelligence.

Exposes:
  - /api/v1/intelligence/lifecycle
  - /api/v1/intelligence/lifecycle/{product_id}
  - /api/v1/intelligence/lifecycle/{product_id}/history
  - /api/v1/intelligence/lifecycle/evaluate
  - /api/v1/intelligence/lifecycle/{product_id}/discontinue
  - /api/v1/intelligence/dead-stock
  - /api/v1/settings/lifecycle (GET / PUT)
  - /api/v1/settings/lifecycle/reset (POST)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.core.interfaces import AuditWriteError
from app.core.provenance import RequestProvenance, get_request_provenance
from app.schemas.lifecycle import (
    DeadStockResponse,
    DiscontinueProductRequest,
    DiscontinueProductResponse,
    LifecycleDetailResponse,
    LifecycleEvaluationRequest,
    LifecycleEvaluationResponse,
    LifecycleHistoryResponse,
    LifecycleListResponse,
    LifecycleSettingsResetRequest,
    LifecycleSettingsResponse,
    LifecycleSettingsUpdateRequest,
    LifecycleSourceFilter,
    LifecycleStage,
)
from app.services.lifecycle_service import (
    LifecycleGovernanceError,
    LifecycleNotFoundError,
    LifecycleValidationError,
    lifecycle_service,
)

logger = logging.getLogger(__name__)

intelligence_router = APIRouter(prefix="/intelligence", tags=["M08 Product Lifecycle Intelligence"])
settings_router = APIRouter(prefix="/settings", tags=["M08 Lifecycle Settings"])


def _handle_lifecycle_errors(exc: Exception) -> HTTPException:
    if isinstance(exc, LifecycleNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, LifecycleValidationError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, LifecycleGovernanceError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, AuditWriteError):
        logger.error("DDR-10 Tier 1 fail-closed audit failure in M08: %s", exc)
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Critical audit logging failed; operation was rolled back atomically (DDR-10).",
        )
    logger.error("Unexpected M08 lifecycle error: %s", exc, exc_info=True)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred in Product Lifecycle Intelligence.",
    )


@intelligence_router.get(
    "/lifecycle",
    response_model=LifecycleListResponse,
    summary="Filterable SKU Lifecycle Portfolio & Stage Distribution",
    description=(
        "Returns portfolio stage counts across the 5 canonical DDR-08 stages "
        "(Introduction, Growth, Maturity, Decline, Discontinued) and paginated SKU rows."
    ),
)
def list_product_lifecycle(
    source_origin: LifecycleSourceFilter = Query(default="all"),
    stage: Optional[LifecycleStage] = Query(default=None, description="Filter by canonical DDR-08 lifecycle stage"),
    is_dormant_stock: Optional[bool] = Query(default=None, description="Filter active SKUs flagged as dormant stock"),
    search: Optional[str] = Query(default=None, description="Substring match on stock_code or description"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> LifecycleListResponse:
    try:
        return lifecycle_service.list_lifecycle(
            provenance=provenance,
            source_origin=source_origin,
            stage=stage,
            is_dormant_stock=is_dormant_stock,
            search=search,
            page=page,
            page_size=page_size,
        )
    except Exception as exc:
        raise _handle_lifecycle_errors(exc) from exc


@intelligence_router.post(
    "/lifecycle/evaluate",
    response_model=LifecycleEvaluationResponse,
    summary="Run Lifecycle Classification with DDR-08 Anti-Flicker Hysteresis",
    description=(
        "Evaluates SKUs against bounded operational_settings thresholds, appends immutable "
        "product_lifecycle_snapshots, enforces anti-flicker hysteresis, never auto-assigns "
        "'Discontinued', and dispatches deduplicated SYS-03 alerts on decline/dormancy."
    ),
)
def run_lifecycle_evaluation(
    request: LifecycleEvaluationRequest = Body(default_factory=LifecycleEvaluationRequest),
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> LifecycleEvaluationResponse:
    try:
        return lifecycle_service.evaluate_lifecycle(request=request, provenance=provenance)
    except Exception as exc:
        raise _handle_lifecycle_errors(exc) from exc


@intelligence_router.get(
    "/dead-stock",
    response_model=DeadStockResponse,
    summary="Dormant / Dead-Stock Active Inventory Review",
    description=(
        "Lists active SKUs holding positive inventory beyond the configured inactivity threshold "
        "with exact DECIMAL capital valuation. Separated strictly from manual Discontinued status (DDR-08, EXCL-04)."
    ),
)
def list_dead_stock(
    source_origin: LifecycleSourceFilter = Query(default="all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> DeadStockResponse:
    try:
        return lifecycle_service.get_dead_stock(
            provenance=provenance,
            source_origin=source_origin,
            page=page,
            page_size=page_size,
        )
    except Exception as exc:
        raise _handle_lifecycle_errors(exc) from exc


@intelligence_router.get(
    "/lifecycle/{product_id}",
    response_model=LifecycleDetailResponse,
    summary="Detailed SKU Lifecycle Trajectory & Classification Breakdown",
    description="Accepts numeric product_id or stock_code and returns trajectory metrics plus snapshot history.",
)
def get_product_lifecycle_detail(
    product_id: str,
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> LifecycleDetailResponse:
    try:
        return lifecycle_service.get_sku_detail(
            product_identifier=product_id,
            provenance=provenance,
        )
    except Exception as exc:
        raise _handle_lifecycle_errors(exc) from exc


@intelligence_router.get(
    "/lifecycle/{product_id}/history",
    response_model=LifecycleHistoryResponse,
    summary="Immutable Append-Only Lifecycle Snapshot History",
)
def get_product_lifecycle_history(
    product_id: str,
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> LifecycleHistoryResponse:
    try:
        return lifecycle_service.get_sku_history(
            product_identifier=product_id,
            provenance=provenance,
        )
    except Exception as exc:
        raise _handle_lifecycle_errors(exc) from exc


@intelligence_router.patch(
    "/lifecycle/{product_id}/discontinue",
    response_model=DiscontinueProductResponse,
    summary="Explicit Authorized Manual Discontinuation (Store Manager Governance)",
    description=(
        "Transitions a product to 'Discontinued' strictly upon explicit Store Manager (Admin) "
        "confirmation with mandatory reason and DDR-10 Tier 1 fail-closed atomic audit logging."
    ),
)
def discontinue_product_lifecycle(
    product_id: str,
    request: DiscontinueProductRequest,
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> DiscontinueProductResponse:
    try:
        return lifecycle_service.discontinue_product(
            product_identifier=product_id,
            request=request,
            provenance=provenance,
        )
    except Exception as exc:
        raise _handle_lifecycle_errors(exc) from exc


@settings_router.get(
    "/lifecycle",
    response_model=LifecycleSettingsResponse,
    summary="Inspect Bounded Lifecycle Threshold Settings",
)
def get_lifecycle_settings(
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> LifecycleSettingsResponse:
    try:
        return lifecycle_service.get_settings(provenance=provenance)
    except Exception as exc:
        raise _handle_lifecycle_errors(exc) from exc


@settings_router.put(
    "/lifecycle",
    response_model=LifecycleSettingsResponse,
    summary="Update Bounded Lifecycle Threshold Settings (Forward-Only, Tier 1 Audited)",
)
def update_lifecycle_settings(
    request: LifecycleSettingsUpdateRequest,
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> LifecycleSettingsResponse:
    try:
        return lifecycle_service.update_settings(request=request, provenance=provenance)
    except Exception as exc:
        raise _handle_lifecycle_errors(exc) from exc


@settings_router.post(
    "/lifecycle/reset",
    response_model=LifecycleSettingsResponse,
    summary="Reset Lifecycle Threshold Settings to System Defaults (Tier 1 Audited)",
)
def reset_lifecycle_settings(
    request: LifecycleSettingsResetRequest = Body(default_factory=LifecycleSettingsResetRequest),
    provenance: RequestProvenance = Depends(get_request_provenance),
) -> LifecycleSettingsResponse:
    try:
        return lifecycle_service.reset_settings(request=request, provenance=provenance)
    except Exception as exc:
        raise _handle_lifecycle_errors(exc) from exc

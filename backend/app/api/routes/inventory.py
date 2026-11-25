"""Inventory Management & Purchasing API routes.

Exposes RESTful endpoints under /api/v1/inventory for generating automated replenishment
recommendations, target stock calculations, and purchase order decision support.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.inventory import (
    InventoryRecommendationRequest,
    InventoryRecommendationResponse
)
from app.services.inventory_service import inventory_service
from app.services.historical_data_service import (
    HistoricalDataNotFoundError,
    InsufficientHistoryError,
    DatasetUnavailableError
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post(
    "/recommend",
    response_model=InventoryRecommendationResponse,
    summary="Generate inventory replenishment and purchase recommendation",
    description=(
        "Translates machine learning demand forecasts into an explainable purchase recommendation "
        "based on current on-hand stock, supplier lead times, review cycles, and safety stock days."
    ),
    responses={
        200: {"description": "Replenishment recommendation generated successfully"},
        404: {"description": "Product SKU not found in historical catalog"},
        422: {"description": "Validation error or insufficient historical sales data (< 29 days)"},
        503: {"description": "Forecasting service or historical dataset unavailable"}
    }
)
def get_inventory_recommendation(
    request: InventoryRecommendationRequest
) -> InventoryRecommendationResponse:
    """Generates an inventory replenishment recommendation with transparent mathematical explanation."""
    try:
        return inventory_service.get_recommendation(request)
    except HistoricalDataNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientHistoryError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except DatasetUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Historical dataset unavailable: {str(e)}"
        )
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Forecasting service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected failure generating inventory recommendation for '{request.stock_code}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inventory recommendation calculation failed: {str(e)}"
        )

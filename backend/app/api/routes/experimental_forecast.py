"""Experimental Demand Forecasting API endpoints (Task 12 Models).

Exposes RESTful endpoints under /api/v1/experimental for generating multi-horizon
demand forecasts using the Task 12 models trained on the 2-year Online Retail II
dataset with chronological TargetEncoder, point-in-time pricing, and 60-day coverage.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Response

from app.schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    SupportedHorizonsResponse,
    ComponentReadiness,
    ReadinessResponse
)
from app.services.experimental_prediction_service import experimental_prediction_service
from app.services.historical_data_service import (
    historical_data_service,
    HistoricalDataNotFoundError,
    InsufficientHistoryError,
    DatasetUnavailableError
)
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experimental", tags=["Experimental Forecast"])


@router.get(
    "/ready",
    summary="Experimental service readiness probe",
    description="Verifies that Task 12 experimental models and the historical dataset are loaded and ready."
)
def get_experimental_readiness(response: Response) -> Dict[str, Any]:
    """Returns readiness status for Task 12 experimental forecasting subsystem."""
    exp_status = experimental_prediction_service.get_status()
    data_status = historical_data_service.get_status()

    is_ready = bool(exp_status["ready"] and data_status["ready"])
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "service": "experimental_forecast",
        "experimental_models": exp_status,
        "historical_data": data_status
    }


@router.get(
    "/forecast/horizons",
    summary="Get experimental supported forecast horizons",
    description="Returns the list and candidate model definitions for Task 12 experimental horizons."
)
def get_experimental_supported_horizons() -> Dict[str, Any]:
    """Returns supported forecasting horizons and model architectures for Task 12."""
    return experimental_prediction_service.get_supported_horizons()


@router.get(
    "/forecast/model-metrics",
    summary="Get Task 12 experimental evaluation benchmark metrics",
    description="Returns chronological time-series cross-validation and holdout error metrics for Task 12 models."
)
def get_experimental_model_metrics() -> Dict[str, Any]:
    """Returns documented model metrics and holdout benchmarks for Task 12 models."""
    if not experimental_prediction_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Experimental model service is not ready: {experimental_prediction_service.load_error or 'Metadata uninitialized'}"
        )
    try:
        return experimental_prediction_service.get_model_metrics()
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Experimental model metadata is not available: {str(e)}"
        )


@router.get(
    "/forecast/model-info",
    summary="Get Task 12 experimental runtime model architecture",
    description="Returns active Task 12 model architectures, 20-column feature contract, and encoding configuration."
)
def get_experimental_model_info() -> Dict[str, Any]:
    """Returns active Task 12 pipeline configurations and runtime status."""
    if not experimental_prediction_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Experimental model service is not ready: {experimental_prediction_service.load_error or 'Models uninitialized'}"
        )
    try:
        return experimental_prediction_service.get_model_info()
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Experimental model metadata is not available: {str(e)}"
        )


@router.post(
    "/forecast/predict",
    response_model=ForecastResponse,
    summary="Generate multi-horizon demand forecast using Task 12 experimental models",
    description="Submits an SKU to generate estimated demand over requested horizons using the Task 12 best models."
)
def predict_experimental_demand(request: ForecastRequest) -> ForecastResponse:
    """Generates demand forecasts using Task 12 models for requested horizons (7, 15, 30, 90 days)."""
    # 1. Pre-execution readiness validation
    if not experimental_prediction_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Experimental forecasting models are not ready: {experimental_prediction_service.load_error or 'Service uninitialized'}"
        )
    if request.features is None and not historical_data_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Historical sales dataset is not ready: {historical_data_service._load_error or 'Dataset uninitialized'}"
        )

    # 2. Execution and granular error handling
    try:
        response = experimental_prediction_service.get_forecast(request)
        return response
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
            detail=f"Experimental forecasting service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected experimental prediction failure for SKU '{request.stock_code}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Experimental inference execution failed: {str(e)}"
        )


@router.post(
    "/forecast",
    response_model=ForecastResponse,
    summary="Generate multi-horizon demand forecast (Experimental root alias)",
    description="Alias for /api/v1/experimental/forecast/predict.",
    include_in_schema=True
)
def predict_experimental_demand_alias(request: ForecastRequest) -> ForecastResponse:
    """Alias for experimental forecast prediction."""
    return predict_experimental_demand(request)


@router.post(
    "/forecast/",
    response_model=ForecastResponse,
    include_in_schema=False
)
def predict_experimental_demand_slash_alias(request: ForecastRequest) -> ForecastResponse:
    """Trailing slash alias for experimental forecast prediction."""
    return predict_experimental_demand(request)

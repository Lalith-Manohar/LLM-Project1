"""Demand Forecasting API endpoints.

Exposes RESTful endpoints under /api/v1/forecast for generating multi-horizon
demand forecasts, querying supported horizons, inspecting evaluation metrics,
and retrieving runtime model metadata.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from app.schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    SupportedHorizonsResponse,
    ModelMetricsResponse,
    ModelInfoResponse
)
from app.services.prediction_service import prediction_service
from app.services.store_wide_service import store_wide_service
from app.services.historical_data_service import (
    historical_data_service,
    HistoricalDataNotFoundError,
    InsufficientHistoryError,
    DatasetUnavailableError
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get(
    "/horizons",
    response_model=SupportedHorizonsResponse,
    summary="Get supported forecast horizons",
    description="Returns the list and business definitions of forecasting horizons supported by NEXORA."
)
def get_supported_horizons():
    """Returns supported forecasting horizons (7, 15, 30, and 90 days)."""
    return prediction_service.get_supported_horizons()


@router.get(
    "/model-metrics",
    summary="Get model evaluation benchmark metrics",
    description="Returns out-of-time chronological backtesting error metrics (MAE, RMSE, WAPE) across all models."
)
def get_model_metrics() -> Dict[str, Any]:
    """Returns documented model comparison matrix and error benchmarks."""
    if not prediction_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model service is not ready: {prediction_service.load_error or 'Metadata uninitialized'}"
        )
    try:
        return prediction_service.get_model_metrics()
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model metadata is not available: {str(e)}"
        )


@router.get(
    "/model-info",
    summary="Get runtime model registry architecture",
    description="Returns active model architectures, feature column specifications, and encoding configuration."
)
def get_model_info() -> Dict[str, Any]:
    """Returns active pipeline configurations and runtime status."""
    if not prediction_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model service is not ready: {prediction_service.load_error or 'Models uninitialized'}"
        )
    try:
        return prediction_service.get_model_info()
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model metadata is not available: {str(e)}"
        )


@router.post(
    "/",
    response_model=ForecastResponse,
    summary="Generate multi-horizon demand forecast",
    description="Submits an SKU to generate estimated demand over requested horizons from historical CSV data (or manual features for testing)."
)
def predict_demand(request: ForecastRequest) -> ForecastResponse:
    """Generates demand forecasts for one or more requested horizons (7, 15, 30, 90 days)."""
    # 1. Pre-execution readiness validation
    if not prediction_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Forecasting models are not ready: {prediction_service.load_error or 'Service uninitialized'}"
        )
    if request.features is None and not historical_data_service.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Historical sales dataset is not ready: {historical_data_service._load_error or 'Dataset uninitialized'}"
        )

    # 2. Execution and granular error handling
    try:
        response = prediction_service.get_forecast(request)
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
            detail=f"Forecasting service unavailable: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected prediction failure for SKU '{request.stock_code}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference execution failed: {str(e)}"
        )


@router.post(
    "/predict",
    response_model=ForecastResponse,
    summary="Generate multi-horizon demand forecast (Blueprint alias)",
    description="Alternative route matching Section 9 of the Technical Blueprint.",
    include_in_schema=True
)
def predict_demand_alias(request: ForecastRequest) -> ForecastResponse:
    """Blueprint-compatible alias for demand forecast generation."""
    return predict_demand(request)


@router.get(
    "/evaluation-comparison",
    summary="Get multi-horizon comparative model evaluation metrics",
    description=(
        "Returns comparative performance benchmarks across three evaluation tiers: "
        "(1) Production Baseline SKU Models, (2) Optimized Experimental SKU Models, "
        "and (3) Store-Wide Macro Demand Models, explaining the empirical variance gap."
    )
)
def get_evaluation_comparison() -> Dict[str, Any]:
    """Returns comparative metrics across production, optimized, and store-wide models."""
    try:
        return store_wide_service.get_evaluation_comparison()
    except Exception as e:
        logger.error(f"Failed to retrieve evaluation comparison: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve evaluation comparison: {str(e)}"
        )


@router.get(
    "/store-wide",
    summary="Get store-wide macro aggregate demand forecasts",
    description=(
        "Returns multi-horizon store-wide aggregate demand predictions (D_7, D_15, D_30, D_90) "
        "and current store-level sales run-rate across all 3,922 catalog SKUs."
    )
)
def get_store_wide_forecast() -> Dict[str, Any]:
    """Returns store-wide aggregate demand predictions and historical context."""
    try:
        return store_wide_service.get_store_wide_forecast()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to generate store-wide forecast: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Store-wide forecast generation failed: {str(e)}"
        )

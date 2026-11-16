"""Demand Forecasting API endpoints.

Exposes RESTful endpoints under /api/v1/forecast for generating multi-horizon
demand forecasts, querying supported horizons, inspecting evaluation metrics,
and retrieving runtime model metadata.
"""

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
    try:
        return prediction_service.get_model_metrics()
    except FileNotFoundError as e:
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
    try:
        return prediction_service.get_model_info()
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Model metadata is not available: {str(e)}"
        )


@router.post(
    "/",
    response_model=ForecastResponse,
    summary="Generate multi-horizon demand forecast",
    description="Submits an SKU and historical feature values to generate estimated demand over requested horizons."
)
def predict_demand(request: ForecastRequest) -> ForecastResponse:
    """Generates demand forecasts for one or more requested horizons (7, 15, 30, 90 days)."""
    try:
        response = prediction_service.get_forecast(request)
        return response
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Forecasting models are not ready: {str(e)}"
        )
    except Exception as e:
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

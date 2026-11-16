"""Demand Forecasting API endpoints."""

from fastapi import APIRouter, HTTPException, status
from app.schemas.forecast import ForecastRequest, ForecastResponse
from app.services.prediction_service import prediction_service

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get("/horizons", summary="Get supported forecast horizons")
def get_supported_horizons():
    """Returns the list of forecast horizon windows supported by the system."""
    return {
        "supported_horizons_days": [7, 15, 30, 90],
        "description": "Short-term to quarterly retail demand horizons."
    }


@router.post("/", response_model=ForecastResponse, summary="Request demand forecast")
def predict_demand(request: ForecastRequest):
    """Placeholder endpoint to request demand forecast for a product SKU/StockCode.
    
    ML models will be connected in subsequent milestones.
    """
    response = prediction_service.get_forecast(request)
    return response

"""Forecast Pydantic Schemas for validation and serialization."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    """Request schema for product demand forecast."""
    stock_code: str = Field(..., description="Unique product stock code / SKU", example="85123A")
    horizon_days: int = Field(..., description="Forecast horizon in days (e.g., 7, 15, 30, 90)", example=30)

    class Config:
        json_schema_extra = {
            "example": {
                "stock_code": "85123A",
                "horizon_days": 30
            }
        }


class ForecastItem(BaseModel):
    """Daily or periodic forecast point."""
    date: str = Field(..., description="Forecast date (YYYY-MM-DD)")
    predicted_quantity: float = Field(..., description="Predicted demand units")


class ForecastResponse(BaseModel):
    """Response schema for forecast predictions."""
    stock_code: str
    horizon_days: int
    total_predicted_demand: Optional[float] = None
    daily_forecasts: Optional[List[ForecastItem]] = []
    status: str = Field(default="pending", description="Status of forecast prediction")
    message: Optional[str] = None

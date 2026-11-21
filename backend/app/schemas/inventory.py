"""Inventory Management & Purchasing Pydantic Schemas.

Implements request and response schemas for inventory replenishment recommendations,
decision support, and safety stock calculations matching AGENTS.md Section 6.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator


class InventoryRecommendationRequest(BaseModel):
    """Request schema for inventory replenishment recommendation."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "stock_code": "85123A",
                "current_stock": 100.0,
                "lead_time_days": 7,
                "review_period_days": 7,
                "safety_stock_days": 3.0,
                "use_experimental": False
            }
        }
    )

    stock_code: str = Field(
        ..., min_length=1,
        description="Unique product SKU or stock code (e.g. '85123A')."
    )
    current_stock: float = Field(
        ..., ge=0.0,
        description="Current physical or available on-hand stock quantity. Must be non-negative."
    )
    lead_time_days: int = Field(
        default=7, ge=1, le=180,
        description="Supplier replenishment lead time in calendar days (default: 7)."
    )
    review_period_days: int = Field(
        default=7, ge=1, le=180,
        description="Inventory review and reorder cycle period in calendar days (default: 7)."
    )
    safety_stock_days: float = Field(
        default=3.0, ge=0.0, le=90.0,
        description="Safety buffer expressed in days of projected daily demand (default: 3.0)."
    )
    use_experimental: bool = Field(
        default=False,
        description="Whether to use Task 12 experimental models instead of baseline production models."
    )

    @model_validator(mode="after")
    def clean_and_validate(self) -> "InventoryRecommendationRequest":
        cleaned = self.stock_code.strip()
        if not cleaned:
            raise ValueError("stock_code cannot be empty or whitespace.")
        self.stock_code = cleaned
        return self


class InventoryRecommendationResponse(BaseModel):
    """Response schema for inventory replenishment recommendation."""
    stock_code: str = Field(..., description="Unique product SKU identifier")
    current_stock: float = Field(..., description="Current available on-hand stock units")
    lead_time_days: int = Field(..., description="Supplier replenishment lead time in days")
    review_period_days: int = Field(..., description="Inventory review period in days")
    coverage_period_days: int = Field(..., description="Total coverage cycle window in days (lead_time + review_period)")
    forecast_demand: float = Field(..., description="Projected cumulative customer demand over coverage period")
    daily_demand_rate: float = Field(..., description="Average daily projected demand rate (forecast_demand / coverage_period_days)")
    safety_stock_days: float = Field(..., description="Safety buffer duration in days")
    safety_stock: float = Field(..., description="Calculated safety stock buffer units")
    target_stock: float = Field(..., description="Total target inventory level (forecast_demand + safety_stock)")
    recommended_purchase_quantity: float = Field(..., description="Recommended additional stock units to purchase (max(0, target_stock - current_stock))")
    stock_condition: str = Field(..., description="Operational stock condition risk classification ('CRITICAL', 'ELEVATED', 'SAFE')")
    recommendation: str = Field(..., description="Actionable replenishment recommendation directive")
    calculation_explanation: str = Field(..., description="Transparent mathematical breakdown of the recommendation calculation")
    model_used: str = Field(..., description="ML model pipeline version utilized for demand inference")
    timestamp: str = Field(..., description="ISO-8601 timestamp of recommendation calculation")

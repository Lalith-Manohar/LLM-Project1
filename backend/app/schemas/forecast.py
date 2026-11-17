"""Forecast Pydantic Schemas for validation and serialization.

Implements multi-horizon forecasting schemas matching Blueprint Section 9,
supporting single or multiple requested horizons ([7, 15, 30, 90]),
historical feature input validation, and machine-readable metadata.
"""

import math
import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator


SUPPORTED_HORIZONS = [7, 15, 30, 90]


class HistoricalFeatures(BaseModel):
    """Historical demand lag and rolling statistics for feature input."""
    day_of_week: Optional[int] = Field(
        None, ge=0, le=6,
        description="Day of week index (0=Monday, 6=Sunday). Defaults to observation date if omitted."
    )
    month: Optional[int] = Field(
        None, ge=1, le=12,
        description="Calendar month (1=January, 12=December). Defaults to observation date if omitted."
    )
    day_of_month: Optional[int] = Field(
        None, ge=1, le=31,
        description="Day of the month (1-31). Defaults to observation date if omitted."
    )
    lag_1: float = Field(
        ..., ge=0.0,
        description="Actual sales demand from 1 day prior (t-1). Must be finite and non-negative."
    )
    lag_7: float = Field(
        ..., ge=0.0,
        description="Actual sales demand from 7 days prior (t-7). Must be finite and non-negative."
    )
    lag_14: float = Field(
        ..., ge=0.0,
        description="Actual sales demand from 14 days prior (t-14). Must be finite and non-negative."
    )
    lag_28: float = Field(
        ..., ge=0.0,
        description="Actual sales demand from 28 days prior (t-28). Must be finite and non-negative."
    )
    rolling_mean_7: float = Field(
        ..., ge=0.0,
        description="Historical 7-day rolling average demand (t-7 to t-1). Must be finite and non-negative."
    )
    rolling_mean_28: float = Field(
        ..., ge=0.0,
        description="Historical 28-day rolling average demand (t-28 to t-1). Must be finite and non-negative."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "day_of_week": 2,
                "month": 11,
                "day_of_month": 15,
                "lag_1": 12.0,
                "lag_7": 15.0,
                "lag_14": 10.0,
                "lag_28": 14.0,
                "rolling_mean_7": 13.5,
                "rolling_mean_28": 12.8
            }
        }
    )

    @model_validator(mode="after")
    def validate_finite_numbers(self) -> "HistoricalFeatures":
        num_fields = ["lag_1", "lag_7", "lag_14", "lag_28", "rolling_mean_7", "rolling_mean_28"]
        for f in num_fields:
            val = getattr(self, f)
            if val is not None and (math.isnan(val) or math.isinf(val)):
                raise ValueError(f"Feature field '{f}' must be a finite numerical value.")
        return self


class ForecastRequest(BaseModel):
    """Request schema for product demand forecast.
    
    Accepts an SKU identifier, an optional list of requested horizons
    (subset of [7, 15, 30, 90]), and historical features (either nested
    under 'features' or passed directly as flat fields).
    """
    stock_code: str = Field(
        ..., min_length=1,
        description="Unique product SKU or stock code (e.g. '85123A')."
    )
    horizons: Optional[List[int]] = Field(
        default=None,
        description="List of target horizons in days to forecast (subset of [7, 15, 30, 90]). Defaults to all four."
    )
    horizon_days: Optional[int] = Field(
        default=None,
        description="Legacy single horizon field for backward compatibility."
    )
    features: Optional[HistoricalFeatures] = Field(
        default=None,
        description="Historical feature vector. If omitted, flat fields are parsed from root level."
    )

    # Flat feature fields accepted at root level for caller convenience
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    month: Optional[int] = Field(None, ge=1, le=12)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    lag_1: Optional[float] = Field(None, ge=0.0)
    lag_7: Optional[float] = Field(None, ge=0.0)
    lag_14: Optional[float] = Field(None, ge=0.0)
    lag_28: Optional[float] = Field(None, ge=0.0)
    rolling_mean_7: Optional[float] = Field(None, ge=0.0)
    rolling_mean_28: Optional[float] = Field(None, ge=0.0)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "stock_code": "85123A",
                "horizons": [7, 15, 30, 90],
                "features": {
                    "day_of_week": 2,
                    "month": 11,
                    "day_of_month": 15,
                    "lag_1": 12.0,
                    "lag_7": 15.0,
                    "lag_14": 10.0,
                    "lag_28": 14.0,
                    "rolling_mean_7": 13.5,
                    "rolling_mean_28": 12.8
                }
            }
        }
    )

    @model_validator(mode="after")
    def validate_and_harmonize(self) -> "ForecastRequest":
        # 1. Clean StockCode
        cleaned_sku = self.stock_code.strip()
        if not cleaned_sku:
            raise ValueError("stock_code cannot be empty or whitespace.")
        self.stock_code = cleaned_sku

        # 2. Harmonize Horizons
        if self.horizons is not None:
            if not self.horizons:
                raise ValueError("horizons list cannot be empty when provided.")
            for h in self.horizons:
                if h not in SUPPORTED_HORIZONS:
                    raise ValueError(
                        f"Unsupported forecast horizon '{h}'. "
                        f"Supported horizons are {SUPPORTED_HORIZONS} days."
                    )
            # Deduplicate while preserving order
            self.horizons = list(dict.fromkeys(self.horizons))
        elif self.horizon_days is not None:
            if self.horizon_days not in SUPPORTED_HORIZONS:
                raise ValueError(
                    f"Unsupported forecast horizon '{self.horizon_days}'. "
                    f"Supported horizons are {SUPPORTED_HORIZONS} days."
                )
            self.horizons = [self.horizon_days]
        else:
            self.horizons = list(SUPPORTED_HORIZONS)

        # 3. Harmonize Historical Features
        # If nested 'features' object is missing, check if caller provided flat fields (backward compatibility).
        # If any flat feature was provided, ensure all required numerical features are present and valid.
        # If no features or flat fields are provided at all, self.features remains None, signalling
        # the PredictionService to automatically generate features from the historical CSV dataset.
        required_num = ["lag_1", "lag_7", "lag_14", "lag_28", "rolling_mean_7", "rolling_mean_28"]
        if self.features is None:
            any_flat_provided = any(getattr(self, f) is not None for f in required_num)
            if any_flat_provided:
                missing_flat = [f for f in required_num if getattr(self, f) is None]
                if missing_flat:
                    raise ValueError(
                        f"Missing required historical demand features: {missing_flat}. "
                        "Provide all numerical lag/rolling features when specifying manual features, "
                        "or omit features completely for automatic CSV-based feature generation."
                    )

                # Check finite
                for f in required_num:
                    val = getattr(self, f)
                    if math.isnan(val) or math.isinf(val):
                        raise ValueError(f"Feature '{f}' must be a finite numerical value.")

                # Create internal HistoricalFeatures
                self.features = HistoricalFeatures(
                    day_of_week=self.day_of_week,
                    month=self.month,
                    day_of_month=self.day_of_month,
                    lag_1=self.lag_1,
                    lag_7=self.lag_7,
                    lag_14=self.lag_14,
                    lag_28=self.lag_28,
                    rolling_mean_7=self.rolling_mean_7,
                    rolling_mean_28=self.rolling_mean_28
                )

        # 4. Fill calendar defaults if manual features were provided without calendar values
        if self.features is not None:
            today = datetime.date.today()
            if self.features.day_of_week is None:
                self.features.day_of_week = today.weekday()
            if self.features.month is None:
                self.features.month = today.month
            if self.features.day_of_month is None:
                self.features.day_of_month = today.day

        return self


class HorizonPredictionDetail(BaseModel):
    """Detailed breakdown for a single forecast horizon."""
    horizon_days: int = Field(..., description="Target forecast window in days")
    predicted_demand: float = Field(..., description="Projected cumulative demand units over horizon")
    model_name: str = Field(..., description="Selected ML pipeline name")
    wape: Optional[float] = Field(None, description="Validation Weighted Absolute Percentage Error (%)")


class ForecastResponse(BaseModel):
    """Response schema for multi-horizon demand forecast predictions."""
    stock_code: str = Field(..., description="Product SKU identifier")
    horizons: List[int] = Field(..., description="List of forecast horizons evaluated")
    predictions: Dict[str, float] = Field(
        ...,
        description="Key-value mapping of horizon days (e.g. '7', '15', '30', '90') to predicted demand units."
    )
    horizon_details: List[HorizonPredictionDetail] = Field(
        default=[],
        description="Granular performance and model details per requested horizon."
    )
    units: str = Field(default="units", description="Unit of measurement for forecasted demand")
    model_version: str = Field(default="v1.0", description="Model training version / manifest identifier")
    timestamp: str = Field(..., description="ISO-8601 timestamp of forecast inference")
    warnings: List[str] = Field(
        default=[],
        description="Informational notes or warnings (e.g., infrequent SKU mapping)."
    )

    # Historical context & transparency
    observation_date: Optional[str] = Field(
        None,
        description="Historical observation cutoff date (YYYY-MM-DD) from which the forecast is projected."
    )
    history_days: Optional[int] = Field(
        None,
        description="Number of continuous daily historical records evaluated."
    )
    is_auto_generated: bool = Field(
        default=False,
        description="True if historical features were automatically derived from CSV dataset."
    )

    # Backward-compatible fields
    status: str = Field(default="success", description="Prediction status code")
    total_predicted_demand: Optional[float] = Field(
        None,
        description="Demand for primary requested horizon (for backward compatibility)."
    )
    horizon_days: Optional[int] = Field(
        None,
        description="Primary horizon in days (for backward compatibility)."
    )


class SupportedHorizonsResponse(BaseModel):
    """Response schema for supported forecast horizons."""
    supported_horizons_days: List[int] = Field(..., description="List of integer horizon windows in days")
    description: str = Field(..., description="Operational description of forecast horizons")
    horizon_definitions: Dict[str, str] = Field(..., description="Business operational usage per horizon")


class ModelMetricsResponse(BaseModel):
    """Response schema for model evaluation benchmarks."""
    project: str
    milestone: str
    dataset_reference: str
    training_timestamp: str
    encoding_strategy: str
    backtesting_strategy: str
    models: Dict[str, Any]


class ModelInfoResponse(BaseModel):
    """Response schema for model architecture and runtime info."""
    project: str
    version: str
    status: str
    python_version: str
    scikit_learn_version: str
    supported_horizons: List[int]
    active_models: Dict[str, str]
    feature_columns: List[str]
    categorical_columns: List[str]
    numerical_columns: List[str]
    unseen_sku_handling: str

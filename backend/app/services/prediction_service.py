"""Prediction Service layer for handling model loading and inference.

NOTE: This is currently a placeholder. ML models will be loaded here once
trained and saved in ml/models/.
"""

import os
from typing import Dict, Any
from app.core.config import settings
from app.schemas.forecast import ForecastRequest, ForecastResponse


class PredictionService:
    def __init__(self):
        self.models_dir = settings.MODELS_DIR

    def get_forecast(self, request: ForecastRequest) -> ForecastResponse:
        """Generate demand forecast for a given product and horizon.
        
        Currently returns placeholder status until models are trained and saved.
        """
        # Validate supported horizons: 7, 15, 30, 90
        supported_horizons = [7, 15, 30, 90]
        if request.horizon_days not in supported_horizons:
            return ForecastResponse(
                stock_code=request.stock_code,
                horizon_days=request.horizon_days,
                status="unsupported_horizon",
                message=f"Supported forecast horizons are {supported_horizons} days."
            )

        # Placeholder: In the next milestone, trained ML model artifacts (.joblib)
        # will be loaded to produce real forecasts.
        return ForecastResponse(
            stock_code=request.stock_code,
            horizon_days=request.horizon_days,
            total_predicted_demand=None,
            daily_forecasts=[],
            status="model_not_trained",
            message="Model training pending. Place model artifact in backend/ml/models to enable inference."
        )


prediction_service = PredictionService()

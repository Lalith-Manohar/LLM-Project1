"""Model inference module for loading saved models and producing predictions.

Provides programmatic and CLI-accessible prediction utility for NEXORA
forecasting pipelines across 7, 15, 30, and 90-day horizons.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

# Add backend directory to sys.path to allow module imports
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.prediction_service import prediction_service
from app.schemas.forecast import ForecastRequest, HistoricalFeatures, SUPPORTED_HORIZONS


def run_inference(
    stock_code: str,
    horizons: Optional[List[int]] = None,
    features: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """Generates demand forecasts for a stock code and requested horizons.
    
    Args:
        stock_code: Product SKU / StockCode (e.g. '85123A').
        horizons: Target horizons in days (subset of [7, 15, 30, 90]).
                  Defaults to all 4 horizons.
        features: Optional dictionary of historical lag and rolling features.
                  If omitted, sensible baseline defaults (0.0) are used.
                  
    Returns:
        Dict[str, Any]: Prediction result dictionary with multi-horizon outputs.
    """
    feature_dict = features or {
        "day_of_week": 2,
        "month": 11,
        "day_of_month": 15,
        "lag_1": 0.0,
        "lag_7": 0.0,
        "lag_14": 0.0,
        "lag_28": 0.0,
        "rolling_mean_7": 0.0,
        "rolling_mean_28": 0.0
    }

    req = ForecastRequest(
        stock_code=stock_code,
        horizons=horizons or list(SUPPORTED_HORIZONS),
        features=HistoricalFeatures(**feature_dict)
    )

    response = prediction_service.get_forecast(req)
    return response.model_dump()


if __name__ == "__main__":
    demo_sku = "85123A"
    print(f"[NEXORA Inference CLI] Running demo prediction for SKU: '{demo_sku}'...")
    result = run_inference(demo_sku, horizons=[7, 15, 30, 90])
    print(f"Predictions: {result['predictions']}")
    print(f"Status: {result['status']}")

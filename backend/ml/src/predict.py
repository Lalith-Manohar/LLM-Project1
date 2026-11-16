"""Model inference module for loading saved models and producing predictions.

PLACEHOLDER: Will load serialized models from backend/ml/models/ and generate
forecast values for requested horizon windows.
"""

from typing import List, Dict, Any


def run_inference(stock_code: str, horizon_days: int) -> Dict[str, Any]:
    """Generates demand forecasts for a stock code.
    
    Args:
        stock_code: Product SKU / StockCode.
        horizon_days: Horizon window (7, 15, 30, 90).
        
    Returns:
        Prediction result dictionary.
    """
    raise NotImplementedError(
        "Model inference is not yet available. No trained model found in backend/ml/models."
    )

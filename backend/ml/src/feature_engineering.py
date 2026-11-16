"""Feature engineering module for retail demand time-series forecasting.

PLACEHOLDER: Will build lag features, rolling windows, calendar features
(day of week, month, holidays), and aggregation at daily/product levels.
"""

import pandas as pd


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts features for demand forecasting models.
    
    Args:
        df: Cleaned transaction DataFrame.
        
    Returns:
        DataFrame with engineered feature matrix.
    """
    raise NotImplementedError(
        "Feature engineering pipeline is not yet implemented."
    )

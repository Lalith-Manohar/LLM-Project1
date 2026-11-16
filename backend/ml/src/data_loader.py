"""Data loader module for loading raw UCI Online Retail II dataset.

PLACEHOLDER: Waiting for user approval and dataset download before implementing
actual loading logic.
"""

from pathlib import Path
from typing import Optional
import pandas as pd


def load_raw_data(file_path: Optional[str] = None) -> pd.DataFrame:
    """Loads raw retail data from backend/ml/data/raw/ directory.
    
    Args:
        file_path: Optional custom path to raw dataset file.
        
    Returns:
        DataFrame: Raw dataset.
    """
    raise NotImplementedError(
        "Data loading is not yet implemented. Please download the UCI Online Retail II dataset into backend/ml/data/raw/"
    )

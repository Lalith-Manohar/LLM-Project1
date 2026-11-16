"""Model evaluation and chronological backtesting module for NEXORA.

Implements evaluation metrics (MAE, RMSE, WAPE) and strict chronological time-based
splitting with purge/embargo windows to prevent forward target-window leakage.
"""

import datetime
from typing import Dict, Any, Tuple, List, Optional
import numpy as np
import pandas as pd


def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Mean Absolute Error (MAE).
    
    MAE = mean(|y_true - y_pred|)
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_true_arr - y_pred_arr)))


def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Root Mean Squared Error (RMSE).
    
    RMSE = sqrt(mean((y_true - y_pred)^2))
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_true_arr - y_pred_arr) ** 2)))


def calculate_wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculates Weighted Absolute Percentage Error (WAPE).
    
    WAPE = (sum(|y_true - y_pred|) / sum(|y_true|)) * 100
    
    Handles zero denominator explicitly:
    - If sum(|y_true|) == 0 and sum(|y_true - y_pred|) == 0: returns 0.0%
    - If sum(|y_true|) == 0 and predictions > 0: returns 100.0%
    """
    y_true_arr = np.asarray(y_true, dtype=float)
    y_pred_arr = np.asarray(y_pred, dtype=float)
    
    total_abs_error = float(np.sum(np.abs(y_true_arr - y_pred_arr)))
    total_actual = float(np.sum(np.abs(y_true_arr)))
    
    if total_actual == 0.0:
        return 0.0 if total_abs_error == 0.0 else 100.0
        
    return float((total_abs_error / total_actual) * 100.0)


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculates all mandatory forecasting accuracy and error metrics.
    
    Args:
        y_true: True actual demand values.
        y_pred: Model predicted demand values.
        
    Returns:
        Dict[str, float]: Dictionary with 'mae', 'rmse', and 'wape' (rounded to 4 decimals).
    """
    mae = calculate_mae(y_true, y_pred)
    rmse = calculate_rmse(y_true, y_pred)
    wape = calculate_wape(y_true, y_pred)
    
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "wape": round(wape, 4)
    }


def get_chronological_split(
    df: pd.DataFrame,
    horizon: int,
    val_start: datetime.date,
    val_end: datetime.date,
    feature_cols: List[str],
    target_col: Optional[str] = None
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, Dict[str, Any]]:
    """Performs strict chronological train/validation splitting with purge/embargo.
    
    Target-Window Leakage Prevention Rule:
    For horizon H, a sample observed at date t has a cumulative target covering
    dates t+1 through t+H. For a validation period starting at val_start,
    a training observation is eligible ONLY if its entire target window ends
    strictly before val_start:
        t + H < val_start  ==>  t <= val_start - timedelta(days=H + 1)
        
    This guarantees zero overlap between training targets and validation periods.
    
    Args:
        df: Feature DataFrame with 'date', 'StockCode', features, and target.
        horizon: Horizon window in days (7, 15, 30, 90).
        val_start: Validation period start date.
        val_end: Validation period end date.
        feature_cols: List of predictor column names.
        target_col: Target column name (default: f"D_{horizon}").
        
    Returns:
        Tuple: (X_train, y_train, X_val, y_val, split_metadata)
    """
    t_col = target_col or f"D_{horizon}"
    
    # Ensure date is date object
    if not isinstance(df["date"].iloc[0], datetime.date):
        dates = pd.to_datetime(df["date"]).dt.date
    else:
        dates = df["date"]
        
    # Check completeness of required columns
    all_needed_cols = feature_cols + [t_col]
    complete_mask = ~df[all_needed_cols].isnull().any(axis=1)
    
    # Compute exact purge/embargo training cutoff
    train_cutoff = val_start - datetime.timedelta(days=horizon + 1)
    
    # Train mask: observations <= train_cutoff with complete features and target
    train_mask = complete_mask & (dates <= train_cutoff)
    
    # Validation mask: observations between val_start and val_end with complete features and target
    val_mask = complete_mask & (dates >= val_start) & (dates <= val_end)
    
    train_df = df[train_mask]
    val_df = df[val_mask]
    
    if train_df.empty or val_df.empty:
        raise ValueError(
            f"Chronological split produced empty partitions for H={horizon}: "
            f"Train={len(train_df)}, Val={len(val_df)}."
        )
        
    train_max_date = dates[train_mask].max()
    val_min_date = dates[val_mask].min()
    embargo_gap_days = (val_min_date - train_max_date).days
    
    # Verify zero target leakage
    if embargo_gap_days <= horizon:
        raise ValueError(
            f"Target leakage detected! Embargo gap ({embargo_gap_days} days) "
            f"must be strictly greater than horizon ({horizon} days)."
        )
        
    X_train = train_df[feature_cols].copy()
    y_train = train_df[t_col].astype(float).copy()
    
    X_val = val_df[feature_cols].copy()
    y_val = val_df[t_col].astype(float).copy()
    
    split_meta = {
        "horizon": horizon,
        "train_samples": len(X_train),
        "val_samples": len(X_val),
        "train_start_date": str(dates[train_mask].min()),
        "train_end_date": str(train_max_date),
        "train_cutoff": str(train_cutoff),
        "val_start_date": str(val_min_date),
        "val_end_date": str(dates[val_mask].max()),
        "embargo_gap_days": embargo_gap_days,
        "is_leakage_free": True
    }
    
    return X_train, y_train, X_val, y_val, split_meta

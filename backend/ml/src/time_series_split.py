"""Date-Grouped Chronological Time Series Splitter with Horizon Embargo.

Ensures rigorous leakage-free temporal cross-validation:
1. All SKUs sharing a forecast origin date T belong strictly to the same fold.
2. Training dates strictly precede validation dates.
3. Enforces horizon-aware embargo gaps:
   max(train_dates) <= min(val_dates) - (horizon + 1)
   guaranteeing that no cumulative training target window overlaps the validation origin.
"""

import datetime
from typing import Optional, List, Tuple, Dict, Any, Generator
import numpy as np
import pandas as pd


class DateGroupedTimeSeriesSplit:
    """Chronological expanding-window cross-validator grouped by date with horizon embargo.

    Parameters
    ----------
    n_splits : int, default=5
        Number of chronological splits.
    horizon : int, default=7
        Forecast horizon in days (e.g. 7, 15, 30, 90).
    embargo_days : Optional[int], default=None
        Embargo gap between training cutoff and validation start.
        If None, defaults to horizon + 1.
    min_train_dates : int, default=60
        Minimum number of unique calendar dates required in initial training fold.
    date_col : str, default="date"
        Column name for observation dates.
    """

    def __init__(
        self,
        n_splits: int = 5,
        horizon: int = 7,
        embargo_days: Optional[int] = None,
        min_train_dates: int = 60,
        date_col: str = "date"
    ):
        self.n_splits = n_splits
        self.horizon = horizon
        self.embargo_days = embargo_days if embargo_days is not None else (horizon + 1)
        self.min_train_dates = min_train_dates
        self.date_col = date_col

    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        return self.n_splits

    def split(
        self,
        X: pd.DataFrame,
        y: Optional[Any] = None,
        groups: Optional[Any] = None
    ) -> Generator[Tuple[np.ndarray, np.ndarray], None, None]:
        """Yields (train_indices, val_indices) for each chronological fold."""
        if groups is not None:
            dates = pd.Series(groups).values
        elif isinstance(X, pd.DataFrame) and self.date_col in X.columns:
            dates = X[self.date_col].values
        else:
            raise ValueError(f"Date column '{self.date_col}' or groups array required for date-grouped splitting.")

        # Ensure dates are datetime.date objects
        if hasattr(dates[0], "date"):
            dates = np.array([d.date() if hasattr(d, "date") else d for d in dates])
        elif isinstance(dates[0], str):
            dates = np.array([pd.to_datetime(d).date() for d in dates])

        unique_dates = np.array(sorted(list(set(dates))))
        n_dates = len(unique_dates)

        # Adaptively scale min_train_dates if dataset has limited date span relative to embargo
        min_train = self.min_train_dates
        if n_dates - min_train - self.embargo_days <= 0:
            min_train = max(7, (n_dates - self.embargo_days) // 3)

        available_val_dates = n_dates - min_train - self.embargo_days
        if available_val_dates <= 0:
            # If still insufficient for multiple splits, yield at least 1 holdout fold
            min_train = max(7, n_dates - self.embargo_days - 1)
            available_val_dates = max(1, n_dates - min_train - self.embargo_days)

        val_block_size = max(1, available_val_dates // self.n_splits)

        for i in range(self.n_splits):
            val_start_idx = min_train + self.embargo_days + i * val_block_size
            if val_start_idx >= n_dates:
                break

            val_end_idx = val_start_idx + val_block_size if i < self.n_splits - 1 else n_dates
            val_start_date = unique_dates[val_start_idx]
            val_end_date = unique_dates[val_end_idx - 1]

            # Enforce embargo gap strictly: train_cutoff <= val_start_date - embargo_days
            train_cutoff = val_start_date - datetime.timedelta(days=self.embargo_days)
            train_dates = unique_dates[unique_dates <= train_cutoff]
            val_dates = unique_dates[(unique_dates >= val_start_date) & (unique_dates <= val_end_date)]

            train_idx = np.where(np.isin(dates, train_dates))[0]
            val_idx = np.where(np.isin(dates, val_dates))[0]

            if len(train_idx) == 0 or len(val_idx) == 0:
                continue

            yield train_idx, val_idx

    def get_fold_summary(
        self,
        X: pd.DataFrame,
        y: Optional[Any] = None,
        groups: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Returns structured metadata for all generated folds."""
        if groups is not None:
            dates = pd.Series(groups).values
        elif isinstance(X, pd.DataFrame) and self.date_col in X.columns:
            dates = X[self.date_col].values
        else:
            raise ValueError(f"Date column '{self.date_col}' or groups array required.")

        if hasattr(dates[0], "date"):
            dates = np.array([d.date() if hasattr(d, "date") else d for d in dates])

        summary = []
        for fold, (tr_idx, val_idx) in enumerate(self.split(X, y, groups)):
            tr_dates = dates[tr_idx]
            val_dates = dates[val_idx]

            max_tr_date = max(tr_dates)
            min_val_date = min(val_dates)
            embargo_actual = (min_val_date - max_tr_date).days

            summary.append({
                "fold": fold + 1,
                "train_rows": len(tr_idx),
                "val_rows": len(val_idx),
                "train_date_min": str(min(tr_dates)),
                "train_date_max": str(max_tr_date),
                "val_date_min": str(min_val_date),
                "val_date_max": str(max(val_dates)),
                "embargo_days": embargo_actual,
                "horizon": self.horizon,
                "temporal_valid": max_tr_date < min_val_date and embargo_actual >= self.embargo_days
            })
        return summary

"""Chronological Point-in-Time Expanding-Window Target Encoder for Time Series.

Guarantees strict temporal separation:
1. In-sample training encodings for date T depend exclusively on realized targets
   from historical dates t <= T - (horizon + 1).
2. Out-of-sample / inference encodings map categories to the final cumulative
   smoothed target statistics learned from the complete training history.
3. Unseen categories receive the global historical training prior.
4. Perturbations to future targets have exactly 0.0 impact on earlier encodings.
"""

import bisect
import datetime
from typing import Dict, Optional, Union, List
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin


class ChronologicalTargetEncoder(BaseEstimator, TransformerMixin):
    """Chronological expanding-window target encoder with horizon embargo.
    
    Parameters
    ----------
    horizon : int, default=7
        Forecast horizon in days (e.g. 7, 15, 30, 90).
    smooth : float, default=10.0
        Smoothing factor m in m-estimate: (sum + m * prior) / (count + m).
    default_prior : float, default=0.0
        Fixed prior used when no historical targets have realized yet.
    stock_col : str, default="StockCode"
        Name of the categorical SKU identifier column.
    date_col : str, default="date"
        Name of the date column.
    """

    def __init__(
        self,
        horizon: int = 7,
        smooth: float = 10.0,
        default_prior: float = 0.0,
        stock_col: str = "StockCode",
        date_col: str = "date"
    ):
        self.horizon = horizon
        self.smooth = smooth
        self.default_prior = default_prior
        self.stock_col = stock_col
        self.date_col = date_col
        self.embargo_days = horizon + 1

        # Fitted attributes
        self.final_encodings_: Dict[str, float] = {}
        self.global_prior_: float = default_prior
        self.unique_dates_: List[datetime.date] = []
        self.pivot_sum_ = None
        self.pivot_count_ = None
        self.g_sum_series_ = None
        self.g_count_series_ = None

    def fit(self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]):
        """Fits cumulative category statistics up to the end of training history."""
        self._fit_internal(X, y)
        return self

    def _fit_internal(self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]):
        if isinstance(X, pd.DataFrame):
            df = X.copy()
        elif isinstance(X, np.ndarray):
            # Assume col 0 is StockCode, col 1 is date (if present)
            if X.shape[1] >= 2:
                df = pd.DataFrame({self.stock_col: X[:, 0], self.date_col: X[:, 1]})
            else:
                df = pd.DataFrame({self.stock_col: X[:, 0]})
        else:
            df = pd.DataFrame(X)

        df["target"] = np.asarray(y, dtype=float)
        df[self.stock_col] = df[self.stock_col].astype(str).str.strip()

        # If date column missing, use fallback
        if self.date_col in df.columns:
            df[self.date_col] = pd.to_datetime(df[self.date_col]).dt.date
        else:
            # Fallback to single static group if date not provided
            df[self.date_col] = datetime.date(2010, 1, 1)

        daily_sku = df.groupby([self.date_col, self.stock_col])["target"].agg(["sum", "count"]).reset_index()
        daily_global = df.groupby(self.date_col)["target"].agg(["sum", "count"]).reset_index()

        self.unique_dates_ = sorted(list(set(df[self.date_col])))
        self.pivot_sum_ = daily_sku.pivot(index=self.date_col, columns=self.stock_col, values="sum").reindex(self.unique_dates_).fillna(0.0).cumsum()
        self.pivot_count_ = daily_sku.pivot(index=self.date_col, columns=self.stock_col, values="count").reindex(self.unique_dates_).fillna(0.0).cumsum()

        self.g_sum_series_ = daily_global.set_index(self.date_col)["sum"].reindex(self.unique_dates_).fillna(0.0).cumsum()
        self.g_count_series_ = daily_global.set_index(self.date_col)["count"].reindex(self.unique_dates_).fillna(0.0).cumsum()

        # Compute final cumulative encodings at the end of training
        if len(self.unique_dates_) > 0:
            last_date = self.unique_dates_[-1]
            tot_g_sum = float(self.g_sum_series_.loc[last_date])
            tot_g_cnt = float(self.g_count_series_.loc[last_date])
            self.global_prior_ = (tot_g_sum / tot_g_cnt) if tot_g_cnt > 0 else self.default_prior

            sku_sums = self.pivot_sum_.loc[last_date]
            sku_cnts = self.pivot_count_.loc[last_date]
            enc_series = (sku_sums + self.smooth * self.global_prior_) / (sku_cnts + self.smooth)
            self.final_encodings_ = enc_series.to_dict()
        else:
            self.global_prior_ = self.default_prior
            self.final_encodings_ = {}

        return df

    def fit_transform(self, X: Union[pd.DataFrame, np.ndarray], y: Union[pd.Series, np.ndarray]):
        """Fits and computes point-in-time expanding encodings for training rows."""
        df = self._fit_internal(X, y)

        if self.date_col not in df.columns or len(self.unique_dates_) <= 1:
            # Fallback to transform if dates not present
            return self.transform(X)

        enc_vals = np.full(len(df), self.default_prior, dtype=float)
        date_groups = df.groupby(self.date_col).indices

        for d, idxs in date_groups.items():
            cutoff_date = d - datetime.timedelta(days=self.embargo_days)
            pos = bisect.bisect_right(self.unique_dates_, cutoff_date) - 1

            if pos < 0:
                # No historical targets realized before this date
                enc_vals[idxs] = self.default_prior
            else:
                d_cut = self.unique_dates_[pos]
                g_sum = float(self.g_sum_series_.loc[d_cut])
                g_cnt = float(self.g_count_series_.loc[d_cut])
                prior = (g_sum / g_cnt) if g_cnt > 0 else self.default_prior

                sub_skus = df.iloc[idxs][self.stock_col].values
                s_sum = self.pivot_sum_.loc[d_cut, sub_skus].values
                s_cnt = self.pivot_count_.loc[d_cut, sub_skus].values
                enc = (s_sum + self.smooth * prior) / (s_cnt + self.smooth)
                enc_vals[idxs] = enc

        return enc_vals.reshape(-1, 1)

    def transform(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """Transforms out-of-sample or inference rows using frozen training encodings."""
        if isinstance(X, pd.DataFrame):
            if self.stock_col in X.columns:
                skus = X[self.stock_col].astype(str).str.strip().values
            else:
                skus = X.iloc[:, 0].astype(str).str.strip().values
        elif isinstance(X, np.ndarray):
            if X.ndim == 1:
                skus = pd.Series(X).astype(str).str.strip().values
            else:
                skus = pd.Series(X[:, 0]).astype(str).str.strip().values
        else:
            skus = pd.Series(X).astype(str).str.strip().values

        enc_vals = np.array([
            self.final_encodings_.get(sku, self.global_prior_)
            for sku in skus
        ], dtype=float)

        return enc_vals.reshape(-1, 1)

    def get_feature_names_out(self, input_features=None) -> np.ndarray:
        return np.array([f"{self.stock_col}_target_encoded"], dtype=object)

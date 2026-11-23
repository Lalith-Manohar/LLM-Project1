"""Baseline-Anchored Residual Regressor for Multi-Horizon Demand Forecasting.

In retail demand forecasting, products with continuous history have a strong
underlying run-rate determined by recent moving averages. Estimating the
residual deviation (delta) from a moving-average baseline rather than learning
absolute scale from scratch yields lower variance, eliminates tree-underfitting,
and enforces non-negative physical lower bounds.
"""

from typing import Optional, Any
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin


class ResidualRegressor(BaseEstimator, RegressorMixin):
    """Estimator that models demand as a moving-average baseline plus an ML residual."""

    def __init__(
        self,
        base_feature: str = "RollingMean28",
        multiplier: float = 1.0,
        estimator: Optional[Any] = None
    ):
        self.base_feature = base_feature
        self.multiplier = float(multiplier)
        self.estimator = estimator

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> "ResidualRegressor":
        """Fits the underlying estimator on the residual (y - base)."""
        base_val = self.multiplier * X[self.base_feature].values.astype(float)
        residual = y.astype(float) - base_val
        if self.estimator is not None:
            self.estimator.fit(X, residual)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generates predictions by summing baseline and predicted residual."""
        base_val = self.multiplier * X[self.base_feature].values.astype(float)
        if self.estimator is not None:
            res_pred = self.estimator.predict(X)
            raw = base_val + res_pred
        else:
            raw = base_val
        return np.clip(np.asarray(raw, dtype=float), 0.0, None)

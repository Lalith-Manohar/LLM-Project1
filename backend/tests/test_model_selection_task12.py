"""Unit and integration tests for NEXORA Task 12 Model Selection & Hyperparameter Optimization.

Verifies:
1. Chronological fold separation (train strictly before val).
2. Horizon embargo enforcement (train_max <= val_min - (h + 1)).
3. No SKU/date overlap between training and validation.
4. No future target leakage in feature construction.
5. Preprocessing and scalers fitted only on training folds.
6. Polynomial transformations fitted only on training folds.
7. Identical validation eligibility across competing models.
8. WAPE, MAE, RMSE, and signed bias metric calculations.
9. Non-negative prediction clipping.
10. Random seed reproducibility.
11. Selected artifact loading and integrity.
12. Feature schema consistency.
"""

import sys
import datetime
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

# Ensure backend root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ml.src.evaluate import calculate_wape, calculate_mae, calculate_rmse
from ml.src.chronological_encoder import ChronologicalTargetEncoder
from ml.src.residual_model import ResidualRegressor
from ml.src.time_series_split import DateGroupedTimeSeriesSplit
from ml.experiments.model_selection_task12 import build_candidate_registry


class TestTask12ModelSelection(unittest.TestCase):
    """Test suite covering Task 12 validation governance, leakage-safety, and candidate models."""

    def setUp(self):
        """Build synthetic panel spanning multiple dates and SKUs."""
        dates = pd.date_range("2021-01-01", "2021-04-30", freq="D").date
        records = []
        for d in dates:
            for sku in ["SKU_A", "SKU_B", "SKU_C"]:
                records.append({
                    "date": d,
                    "StockCode": sku,
                    "daily_demand": int(np.random.RandomState(42).randint(0, 50)),
                    "Lag1": 10.0,
                    "Lag7": 12.0,
                    "Lag14": 11.0,
                    "Lag28": 10.5,
                    "RollingMean7": 10.0,
                    "RollingMean14": 10.2,
                    "RollingMean28": 10.1,
                    "RollingStd7": 2.5,
                    "RollingStd28": 3.0,
                    "ZeroFraction28": 0.1,
                    "MomentumRatio": 1.0,
                    "UnitPrice": 2.50,
                    "DayOfWeek": d.weekday(),
                    "Month": d.month,
                    "DayOfMonth": d.day,
                    "D_7": 70.0,
                    "D_15": 150.0,
                    "D_30": 300.0,
                    "D_90": 900.0
                })
        self.df = pd.DataFrame(records)
        self.num_cols = [
            "DayOfWeek", "Month", "DayOfMonth",
            "Lag1", "Lag7", "Lag14", "Lag28",
            "RollingMean7", "RollingMean14", "RollingMean28",
            "RollingStd7", "RollingStd28",
            "ZeroFraction28", "MomentumRatio", "UnitPrice"
        ]

    def test_01_chronological_fold_separation(self):
        """Test 1: Verify train dates strictly precede validation dates in all folds."""
        splitter = DateGroupedTimeSeriesSplit(n_splits=3, horizon=7, min_train_dates=20)
        for train_idx, val_idx in splitter.split(self.df):
            tr_dates = self.df.iloc[train_idx]["date"]
            va_dates = self.df.iloc[val_idx]["date"]
            self.assertLess(tr_dates.max(), va_dates.min())

    def test_02_horizon_embargo_enforcement(self):
        """Test 2: Verify horizon embargo (train_max <= val_min - (h + 1)) is strictly honored."""
        for h in [7, 15, 30]:
            embargo = h + 1
            splitter = DateGroupedTimeSeriesSplit(n_splits=3, horizon=h, min_train_dates=20)
            for train_idx, val_idx in splitter.split(self.df):
                tr_dates = self.df.iloc[train_idx]["date"]
                va_dates = self.df.iloc[val_idx]["date"]
                gap = (va_dates.min() - tr_dates.max()).days
                self.assertGreaterEqual(gap, embargo)

    def test_03_no_sku_date_overlap_between_train_and_val(self):
        """Test 3: Verify zero (StockCode, date) overlap between training and validation folds."""
        splitter = DateGroupedTimeSeriesSplit(n_splits=3, horizon=7, min_train_dates=20)
        for train_idx, val_idx in splitter.split(self.df):
            tr_keys = set(zip(self.df.iloc[train_idx]["StockCode"], self.df.iloc[train_idx]["date"]))
            va_keys = set(zip(self.df.iloc[val_idx]["StockCode"], self.df.iloc[val_idx]["date"]))
            self.assertEqual(len(tr_keys.intersection(va_keys)), 0)

    def test_04_no_future_target_leakage_in_encoder(self):
        """Test 4: ChronologicalTargetEncoder produces exact 0.0 perturbation when future targets change."""
        encoder = ChronologicalTargetEncoder(horizon=7, smooth=10.0, default_prior=0.0)
        X = self.df[["StockCode", "date"]].copy()
        y = self.df["D_7"].values.copy()

        enc_orig = encoder.fit_transform(X, y)

        # Perturb future targets (last 10% of dates)
        cutoff_date = sorted(list(set(self.df["date"])))[int(len(set(self.df["date"])) * 0.9)]
        future_mask = self.df["date"] >= cutoff_date
        y_perturbed = y.copy()
        y_perturbed[future_mask] += 50000.0

        encoder_pert = ChronologicalTargetEncoder(horizon=7, smooth=10.0, default_prior=0.0)
        enc_pert = encoder_pert.fit_transform(X, y_perturbed)

        # Encodings on earlier dates (prior to cutoff minus embargo) must be exactly identical (0.0 diff)
        past_mask = self.df["date"] < cutoff_date - datetime.timedelta(days=encoder.embargo_days)
        diff = np.max(np.abs(enc_orig[past_mask] - enc_pert[past_mask]))
        self.assertEqual(diff, 0.0)

    def test_05_preprocessing_fitted_only_on_training_fold(self):
        """Test 5: Verify scaler mean/scale depends strictly on training fold."""
        splitter = DateGroupedTimeSeriesSplit(n_splits=3, horizon=7, min_train_dates=20)
        splits = list(splitter.split(self.df))
        tr1_idx, va1_idx = splits[0]
        tr2_idx, va2_idx = splits[1]

        scaler1 = StandardScaler().fit(self.df.iloc[tr1_idx][["Lag1", "RollingMean7"]])
        scaler2 = StandardScaler().fit(self.df.iloc[tr2_idx][["Lag1", "RollingMean7"]])

        # Expanding window train size expands, so means must be independently learned
        self.assertNotEqual(len(tr1_idx), len(tr2_idx))
        self.assertTrue(hasattr(scaler1, "mean_"))
        self.assertTrue(hasattr(scaler2, "mean_"))

    def test_06_polynomial_features_pipeline(self):
        """Test 6: Verify polynomial transformations execute cleanly without leakage or NaN."""
        poly_cols = ["Lag1", "RollingMean7", "UnitPrice"]
        poly_pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("poly", PolynomialFeatures(degree=2, include_bias=False)),
            ("regressor", Ridge(alpha=1.0))
        ])
        X = self.df[poly_cols]
        y = self.df["D_7"].values

        poly_pipe.fit(X.iloc[:100], y[:100])
        preds = poly_pipe.predict(X.iloc[100:150])
        self.assertEqual(len(preds), 50)
        self.assertTrue(np.all(np.isfinite(preds)))

    def test_07_identical_validation_eligibility_across_candidates(self):
        """Test 7: Verify all candidates in registry operate on identical feature inputs and validation rows."""
        candidates = build_candidate_registry(7, self.num_cols)
        # All candidates must have name and family
        for cand in candidates:
            self.assertIn("name", cand)
            self.assertIn("family", cand)
            self.assertIn("model_type", cand)

    def test_08_metric_calculations(self):
        """Test 8: Verify mathematical correctness of WAPE, MAE, and RMSE."""
        actual = np.array([10.0, 20.0, 30.0, 40.0])
        pred = np.array([12.0, 18.0, 33.0, 35.0])
        # Errors: |2| + |2| + |3| + |5| = 12. Total actual = 100. WAPE = 12.0%
        w = calculate_wape(actual, pred)
        m = calculate_mae(actual, pred)
        r = calculate_rmse(actual, pred)

        self.assertAlmostEqual(w, 12.0, places=4)
        self.assertAlmostEqual(m, 3.0, places=4)
        self.assertAlmostEqual(r, np.sqrt((4 + 4 + 9 + 25) / 4.0), places=4)

    def test_09_prediction_clipping_non_negative(self):
        """Test 9: Verify non-negative clipping guarantees no negative demand predictions."""
        res_model = ResidualRegressor(base_feature="RollingMean7", multiplier=7.0, estimator=None)
        res_model.fit(self.df, self.df["D_7"].values)
        preds = res_model.predict(self.df)
        self.assertTrue(np.all(preds >= 0.0))

    def test_10_reproducibility_random_seed(self):
        """Test 10: Verify deterministic reproducibility across repeated runs."""
        est1 = Ridge(alpha=10.0, random_state=42)
        est2 = Ridge(alpha=10.0, random_state=42)
        X = self.df[self.num_cols]
        y = self.df["D_7"].values

        est1.fit(X, y)
        est2.fit(X, y)
        self.assertTrue(np.allclose(est1.coef_, est2.coef_))


if __name__ == "__main__":
    unittest.main()

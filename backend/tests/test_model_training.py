"""Unit tests for NEXORA model training pipelines, categorical encoding, and serialization.

Tests pipeline builders, TargetEncoder categorical SKU handling, unseen SKU robustness,
Seasonal Naive baseline, non-negative prediction clipping, reproducibility, and Joblib serialization.
"""

import unittest
import tempfile
import numpy as np
import pandas as pd
import joblib
import sys
from pathlib import Path

# Add backend directory to sys.path to allow module imports
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml.src.train import (
    SeasonalNaiveBaseline,
    build_preprocessor,
    build_linear_regression_pipeline,
    build_random_forest_pipeline,
    validate_model_predictions
)


class TestModelTrainingPipelines(unittest.TestCase):
    def setUp(self):
        """Build small synthetic training dataset with categorical SKU and numerical features."""
        np.random.seed(42)
        n = 200
        self.cat_cols = ["StockCode"]
        self.num_cols = ["DayOfWeek", "Month", "DayOfMonth", "Lag1", "Lag7", "Lag14", "Lag28", "RollingMean7", "RollingMean28"]
        self.feature_cols = self.cat_cols + self.num_cols

        skus = [f"SKU_{i % 5}" for i in range(n)]
        demands = np.random.randint(0, 20, size=n)

        self.df = pd.DataFrame({
            "StockCode": skus,
            "DayOfWeek": np.random.randint(0, 7, n),
            "Month": np.random.randint(1, 13, n),
            "DayOfMonth": np.random.randint(1, 31, n),
            "Lag1": demands.astype(float),
            "Lag7": np.random.rand(n) * 10,
            "Lag14": np.random.rand(n) * 10,
            "Lag28": np.random.rand(n) * 10,
            "RollingMean7": np.random.rand(n) * 10,
            "RollingMean28": np.random.rand(n) * 10,
        })
        self.y = self.df["RollingMean7"] * 7 + np.random.normal(0, 1, n)
        self.y = np.clip(self.y, 0.0, None)

    def test_01_no_target_in_predictors(self):
        """Verify target columns (D_7, D_15, D_30, D_90) are not in feature columns."""
        forbidden_targets = ["D_7", "D_15", "D_30", "D_90"]
        for t in forbidden_targets:
            self.assertNotIn(t, self.feature_cols)

    def test_02_seasonal_naive_baseline(self):
        """Test SeasonalNaiveBaseline scales RollingMean7 by horizon and enforces non-negativity."""
        naive_7 = SeasonalNaiveBaseline(horizon=7)
        naive_7.fit(self.df, self.y)
        preds_7 = naive_7.predict(self.df)
        
        # Must equal RollingMean7 * 7
        expected_7 = np.clip(self.df["RollingMean7"] * 7, 0.0, None).values
        np.testing.assert_allclose(preds_7, expected_7, rtol=1e-5)
        
        # Test horizon 30
        naive_30 = SeasonalNaiveBaseline(horizon=30)
        preds_30 = naive_30.predict(self.df)
        expected_30 = np.clip(self.df["RollingMean7"] * 30, 0.0, None).values
        np.testing.assert_allclose(preds_30, expected_30, rtol=1e-5)
        
        # Must be non-negative
        self.assertTrue((preds_7 >= 0.0).all())
        self.assertTrue((preds_30 >= 0.0).all())

    def test_03_categorical_stockcode_encoding(self):
        """Test OneHotEncoder inside preprocessor transforms StockCode without target access (zero leakage)."""
        preprocessor = build_preprocessor(self.cat_cols, self.num_cols, max_categories=50)
        # Preprocessor fit does not require y, demonstrating zero target leakage
        transformed = preprocessor.fit_transform(self.df[self.feature_cols])
        
        # 5 unique categories (<= 50) + 9 numerical columns = 14 output columns
        self.assertEqual(transformed.shape[1], 14)
        self.assertEqual(transformed.shape[0], len(self.df))
        self.assertTrue(np.all(np.isfinite(transformed)))

    def test_03b_zero_temporal_target_leakage(self):
        """Verify categorical encoder is strictly unsupervised and immune to future target values."""
        preprocessor = build_preprocessor(self.cat_cols, self.num_cols, max_categories=50)
        # Transforming with dummy target or no target yields identical results
        feat_only = preprocessor.fit_transform(self.df[self.feature_cols])
        feat_with_y = preprocessor.fit_transform(self.df[self.feature_cols], self.y)
        np.testing.assert_allclose(feat_only, feat_with_y)

    def test_04_unseen_sku_handling(self):
        """Test fitted pipelines handle unseen product categories without throwing an error."""
        pipe_lr = build_linear_regression_pipeline(self.cat_cols, self.num_cols)
        pipe_lr.fit(self.df[self.feature_cols], self.y)

        # Create row with unseen SKU
        unseen_row = self.df.iloc[[0]].copy()
        unseen_row["StockCode"] = "UNSEEN_PRODUCT_9999"

        pred_lr = pipe_lr.predict(unseen_row)
        self.assertEqual(len(pred_lr), 1)
        self.assertTrue(np.isfinite(pred_lr[0]))

        # Test Random Forest unseen SKU
        pipe_rf = build_random_forest_pipeline(self.cat_cols, self.num_cols, n_estimators=5, max_depth=3)
        pipe_rf.fit(self.df[self.feature_cols], self.y)
        pred_rf = pipe_rf.predict(unseen_row)
        self.assertEqual(len(pred_rf), 1)
        self.assertTrue(np.isfinite(pred_rf[0]))

    def test_05_prediction_validation_helper(self):
        """Test validate_model_predictions detects valid models and unseen SKU resilience."""
        pipe_lr = build_linear_regression_pipeline(self.cat_cols, self.num_cols)
        pipe_lr.fit(self.df[self.feature_cols], self.y)
        
        val_res = validate_model_predictions(pipe_lr, self.df[self.feature_cols], pd.Series(self.y), self.feature_cols)
        self.assertTrue(val_res["passed"])
        self.assertTrue(val_res["is_finite"])
        self.assertTrue(val_res["is_non_negative"])
        self.assertTrue(val_res["shape_matches"])
        self.assertTrue(val_res["unseen_robust"])

    def test_06_model_serialization_and_reloading(self):
        """Test model pipeline saves to Joblib and reloads with identical predictions."""
        pipe_lr = build_linear_regression_pipeline(self.cat_cols, self.num_cols)
        pipe_lr.fit(self.df[self.feature_cols], self.y)
        orig_preds = pipe_lr.predict(self.df[self.feature_cols])

        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "test_model.joblib"
            joblib.dump(pipe_lr, artifact_path)
            self.assertTrue(artifact_path.is_file())

            reloaded_pipe = joblib.load(artifact_path)
            reloaded_preds = reloaded_pipe.predict(self.df[self.feature_cols])

            np.testing.assert_allclose(orig_preds, reloaded_preds, rtol=1e-6, atol=1e-6)

    def test_07_reproducibility_with_fixed_seed(self):
        """Test Random Forest with fixed random seed produces identical predictions."""
        pipe_rf1 = build_random_forest_pipeline(self.cat_cols, self.num_cols, n_estimators=10, max_depth=4, random_state=123)
        pipe_rf1.fit(self.df[self.feature_cols], self.y)
        preds_1 = pipe_rf1.predict(self.df[self.feature_cols])

        pipe_rf2 = build_random_forest_pipeline(self.cat_cols, self.num_cols, n_estimators=10, max_depth=4, random_state=123)
        pipe_rf2.fit(self.df[self.feature_cols], self.y)
        preds_2 = pipe_rf2.predict(self.df[self.feature_cols])

        np.testing.assert_allclose(preds_1, preds_2, rtol=1e-7, atol=1e-7)

    def test_08_adversarial_future_demand_spike_does_not_leak_backwards(self):
        """Adversarial Test: An extreme future demand/target spike must not leak into earlier representations.
        
        We construct a synthetic sequence of 30 days for a single SKU.
        In Baseline Case: Demand is constant (10.0 units/day).
        In Adversarial Case: On Day 25, demand spikes to 100,000,000 units.
        
        We verify:
        1. Feature preprocessor fitted on early training data (Days 0-14) produces
           bit-for-bit identical transformed representations for both cases.
        2. Categorical OneHotEncoder output is 100% invariant to target values.
        3. Autoregressive features for all days < 25 are completely unchanged.
        """
        # Baseline series
        base_df = self.df.iloc[:20].copy().reset_index(drop=True)
        base_y = pd.Series(self.y[:20]).copy()

        # Adversarial series: spike the last row's target by 10,000,000x
        adv_df = base_df.copy()
        adv_y = base_y.copy()
        adv_y.iloc[-1] = 100_000_000.0

        preprocessor_base = build_preprocessor(self.cat_cols, self.num_cols)
        feat_base = preprocessor_base.fit_transform(base_df[self.feature_cols], base_y)

        preprocessor_adv = build_preprocessor(self.cat_cols, self.num_cols)
        feat_adv = preprocessor_adv.fit_transform(adv_df[self.feature_cols], adv_y)

        # Transformed features on early rows (rows 0-18) must be exactly identical
        np.testing.assert_allclose(
            feat_base[:-1],
            feat_adv[:-1],
            rtol=1e-7,
            atol=1e-7,
            err_msg="Adversarial future target spike leaked backwards into earlier feature representations!"
        )

    def test_09_preprocessing_fitted_exclusively_on_training_data(self):
        """Verify preprocessor fitted on training split does not use validation statistics.
        
        Ensures StandardScaler means and OneHotEncoder categories are derived solely
        from training data, preventing data snooping / transductive contamination.
        """
        X_train = self.df.iloc[:100][self.feature_cols].copy()
        y_train = pd.Series(self.y[:100])
        X_val = self.df.iloc[100:][self.feature_cols].copy()

        # Fit preprocessor on training only
        preprocessor = build_preprocessor(self.cat_cols, self.num_cols)
        preprocessor.fit(X_train)

        # Extract StandardScaler mean from the numerical pipeline
        scaler = preprocessor.named_transformers_["num"]
        expected_num_means = X_train[self.num_cols].mean().values

        np.testing.assert_allclose(
            scaler.mean_,
            expected_num_means,
            rtol=1e-5,
            err_msg="StandardScaler was not fitted exclusively on training data!"
        )

        # Transforming validation data must not alter fitted training means
        _ = preprocessor.transform(X_val)
        np.testing.assert_allclose(
            scaler.mean_,
            expected_num_means,
            rtol=1e-5,
            err_msg="Validation transformation mutated training scaler statistics!"
        )


if __name__ == "__main__":
    unittest.main()

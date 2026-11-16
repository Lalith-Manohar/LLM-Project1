"""Unit tests for NEXORA model evaluation metrics and chronological splitting (Phase 1, Task 5).

Tests MAE, RMSE, WAPE calculations (including zero-denominator handling),
chronological splitting, purge/embargo window enforcement, and absence of target window leakage.
"""

import unittest
import datetime
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add backend directory to sys.path to allow module imports
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml.src.evaluate import (
    calculate_mae,
    calculate_rmse,
    calculate_wape,
    evaluate_predictions,
    get_chronological_split
)


class TestModelEvaluation(unittest.TestCase):
    def test_01_mae_calculation(self):
        """Test Mean Absolute Error calculation against manual values."""
        y_true = np.array([10.0, 20.0, 30.0])
        y_pred = np.array([12.0, 18.0, 35.0])
        # Absolute errors: 2, 2, 5 -> Mean: 9 / 3 = 3.0
        self.assertAlmostEqual(calculate_mae(y_true, y_pred), 3.0)

    def test_02_rmse_calculation(self):
        """Test Root Mean Squared Error calculation against manual values."""
        y_true = np.array([10.0, 20.0, 30.0])
        y_pred = np.array([13.0, 16.0, 30.0])
        # Squared errors: 9, 16, 0 -> Mean: 25 / 3 -> sqrt: 2.88675
        expected = np.sqrt(25.0 / 3.0)
        self.assertAlmostEqual(calculate_rmse(y_true, y_pred), expected, places=4)

    def test_03_wape_calculation_standard(self):
        """Test Weighted Absolute Percentage Error calculation."""
        y_true = np.array([100.0, 200.0])
        y_pred = np.array([90.0, 220.0])
        # Abs errors: 10 + 20 = 30. Sum y_true: 300. WAPE = 30 / 300 * 100 = 10.0%
        self.assertAlmostEqual(calculate_wape(y_true, y_pred), 10.0)

    def test_04_wape_zero_denominator_handling(self):
        """Test WAPE zero denominator edge cases."""
        # Case A: Both true and predicted are all zeros -> 0.0% error
        y_true_zero = np.array([0.0, 0.0, 0.0])
        y_pred_zero = np.array([0.0, 0.0, 0.0])
        self.assertEqual(calculate_wape(y_true_zero, y_pred_zero), 0.0)
        
        # Case B: True is all zeros, but prediction is non-zero -> 100.0% error
        y_pred_nonzero = np.array([5.0, 0.0, 1.0])
        self.assertEqual(calculate_wape(y_true_zero, y_pred_nonzero), 100.0)

    def test_05_evaluate_predictions_bundle(self):
        """Test evaluate_predictions returns complete dictionary."""
        y_true = np.array([10.0, 20.0, 30.0])
        y_pred = np.array([10.0, 20.0, 30.0])
        metrics = evaluate_predictions(y_true, y_pred)
        self.assertIn("mae", metrics)
        self.assertIn("rmse", metrics)
        self.assertIn("wape", metrics)
        self.assertEqual(metrics["mae"], 0.0)
        self.assertEqual(metrics["rmse"], 0.0)
        self.assertEqual(metrics["wape"], 0.0)

    def test_06_chronological_splitting_and_purge_embargo(self):
        """Test chronological split strictly enforces purge/embargo gap."""
        # Construct synthetic daily dataset from 2021-01-01 to 2021-02-28
        start_date = datetime.date(2021, 1, 1)
        dates = [start_date + datetime.timedelta(days=i) for i in range(50)]
        
        df = pd.DataFrame({
            "StockCode": ["SKU1"] * 50,
            "date": dates,
            "feat1": [1.0] * 50,
            "D_7": [10.0] * 50
        })
        
        # Validation window: days 35 to 45 (2021-02-05 to 2021-02-15)
        val_start = start_date + datetime.timedelta(days=35)
        val_end = start_date + datetime.timedelta(days=45)
        
        X_train, y_train, X_val, y_val, meta = get_chronological_split(
            df=df,
            horizon=7,
            val_start=val_start,
            val_end=val_end,
            feature_cols=["StockCode", "feat1"],
            target_col="D_7"
        )
        
        # 1. Training observations must precede validation observations
        train_max = pd.to_datetime(meta["train_end_date"]).date()
        val_min = pd.to_datetime(meta["val_start_date"]).date()
        self.assertLess(train_max, val_min)
        
        # 2. Strict Embargo Gap: train_max + 7 days must be strictly before val_min
        embargo_gap = (val_min - train_max).days
        self.assertGreater(embargo_gap, 7)
        self.assertEqual(meta["embargo_gap_days"], embargo_gap)
        self.assertTrue(meta["is_leakage_free"])

    def test_07_exclusion_of_incomplete_targets_and_features(self):
        """Test that rows missing targets or features are excluded from train and val."""
        start_date = datetime.date(2021, 1, 1)
        dates = [start_date + datetime.timedelta(days=i) for i in range(30)]
        
        df = pd.DataFrame({
            "StockCode": ["SKU1"] * 30,
            "date": dates,
            "feat1": [1.0] * 29 + [np.nan],  # Last row missing feature
            "D_7": [10.0] * 20 + [np.nan] * 10  # Last 10 rows missing target
        })
        
        val_start = start_date + datetime.timedelta(days=15)
        val_end = start_date + datetime.timedelta(days=25)
        
        X_train, y_train, X_val, y_val, meta = get_chronological_split(
            df=df,
            horizon=7,
            val_start=val_start,
            val_end=val_end,
            feature_cols=["StockCode", "feat1"],
            target_col="D_7"
        )
        
        # In validation, rows with NaN D_7 (from day 20 onwards) must be excluded
        self.assertFalse(y_val.isnull().any())
        self.assertFalse(X_val.isnull().any().any())
        self.assertFalse(y_train.isnull().any())
        self.assertFalse(X_train.isnull().any().any())

    def test_08_multi_horizon_purge_embargo_all_horizons(self):
        """Verify strict embargo condition across all four horizons (D_7, D_15, D_30, D_90).
        
        Ensures that for each planning horizon:
        1. Embargo gap is strictly greater than the horizon (embargo_gap_days > H).
        2. Last training date + H is strictly less than validation start date.
        3. No overlap exists between the training target window and validation window.
        """
        start_date = datetime.date(2021, 1, 1)
        dates = [start_date + datetime.timedelta(days=i) for i in range(250)]
        
        df = pd.DataFrame({
            "StockCode": ["SKU1"] * 250,
            "date": dates,
            "feat1": [1.0] * 250,
            "D_7": [10.0] * 250,
            "D_15": [20.0] * 250,
            "D_30": [40.0] * 250,
            "D_90": [100.0] * 250
        })
        
        val_start = start_date + datetime.timedelta(days=150)
        val_end = start_date + datetime.timedelta(days=180)
        
        for h in [7, 15, 30, 90]:
            _, _, _, _, meta = get_chronological_split(
                df=df,
                horizon=h,
                val_start=val_start,
                val_end=val_end,
                feature_cols=["StockCode", "feat1"],
                target_col=f"D_{h}"
            )
            # 1. Embargo gap must strictly exceed horizon
            self.assertGreater(
                meta["embargo_gap_days"], h,
                f"Horizon D_{h}: Embargo gap ({meta['embargo_gap_days']}) must be > {h} days!"
            )
            self.assertTrue(meta["is_leakage_free"])
            
            # 2. Last training observation's target ends at (train_max + H)
            train_max = pd.to_datetime(meta["train_end_date"]).date()
            val_min = pd.to_datetime(meta["val_start_date"]).date()
            last_target_date = train_max + datetime.timedelta(days=h)
            
            self.assertLess(
                last_target_date, val_min,
                f"Horizon D_{h}: Last training target date ({last_target_date}) overlaps validation start ({val_min})!"
            )

    def test_09_training_forward_target_windows_strictly_precede_validation(self):
        """Mathematical assertion: No training sample's label interval overlaps validation interval."""
        start_date = datetime.date(2021, 1, 1)
        dates = [start_date + datetime.timedelta(days=i) for i in range(100)]
        df = pd.DataFrame({
            "StockCode": ["SKU_LEAK_CHECK"] * 100,
            "date": dates,
            "feat1": [5.0] * 100,
            "D_15": [50.0] * 100
        })
        
        val_start = start_date + datetime.timedelta(days=50)
        val_end = start_date + datetime.timedelta(days=70)
        
        X_train, y_train, X_val, y_val, meta = get_chronological_split(
            df=df,
            horizon=15,
            val_start=val_start,
            val_end=val_end,
            feature_cols=["StockCode", "feat1"]
        )
        
        train_cutoff = pd.to_datetime(meta["train_cutoff"]).date()
        # Cutoff must be val_start - (15 + 1) = val_start - 16 days
        expected_cutoff = val_start - datetime.timedelta(days=16)
        self.assertEqual(train_cutoff, expected_cutoff)


if __name__ == "__main__":
    unittest.main()

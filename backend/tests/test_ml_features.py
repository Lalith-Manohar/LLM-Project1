"""Unit tests for NEXORA ML Feature Engineering & Multi-Horizon Forecast Targets (Phase 1, Task 4).

Tests calendar feature extraction, historical demand lags (Lag1, Lag7, Lag14, Lag28),
rolling window statistics (RollingMean7, RollingMean28), forward-looking targets (D_7, D_15, D_30, D_90),
temporal leakage prevention, SKU isolation, and the critical incomplete-target rule.
"""

import unittest
import datetime
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add backend directory to sys.path to allow module imports
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from ml.src.feature_engineering import (
    create_calendar_features,
    create_lag_features,
    create_rolling_features,
    create_future_demand_targets,
    validate_feature_dataset
)


class TestMLFeaturesPipeline(unittest.TestCase):
    def setUp(self):
        """Build synthetic daily time-series covering long lifespans for multiple SKUs."""
        # We need a series with at least 100 consecutive days to test D_90 and RollingMean28
        start_date = datetime.date(2021, 1, 1)
        
        # SKU1 (100 days): Daily demand is known sequence (1, 2, 3, ...)
        sku1_dates = [start_date + datetime.timedelta(days=i) for i in range(120)]
        sku1_demands = [i + 1 for i in range(120)]  # 1 to 120
        
        # SKU2 (40 days): Different SKU to test complete isolation
        sku2_dates = [start_date + datetime.timedelta(days=i) for i in range(40)]
        sku2_demands = [10 for _ in range(40)]  # constant 10
        
        df1 = pd.DataFrame({
            "StockCode": ["SKU1"] * 120,
            "date": sku1_dates,
            "daily_demand": sku1_demands,
            "transaction_count": [1] * 120,
            "revenue": [float(d * 2) for d in sku1_demands],
            "is_imputed": [False] * 120
        })
        
        df2 = pd.DataFrame({
            "StockCode": ["SKU2"] * 40,
            "date": sku2_dates,
            "daily_demand": sku2_demands,
            "transaction_count": [1] * 40,
            "revenue": [20.0] * 40,
            "is_imputed": [False] * 40
        })
        
        self.sample_df = pd.concat([df1, df2], ignore_index=True)

    def test_01_calendar_features_correctness(self):
        """Test DayOfWeek (0-6), Month (1-12), and DayOfMonth (1-31) extraction."""
        df_cal = create_calendar_features(self.sample_df)
        
        # 2021-01-01 was a Friday -> dayofweek = 4
        first_row = df_cal[df_cal["date"] == datetime.date(2021, 1, 1)].iloc[0]
        self.assertEqual(first_row["DayOfWeek"], 4)
        self.assertEqual(first_row["Month"], 1)
        self.assertEqual(first_row["DayOfMonth"], 1)
        
        # 2021-01-03 was a Sunday -> dayofweek = 6
        sun_row = df_cal[df_cal["date"] == datetime.date(2021, 1, 3)].iloc[0]
        self.assertEqual(sun_row["DayOfWeek"], 6)

    def test_02_lag_features_calculations(self):
        """Test Lag1, Lag7, Lag14, and Lag28 calculations."""
        df_lags = create_lag_features(self.sample_df)
        sku1 = df_lags[df_lags["StockCode"] == "SKU1"].sort_values("date").reset_index(drop=True)
        
        # Day index 0: demand = 1. Lags should all be NaN.
        self.assertTrue(np.isnan(sku1.loc[0, "Lag1"]))
        self.assertTrue(np.isnan(sku1.loc[0, "Lag7"]))
        self.assertTrue(np.isnan(sku1.loc[0, "Lag14"]))
        self.assertTrue(np.isnan(sku1.loc[0, "Lag28"]))
        
        # Day index 1: demand = 2. Lag1 should be 1.0 (row 0 demand).
        self.assertEqual(sku1.loc[1, "Lag1"], 1.0)
        
        # Day index 7: demand = 8. Lag7 should be 1.0 (row 0 demand).
        self.assertEqual(sku1.loc[7, "Lag7"], 1.0)
        self.assertEqual(sku1.loc[7, "Lag1"], 7.0)
        
        # Day index 14: demand = 15. Lag14 should be 1.0.
        self.assertEqual(sku1.loc[14, "Lag14"], 1.0)
        
        # Day index 28: demand = 29. Lag28 should be 1.0.
        self.assertEqual(sku1.loc[28, "Lag28"], 1.0)

    def test_03_and_04_rolling_means_and_exclusion_of_current_date(self):
        """Test RollingMean7 and RollingMean28 calculations and verify current date exclusion."""
        df_roll = create_rolling_features(self.sample_df)
        sku1 = df_roll[df_roll["StockCode"] == "SKU1"].sort_values("date").reset_index(drop=True)
        
        # Rows 0 through 6 must be NaN for RollingMean7
        for i in range(7):
            self.assertTrue(np.isnan(sku1.loc[i, "RollingMean7"]), f"Row {i} should be NaN for RollingMean7")
            
        # Row 7 (the 8th day): demand = 8.
        # RollingMean7 must use rows 0..6 (demands 1, 2, 3, 4, 5, 6, 7).
        # Expected mean: (1 + 2 + 3 + 4 + 5 + 6 + 7) / 7 = 28 / 7 = 4.0.
        # Note: demand of row 7 (8) must NOT be included!
        self.assertEqual(sku1.loc[7, "RollingMean7"], 4.0)
        
        # Row 8: demands 2..8 -> (2 + 3 + 4 + 5 + 6 + 7 + 8) / 7 = 35 / 7 = 5.0.
        self.assertEqual(sku1.loc[8, "RollingMean7"], 5.0)
        
        # Rows 0 through 27 must be NaN for RollingMean28
        for i in range(28):
            self.assertTrue(np.isnan(sku1.loc[i, "RollingMean28"]), f"Row {i} should be NaN for RollingMean28")
            
        # Row 28: RollingMean28 must use rows 0..27 (demands 1 through 28).
        # Sum of 1..28 = 28 * 29 / 2 = 406. Mean = 406 / 28 = 14.5.
        self.assertEqual(sku1.loc[28, "RollingMean28"], 14.5)

    def test_05_to_09_multi_horizon_targets_and_exclusion_of_current_date(self):
        """Test D_7, D_15, D_30, D_90 targets and verify current date is excluded."""
        df_targets = create_future_demand_targets(self.sample_df, horizons=[7, 15, 30, 90])
        sku1 = df_targets[df_targets["StockCode"] == "SKU1"].sort_values("date").reset_index(drop=True)
        
        # Row 0 (demand = 1):
        # D_7 must sum rows 1 through 7 (demands 2, 3, 4, 5, 6, 7, 8).
        # Sum = 2 + 3 + 4 + 5 + 6 + 7 + 8 = 35.
        # Row 0 demand (1) must NOT be in D_7!
        self.assertEqual(sku1.loc[0, "D_7"], 35.0)
        
        # D_15 must sum rows 1 through 15 (demands 2 through 16).
        # Sum = 15 * (2 + 16) / 2 = 135.
        self.assertEqual(sku1.loc[0, "D_15"], 135.0)
        
        # D_30 must sum rows 1 through 30 (demands 2 through 31).
        # Sum = 30 * (2 + 31) / 2 = 495.
        self.assertEqual(sku1.loc[0, "D_30"], 495.0)
        
        # D_90 must sum rows 1 through 90 (demands 2 through 91).
        # Sum = 90 * (2 + 91) / 2 = 4185.
        self.assertEqual(sku1.loc[0, "D_90"], 4185.0)

    def test_10_sku_isolation(self):
        """Test that different SKUs never influence each other's lags, rollings, or targets."""
        df_feat = create_lag_features(self.sample_df)
        df_feat = create_rolling_features(df_feat)
        df_feat = create_future_demand_targets(df_feat, horizons=[7, 15, 30, 90])
        
        sku2 = df_feat[df_feat["StockCode"] == "SKU2"].sort_values("date").reset_index(drop=True)
        
        # Row 0 of SKU2 must have NaN for Lag1, regardless of SKU1 ending earlier or later
        self.assertTrue(np.isnan(sku2.loc[0, "Lag1"]))
        self.assertTrue(np.isnan(sku2.loc[0, "RollingMean7"]))
        
        # Row 7 of SKU2 has constant demand = 10, so RollingMean7 must be 10.0
        self.assertEqual(sku2.loc[7, "RollingMean7"], 10.0)
        
        # Target D_7 on row 0 of SKU2 must be 7 * 10 = 70.0
        self.assertEqual(sku2.loc[0, "D_7"], 70.0)

    def test_11_incomplete_future_targets_remain_missing(self):
        """Test critical incomplete-target rule: missing future horizons stay NaN."""
        df_targets = create_future_demand_targets(self.sample_df, horizons=[7, 15, 30, 90])
        sku1 = df_targets[df_targets["StockCode"] == "SKU1"].sort_values("date").reset_index(drop=True)
        total_len = len(sku1)  # 120
        
        # Last 7 rows (indices 113 to 119) of D_7 MUST be NaN
        for i in range(total_len - 7, total_len):
            self.assertTrue(np.isnan(sku1.loc[i, "D_7"]), f"Row {i} should be NaN for D_7")
        # Row 112 should have a valid D_7 (exactly 7 days remain: 113..119)
        self.assertFalse(np.isnan(sku1.loc[total_len - 8, "D_7"]))
        
        # Last 15 rows of D_15 MUST be NaN
        for i in range(total_len - 15, total_len):
            self.assertTrue(np.isnan(sku1.loc[i, "D_15"]), f"Row {i} should be NaN for D_15")
        self.assertFalse(np.isnan(sku1.loc[total_len - 16, "D_15"]))
        
        # Last 90 rows of D_90 MUST be NaN
        for i in range(total_len - 90, total_len):
            self.assertTrue(np.isnan(sku1.loc[i, "D_90"]), f"Row {i} should be NaN for D_90")
        self.assertFalse(np.isnan(sku1.loc[total_len - 91, "D_90"]))
        
        # For SKU2 (length 40), D_90 should be NaN for ALL rows because lifespan < 90
        sku2 = df_targets[df_targets["StockCode"] == "SKU2"]
        self.assertTrue(sku2["D_90"].isnull().all())

    def test_12_initial_missing_values_preserved(self):
        """Test initial lag and rolling missing values are strictly preserved as NaN."""
        df_feat = create_lag_features(self.sample_df)
        df_feat = create_rolling_features(df_feat)
        
        sku1 = df_feat[df_feat["StockCode"] == "SKU1"].sort_values("date").reset_index(drop=True)
        
        # Initial rows must not be zero-filled
        self.assertTrue(np.isnan(sku1.loc[0, "Lag1"]))
        self.assertNotEqual(sku1.loc[0, "Lag1"], 0.0)
        self.assertTrue(np.isnan(sku1.loc[0, "RollingMean7"]))
        self.assertNotEqual(sku1.loc[0, "RollingMean7"], 0.0)

    def test_13_sorting_and_duplicate_validation(self):
        """Test validation catches unsorted or duplicate records."""
        df_feat = create_calendar_features(self.sample_df)
        df_feat = create_lag_features(df_feat)
        df_feat = create_rolling_features(df_feat)
        df_feat = create_future_demand_targets(df_feat, horizons=[7, 15, 30, 90])
        
        # Valid test
        val = validate_feature_dataset(df_feat, self.sample_df, horizons=[7, 15, 30, 90])
        self.assertTrue(val["is_valid"])
        self.assertTrue(val["no_duplicates"])
        
        # Corrupted test with injected duplicate
        corrupted = pd.concat([df_feat, df_feat.iloc[[0]]], ignore_index=True)
        val_corrupted = validate_feature_dataset(corrupted, self.sample_df, horizons=[7, 15, 30, 90])
        self.assertFalse(val_corrupted["is_valid"])
        self.assertFalse(val_corrupted["no_duplicates"])

    def test_14_non_negative_values(self):
        """Test demand, lag, rolling, and target values are never negative."""
        df_feat = create_calendar_features(self.sample_df)
        df_feat = create_lag_features(df_feat)
        df_feat = create_rolling_features(df_feat)
        df_feat = create_future_demand_targets(df_feat, horizons=[7, 15, 30, 90])
        
        cols = ["daily_demand", "Lag1", "Lag7", "Lag14", "Lag28", "RollingMean7", "RollingMean28", "D_7", "D_15", "D_30", "D_90"]
        for c in cols:
            non_null = df_feat[c].dropna()
            self.assertTrue((non_null >= 0).all(), f"Column {c} contains negative values")

    def test_15_sku_cross_boundary_rolling_leakage_prevention(self):
        """Regression test: verify rolling calculations never cross SKU boundaries.
        
        Specifically tests two adjacent SKUs with radically different demand magnitudes:
        - SKU_MASSIVE: 15 consecutive days with daily demand of 10,000 units.
        - SKU_TINY: 10 consecutive days with daily demand of 1 unit.
        
        Verifies that:
        1. SKU_TINY's initial 7 days of RollingMean7 are strictly NaN (preserving missing history).
        2. SKU_TINY's subsequent days (days 8-10) equal exactly 1.0 (mean of prior 1-unit days).
        3. Zero demand (0.0 units) from SKU_MASSIVE (10,000 units) leaks into SKU_TINY.
        """
        massive_dates = [datetime.date(2021, 1, 1) + datetime.timedelta(days=i) for i in range(15)]
        tiny_dates = [datetime.date(2021, 1, 1) + datetime.timedelta(days=i) for i in range(10)]
        
        df_massive = pd.DataFrame({
            "StockCode": ["SKU_MASSIVE"] * 15,
            "date": massive_dates,
            "daily_demand": [10000] * 15,
            "transaction_count": [100] * 15,
            "revenue": [50000.0] * 15,
            "is_imputed": [False] * 15
        })
        df_tiny = pd.DataFrame({
            "StockCode": ["SKU_TINY"] * 10,
            "date": tiny_dates,
            "daily_demand": [1] * 10,
            "transaction_count": [1] * 10,
            "revenue": [5.0] * 10,
            "is_imputed": [False] * 10
        })
        
        df_test = pd.concat([df_massive, df_tiny], ignore_index=True)
        res = create_rolling_features(df_test)
        
        tiny_res = res[res["StockCode"] == "SKU_TINY"].sort_values("date").reset_index(drop=True)
        
        # Days 0 through 6 (first 7 days of SKU_TINY) MUST be NaN
        for day_idx in range(7):
            val = tiny_res.loc[day_idx, "RollingMean7"]
            self.assertTrue(
                np.isnan(val),
                f"Defect detected: SKU_TINY row {day_idx} has RollingMean7 = {val}, expected NaN. "
                "Demand from preceding SKU_MASSIVE leaked across the boundary!"
            )
            
        # Days 7, 8, 9 of SKU_TINY must be exactly 1.0 (no trace of 10,000)
        for day_idx in range(7, 10):
            val = tiny_res.loc[day_idx, "RollingMean7"]
            self.assertAlmostEqual(
                val, 1.0, places=4,
                msg=f"Defect detected: SKU_TINY row {day_idx} has RollingMean7 = {val}, expected 1.0. "
                "Values from SKU_MASSIVE contaminated the rolling average!"
            )
            self.assertLess(
                val, 2.0,
                "Rolling value unexpectedly high! SKU boundary isolation failed."
            )


if __name__ == "__main__":
    unittest.main()

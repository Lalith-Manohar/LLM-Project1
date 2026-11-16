"""Unit tests for NEXORA ML Daily SKU Demand Aggregation & Imputation Module.

Tests aggregation rules, continuous date imputation within SKU lifespan boundaries,
zero-demand filling, demand reconciliation, and validation checks using synthetic data.
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
    aggregate_daily_demand,
    create_continuous_date_series,
    validate_daily_demand_data
)


class TestFeatureEngineeringPipeline(unittest.TestCase):
    def setUp(self):
        """Build synthetic clean sales transactions covering core test scenarios."""
        # Dates:
        # SKU1 (85123A): Sales on 2021-01-01 (two transactions: 5 and 3 units), 2021-01-04 (10 units).
        #                Lifespan: 2021-01-01 to 2021-01-04 (4 days: Jan 1, Jan 2, Jan 3, Jan 4).
        #                Jan 2 & Jan 3 must be imputed with 0 demand.
        # SKU2 (71053):  Sale on 2021-01-02 (4 units).
        #                Lifespan: 2021-01-02 to 2021-01-02 (1 day: Jan 2 only).
        #                No dates before Jan 2 or after Jan 2.
        # SKU3 (POST):   Alphanumeric string code with sales on 2021-01-02 (1 unit) and 2021-01-03 (2 units).
        self.sample_sales = pd.DataFrame([
            {"Invoice": "500001", "StockCode": "85123A", "date": datetime.date(2021, 1, 1), "Quantity": 5, "Price": 2.50, "line_revenue": 12.50},
            {"Invoice": "500002", "StockCode": "85123A", "date": datetime.date(2021, 1, 1), "Quantity": 3, "Price": 2.50, "line_revenue": 7.50},
            {"Invoice": "500003", "StockCode": "85123A", "date": datetime.date(2021, 1, 4), "Quantity": 10, "Price": 3.00, "line_revenue": 30.00},
            {"Invoice": "500004", "StockCode": "71053", "date": datetime.date(2021, 1, 2), "Quantity": 4, "Price": 1.25, "line_revenue": 5.00},
            {"Invoice": "500005", "StockCode": "POST", "date": datetime.date(2021, 1, 2), "Quantity": 1, "Price": 15.00, "line_revenue": 15.00},
            {"Invoice": "500006", "StockCode": "POST", "date": datetime.date(2021, 1, 3), "Quantity": 2, "Price": 15.00, "line_revenue": 30.00},
        ])

    def test_aggregation_sums_and_counts(self):
        """Test that multiple transactions for the same SKU and date are correctly summed."""
        daily_agg = aggregate_daily_demand(self.sample_sales)
        
        # Total rows should be 4 observed product-day pairs:
        # 85123A (2021-01-01), 85123A (2021-01-04), 71053 (2021-01-02), POST (2021-01-02), POST (2021-01-03) -> 5 rows
        self.assertEqual(len(daily_agg), 5)
        
        # Check SKU 85123A on 2021-01-01 (should sum 5 + 3 = 8 units, 2 transactions, revenue 20.0)
        sku1_row = daily_agg[(daily_agg["StockCode"] == "85123A") & (daily_agg["date"] == datetime.date(2021, 1, 1))].iloc[0]
        self.assertEqual(sku1_row["daily_demand"], 8)
        self.assertEqual(sku1_row["transaction_count"], 2)
        self.assertAlmostEqual(sku1_row["revenue"], 20.0)

    def test_continuous_imputation_and_boundaries(self):
        """Test continuous date imputation strictly within SKU lifespan boundaries."""
        daily_agg = aggregate_daily_demand(self.sample_sales)
        continuous_df, stats = create_continuous_date_series(daily_agg)
        
        # Check SKU 85123A lifespan: 2021-01-01 to 2021-01-04 (4 days total)
        sku1_series = continuous_df[continuous_df["StockCode"] == "85123A"].sort_values("date")
        self.assertEqual(len(sku1_series), 4)
        
        dates_sku1 = sku1_series["date"].tolist()
        expected_dates_sku1 = [
            datetime.date(2021, 1, 1),
            datetime.date(2021, 1, 2),
            datetime.date(2021, 1, 3),
            datetime.date(2021, 1, 4),
        ]
        self.assertEqual(dates_sku1, expected_dates_sku1)
        
        # Jan 1 and Jan 4 should not be imputed
        self.assertFalse(sku1_series.iloc[0]["is_imputed"])
        self.assertEqual(sku1_series.iloc[0]["daily_demand"], 8)
        self.assertFalse(sku1_series.iloc[3]["is_imputed"])
        self.assertEqual(sku1_series.iloc[3]["daily_demand"], 10)
        
        # Jan 2 and Jan 3 should be imputed with 0 demand, 0 transactions, 0 revenue
        self.assertTrue(sku1_series.iloc[1]["is_imputed"])
        self.assertEqual(sku1_series.iloc[1]["daily_demand"], 0)
        self.assertEqual(sku1_series.iloc[1]["transaction_count"], 0)
        self.assertEqual(sku1_series.iloc[1]["revenue"], 0.0)
        
        self.assertTrue(sku1_series.iloc[2]["is_imputed"])
        self.assertEqual(sku1_series.iloc[2]["daily_demand"], 0)
        self.assertEqual(sku1_series.iloc[2]["transaction_count"], 0)
        self.assertEqual(sku1_series.iloc[2]["revenue"], 0.0)

    def test_single_day_lifespan(self):
        """Test SKU with only one observed sale date has exactly 1 row and 0 imputed days."""
        daily_agg = aggregate_daily_demand(self.sample_sales)
        continuous_df, stats = create_continuous_date_series(daily_agg)
        
        sku2_series = continuous_df[continuous_df["StockCode"] == "71053"]
        self.assertEqual(len(sku2_series), 1)
        self.assertFalse(sku2_series.iloc[0]["is_imputed"])
        self.assertEqual(sku2_series.iloc[0]["daily_demand"], 4)
        self.assertEqual(sku2_series.iloc[0]["date"], datetime.date(2021, 1, 2))

    def test_alphanumeric_stockcode_preservation(self):
        """Test alphanumeric stock codes remain clean strings."""
        daily_agg = aggregate_daily_demand(self.sample_sales)
        continuous_df, stats = create_continuous_date_series(daily_agg)
        
        skus = set(continuous_df["StockCode"].unique())
        self.assertIn("85123A", skus)
        self.assertIn("71053", skus)
        self.assertIn("POST", skus)
        for code in continuous_df["StockCode"]:
            self.assertIsInstance(code, str)

    def test_exact_demand_reconciliation(self):
        """Test total quantity in raw sales exactly matches continuous daily demand."""
        daily_agg = aggregate_daily_demand(self.sample_sales)
        continuous_df, stats = create_continuous_date_series(daily_agg)
        
        raw_total_units = self.sample_sales["Quantity"].sum()
        agg_total_units = daily_agg["daily_demand"].sum()
        continuous_total_units = continuous_df["daily_demand"].sum()
        
        self.assertEqual(raw_total_units, agg_total_units)
        self.assertEqual(raw_total_units, continuous_total_units)
        self.assertEqual(raw_total_units, 25)

    def test_validation_function(self):
        """Test validate_daily_demand_data passes on valid data and catches anomalies."""
        daily_agg = aggregate_daily_demand(self.sample_sales)
        continuous_df, stats = create_continuous_date_series(daily_agg)
        
        val_result = validate_daily_demand_data(self.sample_sales, daily_agg, continuous_df)
        self.assertTrue(val_result["is_valid"])
        self.assertTrue(val_result["no_duplicates"])
        self.assertTrue(val_result["continuity_valid"])
        self.assertTrue(val_result["reconciled_demand"])
        self.assertTrue(val_result["non_negative_demand"])
        
        # Test detection of an injected duplicate
        corrupted_df = pd.concat([continuous_df, continuous_df.iloc[[0]]], ignore_index=True)
        corrupted_val = validate_daily_demand_data(self.sample_sales, daily_agg, corrupted_df)
        self.assertFalse(corrupted_val["is_valid"])
        self.assertFalse(corrupted_val["no_duplicates"])

    def test_empty_dataframe_handling(self):
        """Test pipeline behavior when provided an empty sales dataframe."""
        empty_sales = pd.DataFrame(columns=["Invoice", "StockCode", "date", "Quantity", "Price", "line_revenue"])
        daily_agg = aggregate_daily_demand(empty_sales)
        self.assertTrue(daily_agg.empty)
        
        continuous_df, stats = create_continuous_date_series(daily_agg)
        self.assertTrue(continuous_df.empty)
        self.assertEqual(stats["total_imputed"], 0)
        
        val_result = validate_daily_demand_data(empty_sales, daily_agg, continuous_df)
        self.assertTrue(val_result["is_valid"])


if __name__ == "__main__":
    unittest.main()

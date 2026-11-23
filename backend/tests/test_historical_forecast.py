"""Automated CSV-to-Forecast Integration Tests for NEXORA Phase 1.

Validates:
1. Automatic historical sales dataset loading and indexing.
2. Exact feature parity against training dataset (ml_feature_dataset.csv).
3. Automatic multi-horizon prediction via FastAPI with SKU-only payload.
4. Observation date transparency and historical metadata.
5. Error handling for unknown SKUs (HTTP 404).
6. Error handling for insufficient historical records (HTTP 422).
7. Backward compatibility for manual feature payloads.
"""

import math
import unittest
from pathlib import Path
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.services.historical_data_service import (
    HistoricalDataService,
    historical_data_service,
    HistoricalDataNotFoundError,
    InsufficientHistoryError,
    DatasetUnavailableError
)
from app.services.prediction_service import prediction_service
from app.schemas.forecast import ForecastRequest, HistoricalFeatures


class TestHistoricalDataService(unittest.TestCase):
    """Unit tests for the HistoricalDataService and feature calculation logic."""

    @classmethod
    def setUpClass(cls):
        historical_data_service.ensure_loaded()
        prediction_service.ensure_loaded()

    def test_01_service_loaded_and_indexed(self):
        """Verifies dataset is indexed with valid metadata."""
        meta = historical_data_service.get_service_metadata()
        self.assertEqual(meta["status"], "ready")
        self.assertGreaterEqual(meta["total_skus"], 3500)
        self.assertGreaterEqual(meta["total_records"], 1000000)
        self.assertEqual(meta["global_max_date"], "2011-12-09")

    def test_02_feature_parity_against_training_dataset(self):
        """Verifies exact feature calculation parity against ml_feature_dataset.csv across multiple SKUs."""
        feat_path = Path("backend/ml/data/processed/ml_feature_dataset.csv")
        self.assertTrue(feat_path.is_file(), "ml_feature_dataset.csv must exist for parity check")
        
        df_feat = pd.read_csv(feat_path, dtype={"StockCode": str})
        df_feat["StockCode"] = df_feat["StockCode"].str.strip()
        df_feat["date"] = pd.to_datetime(df_feat["date"]).dt.date

        test_skus = ["85123A", "71053", "85099B", "22423", "47566"]
        for sku in test_skus:
            features, context = historical_data_service.get_features_for_sku(sku)
            obs_date = context["observation_date"]
            
            # Match against row in training feature dataset
            match_rows = df_feat[(df_feat["StockCode"] == sku) & (df_feat["date"].astype(str) == obs_date)]
            self.assertFalse(match_rows.empty, f"Row for {sku} on {obs_date} not found in training dataset")
            expected = match_rows.iloc[0]

            self.assertEqual(features.day_of_week, int(expected["DayOfWeek"]))
            self.assertEqual(features.month, int(expected["Month"]))
            self.assertEqual(features.day_of_month, int(expected["DayOfMonth"]))
            self.assertEqual(features.lag_1, float(expected["Lag1"]))
            self.assertEqual(features.lag_7, float(expected["Lag7"]))
            self.assertEqual(features.lag_14, float(expected["Lag14"]))
            self.assertEqual(features.lag_28, float(expected["Lag28"]))
            self.assertAlmostEqual(features.rolling_mean_7, float(expected["RollingMean7"]), places=4)
            self.assertAlmostEqual(features.rolling_mean_28, float(expected["RollingMean28"]), places=4)

    def test_03_unknown_sku_raises_not_found(self):
        """Verifies requesting an unknown SKU raises HistoricalDataNotFoundError."""
        with self.assertRaises(HistoricalDataNotFoundError):
            historical_data_service.get_features_for_sku("NON_EXISTENT_SKU_99999")

    def test_04_insufficient_history_raises_error(self):
        """Verifies SKU with < 29 days (e.g. 90004A with 1 day) raises InsufficientHistoryError."""
        with self.assertRaises(InsufficientHistoryError) as ctx:
            historical_data_service.get_features_for_sku("90004A")
        self.assertIn("minimum 29 days required", str(ctx.exception))


class TestAutomatedForecastAPI(unittest.TestCase):
    """Integration tests for FastAPI endpoints with automatic CSV-to-forecast inference."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_05_sku_only_forecast_successful(self):
        """Verifies submitting only stock_code produces valid 4-horizon predictions."""
        payload = {"stock_code": "85123A"}
        resp = self.client.post("/api/v1/forecast/", json=payload)
        self.assertEqual(resp.status_code, 200)
        
        data = resp.json()
        self.assertEqual(data["stock_code"], "85123A")
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["horizons"], [7, 15, 30, 90])
        self.assertEqual(data["observation_date"], "2011-12-09")
        self.assertTrue(data["is_auto_generated"])
        self.assertGreaterEqual(data["history_days"], 29)

        # Check all 4 horizons
        self.assertIn("7", data["predictions"])
        self.assertIn("15", data["predictions"])
        self.assertIn("30", data["predictions"])
        self.assertIn("90", data["predictions"])
        for h, val in data["predictions"].items():
            self.assertGreaterEqual(val, 0.0)
            self.assertFalse(math.isnan(val))

    def test_06_forecast_alias_endpoint_sku_only(self):
        """Verifies /api/v1/forecast/predict alias functions identically with SKU-only payload."""
        payload = {"stock_code": "71053", "horizons": [7, 30]}
        resp = self.client.post("/api/v1/forecast/predict", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["stock_code"], "71053")
        self.assertEqual(data["horizons"], [7, 30])
        self.assertEqual(data["observation_date"], "2011-12-09")

    def test_07_unknown_sku_returns_404(self):
        """Verifies unknown SKU returns HTTP 404 with clear message."""
        payload = {"stock_code": "UNKNOWN_SKU_XYZ"}
        resp = self.client.post("/api/v1/forecast/", json=payload)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("not found in historical sales records", resp.json()["detail"])

    def test_08_insufficient_history_returns_422(self):
        """Verifies SKU with < 29 days history (90004A) returns HTTP 422 with explanation."""
        payload = {"stock_code": "90004A"}
        resp = self.client.post("/api/v1/forecast/", json=payload)
        self.assertEqual(resp.status_code, 422)
        self.assertIn("Insufficient historical sales data", resp.json()["detail"])
        self.assertIn("minimum 29 days required", resp.json()["detail"])

    def test_09_manual_feature_backward_compatibility(self):
        """Verifies manually specifying features still works without regression."""
        manual_payload = {
            "stock_code": "CUSTOM_SKU_TEST",
            "horizons": [7],
            "features": {
                "day_of_week": 1,
                "month": 5,
                "day_of_month": 10,
                "lag_1": 15.0,
                "lag_7": 12.0,
                "lag_14": 18.0,
                "lag_28": 14.0,
                "rolling_mean_7": 14.2,
                "rolling_mean_28": 15.1
            }
        }
        resp = self.client.post("/api/v1/forecast/", json=manual_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["is_auto_generated"])
        self.assertIn("7", data["predictions"])

    def test_10_partial_manual_feature_rejected(self):
        """Verifies partially providing flat features fails validation with HTTP 422."""
        partial_payload = {
            "stock_code": "85123A",
            "lag_1": 10.0
            # missing other required features
        }
        resp = self.client.post("/api/v1/forecast/", json=partial_payload)
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()

"""Automated test suite for backend startup reliability, model loading, and readiness verification.

Tests:
1. Successful loading of all four models in production.
2. Successful loading and indexing of the historical dataset.
3. Missing model artifact detection and error recording.
4. Corrupt model artifact rejection.
5. Missing historical dataset handling.
6. Invalid historical dataset schema rejection.
7. Model initialization failure state and status reporting.
8. Dataset initialization failure state and status reporting.
9. Liveness probe (/health) returns 200 even when subsystems are uninitialized.
10. Readiness probe (/ready) returns 200 when all subsystems are verified.
11. Readiness probe (/ready) returns 503 when a critical service fails.
12. Forecast requests are rejected with 503 when the backend is not ready.
13. Successful forecast generation for supported SKU 85123A.
14. Preservation of 404 (unknown SKU) and 422 (insufficient history) behaviors.
"""

import sys
import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.services.prediction_service import PredictionService, prediction_service
from app.services.historical_data_service import (
    HistoricalDataService,
    historical_data_service,
    DatasetUnavailableError,
    HistoricalDataNotFoundError,
    InsufficientHistoryError
)
from app.schemas.forecast import ForecastRequest


class TestStartupAndReadiness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure production singletons are initialized for integration tests."""
        prediction_service.ensure_loaded()
        historical_data_service.ensure_loaded()
        cls.client = TestClient(app)

    # -------------------------------------------------------------
    # 1 & 2. Production Services Verification
    # -------------------------------------------------------------
    def test_01_production_models_all_loaded_and_verified(self):
        """Test that all four multi-horizon production models are loaded and ready."""
        self.assertTrue(prediction_service.is_ready())
        status = prediction_service.get_status()
        self.assertTrue(status["ready"])
        self.assertEqual(status["models_count"], 4)
        self.assertEqual(status["loaded_horizons"], [7, 15, 30, 90])
        self.assertIsNone(status["error"])

    def test_02_production_historical_dataset_indexed_and_verified(self):
        """Test that the historical dataset is loaded, indexed, and valid."""
        self.assertTrue(historical_data_service.is_ready())
        status = historical_data_service.get_status()
        self.assertTrue(status["ready"])
        self.assertGreater(status["total_skus"], 3000)
        self.assertGreater(status["total_records"], 1000000)
        self.assertIn("daily_product_demand.csv", status["dataset_file"])
        self.assertIsNone(status["error"])

    # -------------------------------------------------------------
    # 3 & 4 & 7. Model Subsystem Failure Scenarios (Isolated)
    # -------------------------------------------------------------
    def test_03_prediction_service_missing_model_file(self):
        """Test that missing model files raise FileNotFoundError and set load_error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Write valid metadata manifest but omit model binaries
            meta = {
                "milestone": "Test",
                "models": {"D_7": {}, "D_15": {}, "D_30": {}, "D_90": {}}
            }
            with open(tmp_path / "models_metadata.json", "w") as f:
                json.dump(meta, f)

            svc = PredictionService(models_dir=str(tmp_path))
            with self.assertRaises(FileNotFoundError) as ctx:
                svc.load_models()
            self.assertIn("demand_model_7d.joblib", str(ctx.exception))
            self.assertFalse(svc.is_ready())
            self.assertIsNotNone(svc.load_error)
            status = svc.get_status()
            self.assertFalse(status["ready"])
            self.assertIn("demand_model_7d.joblib", status["error"])

    def test_04_prediction_service_corrupt_model_file(self):
        """Test that corrupted model binaries raise RuntimeError and set load_error."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with open(tmp_path / "models_metadata.json", "w") as f:
                json.dump({"milestone": "Test"}, f)
            # Write invalid binary content
            with open(tmp_path / "demand_model_7d.joblib", "wb") as f:
                f.write(b"CORRUPTED_NON_JOBLIB_DATA_HEADER_BYTES")

            svc = PredictionService(models_dir=str(tmp_path))
            with self.assertRaises(RuntimeError) as ctx:
                svc.load_models()
            self.assertIn("Corrupted or unreadable model artifact", str(ctx.exception))
            self.assertFalse(svc.is_ready())
            self.assertIsNotNone(svc.load_error)

    # -------------------------------------------------------------
    # 5, 6 & 8. Dataset Subsystem Failure Scenarios (Isolated)
    # -------------------------------------------------------------
    def test_05_historical_data_service_missing_file(self):
        """Test that a non-existent dataset path raises DatasetUnavailableError."""
        svc = HistoricalDataService(data_path="invalid_path_to_non_existent.csv")
        with self.assertRaises(DatasetUnavailableError):
            svc.load_dataset()
        self.assertFalse(svc.is_ready())
        self.assertIsNotNone(svc._load_error)
        status = svc.get_status()
        self.assertFalse(status["ready"])

    def test_06_historical_data_service_invalid_schema(self):
        """Test that a dataset missing required columns is rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "daily_product_demand.csv"
            # Missing 'daily_demand' column
            df = pd.DataFrame({"StockCode": ["85123A"], "date": ["2011-12-01"]})
            df.to_csv(csv_path, index=False)

            svc = HistoricalDataService(data_path=str(csv_path))
            with self.assertRaises(DatasetUnavailableError) as ctx:
                svc.load_dataset()
            self.assertIn("missing required column", str(ctx.exception))
            self.assertFalse(svc.is_ready())
            self.assertIn("daily_demand", svc._load_error)

    def test_07_historical_data_service_empty_dataset(self):
        """Test that an empty dataset (0 records) is rejected."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "daily_product_demand.csv"
            # Headers only, 0 rows
            df = pd.DataFrame(columns=["StockCode", "date", "daily_demand"])
            df.to_csv(csv_path, index=False)

            svc = HistoricalDataService(data_path=str(csv_path))
            with self.assertRaises(DatasetUnavailableError) as ctx:
                svc.load_dataset()
            self.assertIn("empty", str(ctx.exception).lower())
            self.assertFalse(svc.is_ready())

    # -------------------------------------------------------------
    # 9, 10 & 11. Liveness & Readiness Probes
    # -------------------------------------------------------------
    def test_09_liveness_probe_returns_200(self):
        """Test that /health indicates HTTP process is alive."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "backend")

    def test_10_readiness_probe_returns_200_when_ready(self):
        """Test that /ready returns HTTP 200 with structured component readiness."""
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ready")
        self.assertTrue(data["models"]["ready"])
        self.assertEqual(data["models"]["models_count"], 4)
        self.assertTrue(data["historical_data"]["ready"])
        self.assertGreater(data["historical_data"]["total_skus"], 0)

    def test_11_readiness_returns_503_when_model_service_fails(self):
        """Test that /ready returns HTTP 503 if ML model service is not ready."""
        # Temporarily simulate unready state
        orig_ready = prediction_service.is_loaded
        orig_err = prediction_service.load_error
        try:
            prediction_service.is_loaded = False
            prediction_service.load_error = "Simulated missing model binary"

            response = self.client.get("/ready")
            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertEqual(data["status"], "not_ready")
            self.assertFalse(data["models"]["ready"])
            self.assertEqual(data["models"]["error"], "Simulated missing model binary")

            # Liveness (/health) MUST still return 200
            liveness_resp = self.client.get("/health")
            self.assertEqual(liveness_resp.status_code, 200)
        finally:
            prediction_service.is_loaded = orig_ready
            prediction_service.load_error = orig_err

    def test_12_readiness_returns_503_when_historical_data_fails(self):
        """Test that /ready returns HTTP 503 if historical data service is not ready."""
        orig_ready = historical_data_service._is_loaded
        orig_err = historical_data_service._load_error
        try:
            historical_data_service._is_loaded = False
            historical_data_service._load_error = "Simulated unindexed dataset"

            response = self.client.get("/ready")
            self.assertEqual(response.status_code, 503)
            data = response.json()
            self.assertEqual(data["status"], "not_ready")
            self.assertFalse(data["historical_data"]["ready"])
            self.assertEqual(data["historical_data"]["error"], "Simulated unindexed dataset")
        finally:
            historical_data_service._is_loaded = orig_ready
            historical_data_service._load_error = orig_err

    # -------------------------------------------------------------
    # 12, 13 & 14. Prediction Endpoint Error Handling & Invariance
    # -------------------------------------------------------------
    def test_13_prediction_rejected_with_503_when_service_not_ready(self):
        """Test that forecast requests return HTTP 503 when ML models are unready."""
        orig_ready = prediction_service.is_loaded
        orig_err = prediction_service.load_error
        try:
            prediction_service.is_loaded = False
            prediction_service.load_error = "Models uninitialized"

            response = self.client.post("/api/v1/forecast/predict", json={"stock_code": "85123A"})
            self.assertEqual(response.status_code, 503)
            self.assertIn("Forecasting models are not ready", response.json()["detail"])
        finally:
            prediction_service.is_loaded = orig_ready
            prediction_service.load_error = orig_err

    def test_14_successful_forecast_preserves_output_for_sku_85123a(self):
        """Test that valid forecast requests return 200 with all 4 multi-horizon predictions."""
        response = self.client.post("/api/v1/forecast/predict", json={"stock_code": "85123A"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["stock_code"], "85123A")
        self.assertEqual(data["observation_date"], "2011-12-09")
        self.assertIn(data["history_days"], [374, 739])
        self.assertTrue(data["is_auto_generated"])
        self.assertEqual(set(data["predictions"].keys()), {"7", "15", "30", "90"})
        for h, val in data["predictions"].items():
            self.assertGreater(val, 0.0)

    def test_15_existing_error_behavior_preserved(self):
        """Test that 404 (unknown SKU) and 422 (insufficient history) behaviors remain exact."""
        # 1. Unknown SKU -> HTTP 404
        resp_404 = self.client.post("/api/v1/forecast/predict", json={"stock_code": "UNKNOWN_SKU_NON_EXISTENT"})
        self.assertEqual(resp_404.status_code, 404)
        self.assertIn("was not found in historical sales records", resp_404.json()["detail"])

        # 2. Insufficient History -> HTTP 422
        resp_422 = self.client.post("/api/v1/forecast/predict", json={"stock_code": "90004A"})
        self.assertEqual(resp_422.status_code, 422)
        self.assertIn("Insufficient historical sales data", resp_422.json()["detail"])


if __name__ == "__main__":
    unittest.main()

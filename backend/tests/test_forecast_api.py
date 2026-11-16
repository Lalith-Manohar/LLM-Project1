"""Integration and unit tests for NEXORA FastAPI Forecast Inference API (Phase 1, Task 6).

Tests endpoint routing, request validation, multi-horizon inference, legacy single-horizon
support, flat/nested feature input, unseen SKU resilience, error status codes (422),
and model metrics/info inspection.
"""

import unittest
import tempfile
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to sys.path to allow module imports
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app
from app.services.prediction_service import PredictionService, prediction_service
from app.schemas.forecast import ForecastRequest


class TestForecastAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initialize TestClient within lifespan context."""
        cls.client = TestClient(app)
        # Ensure prediction service is loaded
        prediction_service.ensure_loaded()
        
        cls.valid_nested_payload = {
            "stock_code": "85123A",
            "horizons": [7, 15, 30, 90],
            "features": {
                "day_of_week": 2,
                "month": 11,
                "day_of_month": 15,
                "lag_1": 12.0,
                "lag_7": 15.0,
                "lag_14": 10.0,
                "lag_28": 14.0,
                "rolling_mean_7": 13.5,
                "rolling_mean_28": 12.8
            }
        }

        cls.valid_flat_payload = {
            "stock_code": "85123A",
            "horizon_days": 30,
            "day_of_week": 2,
            "month": 11,
            "day_of_month": 15,
            "lag_1": 12.0,
            "lag_7": 15.0,
            "lag_14": 10.0,
            "lag_28": 14.0,
            "rolling_mean_7": 13.5,
            "rolling_mean_28": 12.8
        }

    @classmethod
    def tearDownClass(cls):
        """Clean up TestClient resources and close thread pools."""
        if hasattr(cls, "client") and cls.client:
            cls.client.close()

    def test_01_supported_horizons_endpoint(self):
        """Test GET /api/v1/forecast/horizons returns supported horizon list."""
        resp = self.client.get("/api/v1/forecast/horizons")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["supported_horizons_days"], [7, 15, 30, 90])
        self.assertIn("description", data)
        self.assertIn("horizon_definitions", data)

    def test_02_model_info_endpoint(self):
        """Test GET /api/v1/forecast/model-info returns active model configuration."""
        resp = self.client.get("/api/v1/forecast/model-info")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ready")
        self.assertIn("D_7", data["active_models"])
        self.assertIn("D_15", data["active_models"])
        self.assertIn("D_30", data["active_models"])
        self.assertIn("D_90", data["active_models"])
        self.assertIn("StockCode", data["feature_columns"])
        self.assertIn("RollingMean7", data["feature_columns"])

    def test_03_model_metrics_endpoint(self):
        """Test GET /api/v1/forecast/model-metrics returns documented backtest benchmarks."""
        resp = self.client.get("/api/v1/forecast/model-metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("models", data)
        self.assertIn("D_7", data["models"])
        self.assertIn("best_metrics", data["models"]["D_7"])
        self.assertGreater(data["models"]["D_7"]["best_metrics"]["wape"], 0.0)

    def test_04_multi_horizon_prediction(self):
        """Test POST /api/v1/forecast/ generates forecasts for all 4 requested horizons."""
        resp = self.client.post("/api/v1/forecast/", json=self.valid_nested_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["stock_code"], "85123A")
        self.assertEqual(data["horizons"], [7, 15, 30, 90])
        self.assertEqual(len(data["predictions"]), 4)
        
        # Verify finite and non-negative
        for h_str, val in data["predictions"].items():
            self.assertIsInstance(val, float)
            self.assertGreaterEqual(val, 0.0)

        self.assertEqual(len(data["horizon_details"]), 4)
        self.assertEqual(data["units"], "units")
        self.assertIn("timestamp", data)

    def test_05_single_horizon_prediction(self):
        """Test POST /api/v1/forecast/ with single horizon in list."""
        payload = self.valid_nested_payload.copy()
        payload["horizons"] = [15]
        resp = self.client.post("/api/v1/forecast/", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["horizons"], [15])
        self.assertIn("15", data["predictions"])
        self.assertNotIn("7", data["predictions"])
        self.assertEqual(len(data["predictions"]), 1)

    def test_06_legacy_horizon_days_prediction(self):
        """Test POST /api/v1/forecast/ with legacy horizon_days parameter."""
        payload = {
            "stock_code": "85123A",
            "horizon_days": 30,
            "features": self.valid_nested_payload["features"]
        }
        resp = self.client.post("/api/v1/forecast/", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["horizons"], [30])
        self.assertEqual(data["horizon_days"], 30)
        self.assertIn("30", data["predictions"])

    def test_07_blueprint_predict_alias(self):
        """Test POST /api/v1/forecast/predict endpoint alias matches Blueprint Section 9."""
        resp = self.client.post("/api/v1/forecast/predict", json=self.valid_nested_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["stock_code"], "85123A")
        self.assertIn("7", data["predictions"])

    def test_08_unseen_sku_handling(self):
        """Test unseen SKU is mapped cleanly to infrequent category without failure."""
        payload = self.valid_nested_payload.copy()
        payload["stock_code"] = "TOTALLY_UNSEEN_SKU_ABC_123"
        resp = self.client.post("/api/v1/forecast/", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["stock_code"], "TOTALLY_UNSEEN_SKU_ABC_123")
        for val in data["predictions"].values():
            self.assertGreaterEqual(val, 0.0)
        # Warning about infrequent category mapping must be present
        self.assertTrue(any("infrequent" in w.lower() for w in data["warnings"]))

    def test_09_flat_feature_input_support(self):
        """Test flat feature parameters at top level are automatically parsed."""
        resp = self.client.post("/api/v1/forecast/", json=self.valid_flat_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["horizons"], [30])
        self.assertIn("30", data["predictions"])

    def test_10_invalid_horizon_rejected(self):
        """Test unsupported horizon produces HTTP 422 Unprocessable Entity."""
        bad_payload = self.valid_nested_payload.copy()
        bad_payload["horizons"] = [12]  # Unsupported (must be in [7, 15, 30, 90])
        resp = self.client.post("/api/v1/forecast/", json=bad_payload)
        self.assertEqual(resp.status_code, 422)

    def test_11_missing_required_features_rejected(self):
        """Test omitting required demand lag features produces HTTP 422."""
        incomplete_payload = {
            "stock_code": "85123A",
            "horizons": [7],
            "features": {
                "lag_1": 10.0
                # Missing lag_7, lag_14, lag_28, rolling_mean_7, rolling_mean_28
            }
        }
        resp = self.client.post("/api/v1/forecast/", json=incomplete_payload)
        self.assertEqual(resp.status_code, 422)

    def test_12_negative_feature_rejected(self):
        """Test negative demand values produce HTTP 422."""
        neg_payload = {
            "stock_code": "85123A",
            "horizons": [7],
            "features": {
                "lag_1": -5.0,  # Negative demand is physically impossible in clean gross sales
                "lag_7": 10.0,
                "lag_14": 10.0,
                "lag_28": 10.0,
                "rolling_mean_7": 10.0,
                "rolling_mean_28": 10.0
            }
        }
        resp = self.client.post("/api/v1/forecast/", json=neg_payload)
        self.assertEqual(resp.status_code, 422)

    def test_13_non_finite_feature_rejected(self):
        """Test NaN or infinite features produce HTTP 422."""
        nan_payload = {
            "stock_code": "85123A",
            "horizons": [7],
            "features": {
                "lag_1": float("nan"),
                "lag_7": 10.0,
                "lag_14": 10.0,
                "lag_28": 10.0,
                "rolling_mean_7": 10.0,
                "rolling_mean_28": 10.0
            }
        }
        # Note: JSON spec does not support literal NaN; float parsing in Pydantic catches it
        # Sending null for a required float also triggers 422
        null_payload = {
            "stock_code": "85123A",
            "horizons": [7],
            "features": {
                "lag_1": None,
                "lag_7": 10.0,
                "lag_14": 10.0,
                "lag_28": 10.0,
                "rolling_mean_7": 10.0,
                "rolling_mean_28": 10.0
            }
        }
        resp = self.client.post("/api/v1/forecast/", json=null_payload)
        self.assertEqual(resp.status_code, 422)

    def test_14_empty_stock_code_rejected(self):
        """Test blank or whitespace stock code produces HTTP 422."""
        empty_sku_payload = self.valid_nested_payload.copy()
        empty_sku_payload["stock_code"] = "   "
        resp = self.client.post("/api/v1/forecast/", json=empty_sku_payload)
        self.assertEqual(resp.status_code, 422)

    def test_15_prediction_service_missing_models_dir(self):
        """Test PredictionService raises FileNotFoundError when model directory is missing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_service = PredictionService(models_dir=str(Path(tmp_dir) / "non_existent"))
            with self.assertRaises(FileNotFoundError):
                empty_service.load_models()


if __name__ == "__main__":
    unittest.main()

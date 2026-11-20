"""Comprehensive test suite for Task 12 experimental forecasting models and API integration.

Covers:
1. Feature engineering validation (extended features, fallbacks, 60d coverage, PIT prices).
2. Service lifecycle and model loading for Task 12 estimators (D_7, D_15, D_30, D_90).
3. End-to-end API endpoints under /api/v1/experimental/.
4. Direct artifact inference vs API parity across multiple SKUs and horizons.
5. Backward compatibility and regression verification for production endpoints.
"""

import math
import datetime
from pathlib import Path
import pytest
import joblib
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.services.historical_data_service import (
    historical_data_service,
    HistoricalDataNotFoundError,
    InsufficientHistoryError
)
from app.services.experimental_prediction_service import experimental_prediction_service
from app.schemas.forecast import ForecastRequest, HistoricalFeatures


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module", autouse=True)
def ensure_services_initialized():
    """Ensure both historical data and experimental models are loaded before tests."""
    historical_data_service.ensure_loaded()
    experimental_prediction_service.ensure_loaded()


# =====================================================================
# SECTION 1: Feature Engineering & Contract Validation
# =====================================================================

def test_feature_engineering_sufficient_history():
    """Verifies that an SKU with complete history generates all 18 numerical features accurately."""
    features, meta = historical_data_service.get_features_for_sku("85123A")

    # Calendar features
    assert 0 <= features.day_of_week <= 6
    assert 1 <= features.month <= 12
    assert 1 <= features.day_of_month <= 31

    # Baseline 9 features
    assert features.lag_1 >= 0.0
    assert features.lag_7 >= 0.0
    assert features.lag_14 >= 0.0
    assert features.lag_28 >= 0.0
    assert features.rolling_mean_7 >= 0.0
    assert features.rolling_mean_28 >= 0.0

    # Extended Task 12 features
    assert features.lag_60 is not None and features.lag_60 >= 0.0
    assert features.rolling_mean_14 is not None and features.rolling_mean_14 >= 0.0
    assert features.rolling_mean_60 is not None and features.rolling_mean_60 >= 0.0
    assert features.rolling_std_7 is not None and features.rolling_std_7 >= 0.0
    assert features.rolling_std_28 is not None and features.rolling_std_28 >= 0.0
    assert features.zero_fraction_28 is not None and 0.0 <= features.zero_fraction_28 <= 1.0
    assert features.momentum_ratio is not None and features.momentum_ratio >= 0.0
    assert features.unit_price is not None and features.unit_price > 0.0
    assert features.has_60d_history == 1.0

    # Metadata validation
    assert meta["is_auto_generated"] is True
    assert meta["history_days"] >= 61
    assert "observation_date" in meta


def test_feature_engineering_limited_history_fallback():
    """Verifies coverage restoration fallback when SKU has between 29 and 60 days of history."""
    # Test with as_of_date that slices history to 35 days for an SKU
    sku_df = historical_data_service._sku_records["85123A"]
    target_date = sku_df.iloc[34]["date"]  # exactly 35 days from start

    features, meta = historical_data_service.get_features_for_sku("85123A", as_of_date=target_date)

    assert meta["history_days"] == 35
    assert features.has_60d_history == 0.0
    # Lag60 must fall back to Lag28
    assert features.lag_60 == features.lag_28
    # RollingMean60 must fall back to RollingMean28
    assert features.rolling_mean_60 == features.rolling_mean_28


def test_feature_engineering_insufficient_history_error():
    """Verifies that an SKU cutoff with fewer than 29 days raises InsufficientHistoryError."""
    sku_df = historical_data_service._sku_records["85123A"]
    target_date = sku_df.iloc[10]["date"]  # only 11 days of history

    with pytest.raises(InsufficientHistoryError):
        historical_data_service.get_features_for_sku("85123A", as_of_date=target_date)


def test_feature_engineering_nonexistent_sku_error():
    """Verifies that querying a nonexistent SKU raises HistoricalDataNotFoundError."""
    with pytest.raises(HistoricalDataNotFoundError):
        historical_data_service.get_features_for_sku("NONEXISTENT_SKU_99999")


def test_point_in_time_unit_price_fallback():
    """Verifies that existing SKUs retrieve PIT prices while unknown SKUs fall back to catalog default."""
    known_price = historical_data_service.get_unit_price("85123A")
    assert known_price > 0.0

    unknown_price = historical_data_service.get_unit_price("COMPLETELY_NEW_SKU")
    assert unknown_price == 2.10  # catalog default price


# =====================================================================
# SECTION 2: Experimental Service Lifecycle & Model Usability
# =====================================================================

def test_experimental_service_is_ready():
    """Verifies that experimental prediction service is fully ready and loaded."""
    assert experimental_prediction_service.is_ready() is True
    status = experimental_prediction_service.get_status()
    assert status["ready"] is True
    assert status["models_count"] == 4
    assert status["loaded_horizons"] == [7, 15, 30, 90]
    assert status["error"] is None


def test_experimental_service_model_info():
    """Verifies that experimental get_model_info returns 20-column feature contract."""
    info = experimental_prediction_service.get_model_info()
    assert info["status"] == "ready"
    assert info["feature_contract_columns_count"] == 20
    assert len(info["feature_columns"]) == 20
    assert "StockCode" in info["feature_columns"]
    assert "date" in info["feature_columns"]
    assert "Lag60" in info["feature_columns"]
    assert "Has60dHistory" in info["feature_columns"]
    assert "UnitPrice" in info["feature_columns"]


def test_experimental_service_model_metrics():
    """Verifies that experimental get_model_metrics returns Task 12 CV and holdout results."""
    metrics = experimental_prediction_service.get_model_metrics()
    assert metrics["dataset_rows"] == 1067371
    assert "models" in metrics
    for h in [7, 15, 30, 90]:
        key = f"D_{h}"
        assert key in metrics["models"]
        h_data = metrics["models"][key]
        assert "holdout_wape" in h_data
        assert "cv_pooled_wape" in h_data
        assert h_data["holdout_wape"] > 0.0


# =====================================================================
# SECTION 3: Experimental API Endpoints
# =====================================================================

def test_experimental_ready_endpoint(client):
    """GET /api/v1/experimental/ready returns 200 OK and ready status."""
    response = client.get("/api/v1/experimental/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["service"] == "experimental_forecast"
    assert data["experimental_models"]["ready"] is True
    assert data["historical_data"]["ready"] is True


def test_experimental_horizons_endpoint(client):
    """GET /api/v1/experimental/forecast/horizons returns 4 supported horizons."""
    response = client.get("/api/v1/experimental/forecast/horizons")
    assert response.status_code == 200
    data = response.json()
    assert data["supported_horizons_days"] == [7, 15, 30, 90]
    assert "models" in data
    assert set(data["models"].keys()) == {"7", "15", "30", "90"}


def test_experimental_model_metrics_endpoint(client):
    """GET /api/v1/experimental/forecast/model-metrics returns Task 12 evaluation metrics."""
    response = client.get("/api/v1/experimental/forecast/model-metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["dataset_rows"] == 1067371
    assert "models" in data
    assert "D_7" in data["models"]
    assert "D_15" in data["models"]
    assert "D_30" in data["models"]
    assert "D_90" in data["models"]


def test_experimental_model_info_endpoint(client):
    """GET /api/v1/experimental/forecast/model-info returns architecture details."""
    response = client.get("/api/v1/experimental/forecast/model-info")
    assert response.status_code == 200
    data = response.json()
    assert data["feature_contract_columns_count"] == 20
    assert data["supported_horizons"] == [7, 15, 30, 90]
    assert "active_models" in data


def test_experimental_predict_endpoint_auto_features(client):
    """POST /api/v1/experimental/forecast/predict generates predictions with auto features."""
    payload = {"stock_code": "85123A"}
    response = client.post("/api/v1/experimental/forecast/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["stock_code"] == "85123A"
    assert data["status"] == "success"
    assert set(data["predictions"].keys()) == {"7", "15", "30", "90"}

    # All predictions must be positive finite numbers
    for h in ["7", "15", "30", "90"]:
        val = data["predictions"][h]
        assert isinstance(val, (int, float))
        assert val > 0.0
        assert math.isfinite(val)

    # Details
    assert len(data["horizon_details"]) == 4
    for detail in data["horizon_details"]:
        assert detail["horizon_days"] in [7, 15, 30, 90]
        assert detail["predicted_demand"] > 0.0
        assert detail["wape"] is not None

    assert data["is_auto_generated"] is True
    assert data["observation_date"] is not None


def test_experimental_predict_root_alias(client):
    """POST /api/v1/experimental/forecast works identically to /predict."""
    payload = {"stock_code": "22423", "horizons": [7, 15]}
    resp1 = client.post("/api/v1/experimental/forecast/predict", json=payload)
    resp2 = client.post("/api/v1/experimental/forecast", json=payload)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["predictions"] == resp2.json()["predictions"]


def test_experimental_predict_manual_features(client):
    """POST /api/v1/experimental/forecast/predict with caller-supplied manual features."""
    payload = {
        "stock_code": "85123A",
        "horizons": [7, 30],
        "features": {
            "day_of_week": 2,
            "month": 6,
            "day_of_month": 15,
            "lag_1": 25.0,
            "lag_7": 30.0,
            "lag_14": 20.0,
            "lag_28": 15.0,
            "rolling_mean_7": 24.5,
            "rolling_mean_28": 22.0,
            "lag_60": 18.0,
            "rolling_mean_14": 23.0,
            "rolling_mean_60": 21.0,
            "rolling_std_7": 4.5,
            "rolling_std_28": 5.2,
            "zero_fraction_28": 0.05,
            "momentum_ratio": 1.065,
            "unit_price": 2.55,
            "has_60d_history": 1.0
        }
    }
    response = client.post("/api/v1/experimental/forecast/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "7" in data["predictions"]
    assert "30" in data["predictions"]
    assert data["is_auto_generated"] is False


def test_experimental_predict_unseen_sku_graceful_fallback(client):
    """POST /api/v1/experimental/forecast/predict with unseen SKU and manual features."""
    payload = {
        "stock_code": "TOTALLY_UNSEEN_PRODUCT_999",
        "horizons": [7, 15, 30, 90],
        "features": {
            "day_of_week": 1,
            "month": 3,
            "day_of_month": 10,
            "lag_1": 5.0,
            "lag_7": 5.0,
            "lag_14": 5.0,
            "lag_28": 5.0,
            "rolling_mean_7": 5.0,
            "rolling_mean_28": 5.0
        }
    }
    response = client.post("/api/v1/experimental/forecast/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    for h in ["7", "15", "30", "90"]:
        assert data["predictions"][h] >= 0.0
        assert math.isfinite(data["predictions"][h])


def test_experimental_predict_nonexistent_sku_404(client):
    """POST /api/v1/experimental/forecast/predict with nonexistent SKU and no features returns 404."""
    payload = {"stock_code": "NONEXISTENT_SKU_000"}
    response = client.post("/api/v1/experimental/forecast/predict", json=payload)
    assert response.status_code == 404


# =====================================================================
# SECTION 4: Direct Artifact Inference vs API Parity
# =====================================================================

@pytest.mark.parametrize("sku", ["85123A", "22423", "47566", "84879"])
def test_direct_artifact_vs_api_parity(sku: str):
    """Guarantees bitwise exact prediction parity between direct model artifact inference and the API service."""
    features, meta = historical_data_service.get_features_for_sku(sku)
    obs_date = datetime.date.fromisoformat(meta["observation_date"])

    # Build direct DataFrame matching 20-column contract
    df_row = pd.DataFrame({
        "StockCode": [sku],
        "date": [obs_date],
        "DayOfWeek": [features.day_of_week],
        "Month": [features.month],
        "DayOfMonth": [features.day_of_month],
        "Lag1": [features.lag_1],
        "Lag7": [features.lag_7],
        "Lag14": [features.lag_14],
        "Lag28": [features.lag_28],
        "Lag60": [features.lag_60],
        "RollingMean7": [features.rolling_mean_7],
        "RollingMean14": [features.rolling_mean_14],
        "RollingMean28": [features.rolling_mean_28],
        "RollingMean60": [features.rolling_mean_60],
        "RollingStd7": [features.rolling_std_7],
        "RollingStd28": [features.rolling_std_28],
        "ZeroFraction28": [features.zero_fraction_28],
        "MomentumRatio": [features.momentum_ratio],
        "UnitPrice": [features.unit_price],
        "Has60dHistory": [features.has_60d_history]
    })

    # Execute service prediction
    req = ForecastRequest(stock_code=sku, horizons=[7, 15, 30, 90])
    resp = experimental_prediction_service.get_forecast(req)

    models_dir = Path("backend/ml/models_task12")
    for h in [7, 15, 30, 90]:
        pipe = joblib.load(models_dir / f"demand_model_{h}d.joblib")
        direct_pred = round(max(0.0, float(pipe.predict(df_row)[0])), 4)
        api_pred = resp.predictions[str(h)]

        assert direct_pred == api_pred, (
            f"Parity mismatch for SKU {sku} horizon D_{h}: "
            f"direct_artifact={direct_pred} vs api_service={api_pred}"
        )


# =====================================================================
# SECTION 5: Production Endpoint Regression & Backward Compatibility
# =====================================================================

def test_production_readiness_probe_backward_compatibility(client):
    """Verifies that /ready and /api/v1/ready return 200 OK and include experimental_models."""
    for path in ["/ready", "/api/v1/ready"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["models"]["ready"] is True
        assert data["historical_data"]["ready"] is True
        assert data["experimental_models"] is not None
        assert data["experimental_models"]["ready"] is True


def test_production_health_check(client):
    """Verifies that /health and /api/v1/health remain operational."""
    for path in ["/health", "/api/v1/health"]:
        response = client.get(path)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


def test_production_forecast_predict_unchanged(client):
    """Verifies that production baseline /api/v1/forecast/predict remains untouched."""
    payload = {"stock_code": "85123A"}
    response = client.post("/api/v1/forecast/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["stock_code"] == "85123A"
    assert "predictions" in data
    assert set(data["predictions"].keys()) == {"7", "15", "30", "90"}
    for h in ["7", "15", "30", "90"]:
        assert data["predictions"][h] > 0.0


def test_evaluation_comparison_endpoint(client):
    """Verifies that /api/v1/forecast/evaluation-comparison returns valid multi-tier benchmarks."""
    response = client.get("/api/v1/forecast/evaluation-comparison")
    assert response.status_code == 200
    data = response.json()

    assert "evaluation_tiers" in data
    assert len(data["evaluation_tiers"]) == 4

    horizons = [t["horizon"] for t in data["evaluation_tiers"]]
    assert horizons == ["D_7", "D_15", "D_30", "D_90"]

    for tier in data["evaluation_tiers"]:
        assert "production_baseline_sku" in tier
        assert "optimized_experimental_sku" in tier
        assert "store_wide_macro" in tier

        opt = tier["optimized_experimental_sku"]
        prod = tier["production_baseline_sku"]
        store = tier["store_wide_macro"]

        # Optimized WAPE should be strictly lower than production WAPE
        assert opt["wape_pct"] < prod["wape_pct"]
        assert opt["wape_improvement_pp"] > 0

        # Store-wide WAPE should be under 30% across all horizons
        assert store["store_wape_pct"] < 30.0


def test_store_wide_forecast_endpoint(client):
    """Verifies that /api/v1/forecast/store-wide returns valid macro demand forecasts."""
    response = client.get("/api/v1/forecast/store-wide")
    assert response.status_code == 200
    data = response.json()

    assert data["scope"] == "STORE_WIDE_AGGREGATE"
    assert "predictions" in data
    assert set(data["predictions"].keys()) == {"7", "15", "30", "90"}

    # All predictions must be positive finite floats
    for h, val in data["predictions"].items():
        assert isinstance(val, (int, float))
        assert val > 0

    assert "horizon_details" in data
    assert len(data["horizon_details"]) == 4
    for detail in data["horizon_details"]:
        assert detail["horizon_days"] in [7, 15, 30, 90]
        assert detail["predicted_store_demand"] > 0
        assert detail["store_wape"] < 30.0

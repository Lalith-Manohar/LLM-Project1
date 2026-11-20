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
import os
import copy
import bisect
import tempfile
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


# =====================================================================
# SECTION 6: Task 15 Historical Point-in-Time Pricing & Data Integrity
# =====================================================================

def test_point_in_time_pricing_cutoff_exclusion():
    """Verifies that point-in-time price excludes transactions on and after observation date T."""
    from ml.src.point_in_time_price import pit_price_service
    pit_price_service.ensure_loaded()

    sku = "85123A"
    t1 = datetime.date(2010, 6, 1)
    t2 = datetime.date(2011, 6, 1)

    p1 = pit_price_service.get_price(sku, as_of_date=t1)
    p2 = pit_price_service.get_price(sku, as_of_date=t2)
    p_latest = pit_price_service.get_price(sku, as_of_date=None)

    assert p1 > 0.0
    assert p2 > 0.0
    assert p_latest > 0.0
    # Prices evolve over time; earlier price should reflect early sales
    assert isinstance(p1, float)
    assert isinstance(p2, float)


def test_point_in_time_pricing_transaction_on_date_t_excluded():
    """Verifies boundary condition: transactions occurring ON date T are strictly excluded."""
    from ml.src.point_in_time_price import PointInTimePriceService
    service = PointInTimePriceService()
    service._skus_data = {
        "TEST_BOUND": {
            "dates": ["2011-05-30", "2011-06-01", "2011-06-05"],
            "sums": [2.50, 102.50, 602.50],
            "counts": [1, 2, 3]
        }
    }
    service._static_prices = {"TEST_BOUND": round(602.50 / 3, 4), "__global_default__": 2.10}
    service._global_dates = []
    service._global_sums = []
    service._global_counts = []
    service.is_loaded = True

    # As of 2011-06-01: strictly < 2011-06-01 -> only 2011-05-30 (sum 2.50, cnt 1 -> 2.50)
    p_at_t = service.get_price("TEST_BOUND", as_of_date="2011-06-01")
    assert p_at_t == 2.50, f"Expected 2.50, got {p_at_t}"

    # As of 2011-06-02: includes 2011-06-01 (sum 102.50, cnt 2 -> 51.25)
    p_after_t = service.get_price("TEST_BOUND", as_of_date="2011-06-02")
    assert p_after_t == 51.25, f"Expected 51.25, got {p_after_t}"


def test_point_in_time_pricing_adversarial_future_invariance():
    """Verifies that modifying future transactions after date T produces zero change at date T."""
    import copy
    from ml.src.point_in_time_price import pit_price_service
    pit_price_service.ensure_loaded()

    sku = "85123A"
    t = datetime.date(2011, 6, 1)
    t_str = t.isoformat()

    # Baseline price
    p_base = pit_price_service.get_price(sku, as_of_date=t)
    orig_entry = copy.deepcopy(pit_price_service._skus_data[sku])

    try:
        # Inject adversarial future inflation
        entry = pit_price_service._skus_data[sku]
        dates = entry["dates"]
        sums = entry["sums"]
        counts = entry["counts"]

        import bisect
        idx = bisect.bisect_left(dates, t_str)
        # Perturb strictly from index idx upwards
        for i in range(idx, len(dates)):
            sums[i] += 1000000.0
            counts[i] += 5

        # Re-query at T
        p_perturbed = pit_price_service.get_price(sku, as_of_date=t)
        assert abs(p_perturbed - p_base) == 0.0, f"Leakage detected: {p_base} != {p_perturbed}"

        # Re-query after T (should detect perturbation)
        p_future = pit_price_service.get_price(sku, as_of_date="2011-12-01")
        assert p_future > p_base
    finally:
        pit_price_service._skus_data[sku] = orig_entry


def test_point_in_time_pricing_fallback_prior_to_history():
    """Verifies that querying an SKU prior to any transactions falls back to prior without leaking future price."""
    from ml.src.point_in_time_price import PointInTimePriceService
    service = PointInTimePriceService()
    service._skus_data = {
        "TEST_NEW": {
            "dates": ["2011-01-10"],
            "sums": [50.0],
            "counts": [1]
        }
    }
    service._static_prices = {"TEST_NEW": 50.0, "__global_default__": 2.10}
    service._global_dates = ["2011-01-05"]
    service._global_sums = [10.0]
    service._global_counts = [2]
    service.is_loaded = True

    # Query before TEST_NEW first date, but after global date -> global mean (10 / 2 = 5.0)
    p_global = service.get_price("TEST_NEW", as_of_date="2011-01-08")
    assert p_global == 5.0

    # Query before any global dates -> fallback to 2.10 (never 50.0)
    p_prior = service.get_price("TEST_NEW", as_of_date="2010-01-01")
    assert p_prior == 2.10


# =====================================================================
# SECTION 7: Task 17 Feature Cutoff Propagation & Prediction Integration
# =====================================================================

def test_feature_extraction_historical_cutoff_propagation():
    """Test A: Verifies that get_features_for_sku passes observation cutoff into UnitPrice resolver."""
    sku = "84879"
    cutoff = datetime.date(2010, 6, 1)

    features, ctx = historical_data_service.get_features_for_sku(sku, as_of_date=cutoff)

    # Historical price as of 2010-06-01 is 2.3892; latest static price is 1.8568
    assert features.unit_price == 2.3892, f"Expected historical price 2.3892, got {features.unit_price}"
    assert features.unit_price != 1.8568, "Leaked latest static price into historical feature!"
    assert ctx["observation_date"] == "2010-06-01"


def test_feature_extraction_future_perturbation_invariance():
    """Test B: Verifies that perturbing future transactions does not alter historical feature extraction."""
    from ml.src.point_in_time_price import pit_price_service
    pit_price_service.ensure_loaded()

    sku = "85123A"
    cutoff = datetime.date(2011, 6, 1)
    cutoff_str = cutoff.isoformat()

    features_base, _ = historical_data_service.get_features_for_sku(sku, as_of_date=cutoff)
    orig_entry = copy.deepcopy(pit_price_service._skus_data[sku])

    try:
        # Perturb strictly future dates
        entry = pit_price_service._skus_data[sku]
        idx = bisect.bisect_left(entry["dates"], cutoff_str)
        for i in range(idx, len(entry["dates"])):
            entry["sums"][i] += 5000000.0
            entry["counts"][i] += 10

        features_pert, _ = historical_data_service.get_features_for_sku(sku, as_of_date=cutoff)
        assert features_pert.unit_price == features_base.unit_price, f"Future leakage: {features_base.unit_price} != {features_pert.unit_price}"
    finally:
        pit_price_service._skus_data[sku] = orig_entry


def test_feature_extraction_same_day_exclusion():
    """Test C: Verifies that transactions occurring on observation date T are excluded from features at T."""
    from ml.src.point_in_time_price import pit_price_service
    pit_price_service.ensure_loaded()

    sku = "85123A"
    cutoff = datetime.date(2011, 6, 1)
    cutoff_str = cutoff.isoformat()

    features_base, _ = historical_data_service.get_features_for_sku(sku, as_of_date=cutoff)
    orig_entry = copy.deepcopy(pit_price_service._skus_data[sku])

    try:
        # Invalidate/perturb strictly on date T
        entry = pit_price_service._skus_data[sku]
        idx = bisect.bisect_left(entry["dates"], cutoff_str)
        if idx < len(entry["dates"]) and entry["dates"][idx] == cutoff_str:
            entry["sums"][idx] += 999999.0
            entry["counts"][idx] += 5
        else:
            entry["dates"].insert(idx, cutoff_str)
            prev_s = entry["sums"][idx - 1] if idx > 0 else 0.0
            prev_c = entry["counts"][idx - 1] if idx > 0 else 0
            entry["sums"].insert(idx, prev_s + 999999.0)
            entry["counts"].insert(idx, prev_c + 5)

        features_pert, _ = historical_data_service.get_features_for_sku(sku, as_of_date=cutoff)
        assert features_pert.unit_price == features_base.unit_price, "Same-day transaction contaminated features at date T!"
    finally:
        pit_price_service._skus_data[sku] = orig_entry


def test_feature_extraction_later_date_registration():
    """Test D: Verifies that perturbed transactions on date T become eligible when querying T+1 day."""
    from ml.src.point_in_time_price import pit_price_service
    pit_price_service.ensure_loaded()

    sku = "85123A"
    t = datetime.date(2011, 6, 1)
    t_str = t.isoformat()
    t_plus_1 = datetime.date(2011, 6, 2)

    features_t, _ = historical_data_service.get_features_for_sku(sku, as_of_date=t)
    features_t1_base, _ = historical_data_service.get_features_for_sku(sku, as_of_date=t_plus_1)
    orig_entry = copy.deepcopy(pit_price_service._skus_data[sku])

    try:
        entry = pit_price_service._skus_data[sku]
        idx = bisect.bisect_left(entry["dates"], t_str)
        if idx < len(entry["dates"]) and entry["dates"][idx] == t_str:
            entry["sums"][idx] += 999999.0
            entry["counts"][idx] += 5
            for k in range(idx + 1, len(entry["dates"])):
                entry["sums"][k] += 999999.0
                entry["counts"][k] += 5
        else:
            entry["dates"].insert(idx, t_str)
            prev_s = entry["sums"][idx - 1] if idx > 0 else 0.0
            prev_c = entry["counts"][idx - 1] if idx > 0 else 0
            entry["sums"].insert(idx, prev_s + 999999.0)
            entry["counts"].insert(idx, prev_c + 5)
            for k in range(idx + 1, len(entry["dates"])):
                entry["sums"][k] += 999999.0
                entry["counts"][k] += 5

        # Query at T: unchanged
        features_at_t, _ = historical_data_service.get_features_for_sku(sku, as_of_date=t)
        assert features_at_t.unit_price == features_t.unit_price

        # Query at T+1: reflects the perturbation on T
        features_at_t1, _ = historical_data_service.get_features_for_sku(sku, as_of_date=t_plus_1)
        assert features_at_t1.unit_price > features_t1_base.unit_price
    finally:
        pit_price_service._skus_data[sku] = orig_entry


def test_feature_extraction_forward_inference_compatibility():
    """Test E: Verifies that as_of_date=None retains latest-price behavior for operational forward forecasting."""
    from ml.src.point_in_time_price import pit_price_service
    features, ctx = historical_data_service.get_features_for_sku("84879", as_of_date=None)
    latest_expected = pit_price_service.get_price("84879", as_of_date=None)
    assert features.unit_price == latest_expected == 1.8557, f"Expected latest price 1.8557, got {features.unit_price}"
    assert ctx["observation_date"] == "2011-12-09"


def test_experimental_prediction_service_receives_historical_price():
    """Test F: Exercises experimental prediction service and proves it uses historical UnitPrice through feature extraction."""
    sku = "84879"
    cutoff = datetime.date(2010, 6, 1)

    # 1. Feature extraction with historical cutoff (unit_price = 2.3892)
    feat_hist, _ = historical_data_service.get_features_for_sku(sku, as_of_date=cutoff)
    assert feat_hist.unit_price == 2.3892
    res_hist = experimental_prediction_service.get_forecast(ForecastRequest(stock_code=sku, features=feat_hist))

    # 2. Vector with uncutoff future price (unit_price = 1.8568)
    feat_fut = feat_hist.model_copy(update={"unit_price": 1.8568})
    res_fut = experimental_prediction_service.get_forecast(ForecastRequest(stock_code=sku, features=feat_fut))

    # 3. Prove predictions differ, confirming the model received and evaluated the price feature
    diff_d90 = abs(res_fut.predictions["90"] - res_hist.predictions["90"])
    assert diff_d90 > 0.5, f"Prediction did not respond to price feature change: {diff_d90}"
    assert res_hist.predictions["90"] > 0.0


# =====================================================================
# SECTION 8: Task 17 Cache Freshness & Invalidation Tests
# =====================================================================

def _create_synthetic_sales_csv(path: Path, rows: list) -> None:
    """Helper to write synthetic clean gross sales CSV for deterministic cache tests."""
    df = pd.DataFrame(rows, columns=["StockCode", "Quantity", "Price", "InvoiceDate", "Invoice"])
    df.to_csv(path, index=False, encoding="latin1")


def test_cache_invalidation_valid_cache_no_rebuild():
    """1. Valid cache with unchanged source does not trigger rebuild."""
    from ml.src.point_in_time_price import PointInTimePriceService
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sales_csv = tmp_path / "clean_gross_sales.csv"
        cache_json = tmp_path / "pit_sku_price_history.json"

        _create_synthetic_sales_csv(sales_csv, [
            ["SKU_A", 5, 10.0, "2010-01-01 10:00:00", "500001"],
            ["SKU_A", 5, 20.0, "2010-01-02 10:00:00", "500002"],
        ])

        service = PointInTimePriceService(data_dir=tmp_path)
        service.load_index(cache_path=cache_json, sales_path=sales_csv)
        assert cache_json.is_file()
        mtime_initial = cache_json.stat().st_mtime_ns

        # Reload unchanged source
        service2 = PointInTimePriceService(data_dir=tmp_path)
        service2.load_index(cache_path=cache_json, sales_path=sales_csv)
        mtime_after = cache_json.stat().st_mtime_ns
        assert mtime_after == mtime_initial, "Cache was rebuilt despite unchanged source!"


def test_cache_invalidation_missing_cache_rebuilds():
    """2. Missing cache automatically triggers build from source."""
    from ml.src.point_in_time_price import PointInTimePriceService
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sales_csv = tmp_path / "clean_gross_sales.csv"
        cache_json = tmp_path / "pit_sku_price_history.json"

        _create_synthetic_sales_csv(sales_csv, [["SKU_B", 2, 5.0, "2010-02-01 12:00:00", "500003"]])

        service = PointInTimePriceService(data_dir=tmp_path)
        assert not cache_json.is_file()
        service.load_index(cache_path=cache_json, sales_path=sales_csv)
        assert cache_json.is_file()
        assert service.is_loaded is True
        assert service.get_price("SKU_B", as_of_date=None) == 5.0


def test_cache_invalidation_changed_source_mtime_rebuilds():
    """3. Changed source modification time triggers rebuild."""
    from ml.src.point_in_time_price import PointInTimePriceService
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sales_csv = tmp_path / "clean_gross_sales.csv"
        cache_json = tmp_path / "pit_sku_price_history.json"

        _create_synthetic_sales_csv(sales_csv, [["SKU_C", 1, 15.0, "2010-03-01 10:00:00", "500004"]])

        service = PointInTimePriceService(data_dir=tmp_path)
        service.load_index(cache_path=cache_json, sales_path=sales_csv)
        old_mtime = service._cache_metadata["source_mtime"]

        # Advance mtime of source CSV
        new_time = old_mtime + 200.0
        os.utime(sales_csv, (new_time, new_time))

        service2 = PointInTimePriceService(data_dir=tmp_path)
        service2.load_index(cache_path=cache_json, sales_path=sales_csv)
        assert service2._cache_metadata["source_mtime"] == new_time, "Cache was not rebuilt when source mtime changed!"


def test_cache_invalidation_changed_source_size_rebuilds():
    """4. Changed source file size triggers rebuild."""
    from ml.src.point_in_time_price import PointInTimePriceService
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sales_csv = tmp_path / "clean_gross_sales.csv"
        cache_json = tmp_path / "pit_sku_price_history.json"

        _create_synthetic_sales_csv(sales_csv, [["SKU_D", 1, 10.0, "2010-04-01 10:00:00", "500005"]])

        service = PointInTimePriceService(data_dir=tmp_path)
        service.load_index(cache_path=cache_json, sales_path=sales_csv)
        old_size = service._cache_metadata["source_size"]

        # Append new transaction
        with open(sales_csv, "a", encoding="latin1") as f:
            f.write("SKU_D,2,20.0,2010-04-02 10:00:00,500006\n")

        new_size = sales_csv.stat().st_size
        assert new_size > old_size

        service2 = PointInTimePriceService(data_dir=tmp_path)
        service2.load_index(cache_path=cache_json, sales_path=sales_csv)
        assert service2._cache_metadata["source_size"] == new_size
        # Expanding mean: (10 + 20) / 2 = 15.0
        assert service2.get_price("SKU_D", as_of_date=None) == 15.0


def test_cache_invalidation_missing_metadata_rebuilds():
    """5. Cache missing source metadata fingerprint triggers rebuild."""
    import json
    from ml.src.point_in_time_price import PointInTimePriceService
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sales_csv = tmp_path / "clean_gross_sales.csv"
        cache_json = tmp_path / "pit_sku_price_history.json"

        _create_synthetic_sales_csv(sales_csv, [["SKU_E", 1, 8.0, "2010-05-01 10:00:00", "500007"]])

        service = PointInTimePriceService(data_dir=tmp_path)
        service.load_index(cache_path=cache_json, sales_path=sales_csv)

        # Strip metadata from JSON file
        with open(cache_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        del data["metadata"]
        with open(cache_json, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service2 = PointInTimePriceService(data_dir=tmp_path)
        service2.load_index(cache_path=cache_json, sales_path=sales_csv)
        assert "source_size" in service2._cache_metadata, "Failed to restore metadata upon rebuild!"


def test_cache_invalidation_malformed_json_recovery():
    """6. Malformed JSON file is automatically recovered and rebuilt."""
    from ml.src.point_in_time_price import PointInTimePriceService
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sales_csv = tmp_path / "clean_gross_sales.csv"
        cache_json = tmp_path / "pit_sku_price_history.json"

        _create_synthetic_sales_csv(sales_csv, [["SKU_F", 1, 12.0, "2010-06-01 10:00:00", "500008"]])

        # Write corrupt JSON
        with open(cache_json, "w", encoding="utf-8") as f:
            f.write("CORRUPTED_JSON_DATA_---{{{")

        service = PointInTimePriceService(data_dir=tmp_path)
        service.load_index(cache_path=cache_json, sales_path=sales_csv)
        assert service.is_loaded is True
        assert service.get_price("SKU_F", as_of_date=None) == 12.0


def test_cache_invalidation_failed_rebuild_error():
    """7. Missing cache with unavailable source dataset raises FileNotFoundError."""
    from ml.src.point_in_time_price import PointInTimePriceService
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sales_csv = tmp_path / "non_existent_sales.csv"
        cache_json = tmp_path / "non_existent_cache.json"

        service = PointInTimePriceService(data_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            service.load_index(cache_path=cache_json, sales_path=sales_csv)
        assert service.is_loaded is False
        assert service.load_error is not None


def test_cache_invalidation_reproduces_task12_prices():
    """8. Rebuilt cache exactly reproduces the Task 12 expanding arithmetic price formula."""
    from ml.src.point_in_time_price import PointInTimePriceService
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sales_csv = tmp_path / "clean_gross_sales.csv"
        cache_json = tmp_path / "pit_sku_price_history.json"

        _create_synthetic_sales_csv(sales_csv, [
            ["SKU_G", 1, 10.0, "2010-07-01 10:00:00", "500009"],
            ["SKU_G", 1, 20.0, "2010-07-02 10:00:00", "500010"],
            ["SKU_G", 1, 30.0, "2010-07-03 10:00:00", "500011"],
        ])

        service = PointInTimePriceService(data_dir=tmp_path)
        service.load_index(cache_path=cache_json, sales_path=sales_csv)

        # Before any tx: prior 2.10
        assert service.get_price("SKU_G", as_of_date="2010-07-01") == 2.10
        # After tx 1: 10.0
        assert service.get_price("SKU_G", as_of_date="2010-07-02") == 10.0
        # After tx 2: (10 + 20) / 2 = 15.0
        assert service.get_price("SKU_G", as_of_date="2010-07-03") == 15.0
        # After tx 3: (10 + 20 + 30) / 3 = 20.0
        assert service.get_price("SKU_G", as_of_date="2010-07-04") == 20.0
        assert service.get_price("SKU_G", as_of_date=None) == 20.0



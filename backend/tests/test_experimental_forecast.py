"""Unit tests for experimental forecasting endpoints and comparative evaluations."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


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


def test_sku_predict_backward_compatibility(client):
    """Verifies that existing /api/v1/forecast/predict endpoint remains 100% functional."""
    payload = {"stock_code": "85123A"}
    response = client.post("/api/v1/forecast/predict", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["stock_code"] == "85123A"
    assert "predictions" in data
    assert set(data["predictions"].keys()) == {"7", "15", "30", "90"}
    for h in ["7", "15", "30", "90"]:
        assert data["predictions"][h] > 0

"""Test suite for inventory replenishment recommendations and decision support.

Covers:
1. Low stock replenishment (positive purchase recommendation, CRITICAL / ELEVATED risk).
2. Sufficient stock replenishment (zero purchase recommendation, SAFE).
3. Zero on-hand stock replenishment (purchase quantity equals target stock).
4. Lead time variation impact (longer lead time increases coverage window and purchase quantity).
5. Input validation (negative current stock, invalid lead times, missing fields).
6. Catalog error handling (unknown SKU 404, insufficient history SKU 422).
7. Mathematical invariant properties:
   - Purchase quantity is strictly non-negative.
   - Purchase quantity monotonically decreases with current stock.
   - Demand coverage reconciles with multi-horizon forecast endpoints.
8. Support for Task 12 experimental models.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.inventory_service import inventory_service
from app.services.historical_data_service import historical_data_service
from app.services.prediction_service import prediction_service
from app.services.experimental_prediction_service import experimental_prediction_service


@pytest.fixture(scope="module")
def client():
    """TestClient fixture with application lifespan context."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module", autouse=True)
def ensure_all_services_loaded():
    """Ensure all forecasting and dataset services are loaded in memory."""
    historical_data_service.ensure_loaded()
    prediction_service.ensure_loaded()
    experimental_prediction_service.ensure_loaded()


# =====================================================================
# SECTION 1: Operational Scenarios
# =====================================================================

def test_01_low_stock_positive_purchase_recommendation(client):
    """Test 1: Low current stock produces positive purchase recommendation and risk alert."""
    payload = {
        "stock_code": "85123A",
        "current_stock": 50.0,
        "lead_time_days": 7,
        "review_period_days": 7,
        "safety_stock_days": 3.0
    }
    resp = client.post("/api/v1/inventory/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["stock_code"] == "85123A"
    assert data["current_stock"] == 50.0
    assert data["lead_time_days"] == 7
    assert data["review_period_days"] == 7
    assert data["coverage_period_days"] == 14
    assert data["forecast_demand"] > 0.0
    assert data["safety_stock"] > 0.0
    assert data["target_stock"] > data["forecast_demand"]
    assert data["recommended_purchase_quantity"] > 0.0
    assert data["stock_condition"] in ["CRITICAL", "ELEVATED"]
    assert "Purchase" in data["recommendation"]
    assert "Coverage window of 14 days" in data["calculation_explanation"]


def test_02_sufficient_stock_zero_purchase_recommendation(client):
    """Test 2: High current stock produces zero purchase quantity and SAFE classification."""
    payload = {
        "stock_code": "85123A",
        "current_stock": 50000.0,
        "lead_time_days": 7,
        "review_period_days": 7,
        "safety_stock_days": 3.0
    }
    resp = client.post("/api/v1/inventory/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["recommended_purchase_quantity"] == 0.0
    assert data["stock_condition"] == "SAFE"
    assert "adequately covers" in data["recommendation"] or "No reorder" in data["recommendation"]


def test_03_zero_stock_covers_target_stock(client):
    """Test 3: Zero on-hand stock requires purchasing the full target stock."""
    payload = {
        "stock_code": "85123A",
        "current_stock": 0.0,
        "lead_time_days": 7,
        "review_period_days": 7,
        "safety_stock_days": 3.0
    }
    resp = client.post("/api/v1/inventory/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["current_stock"] == 0.0
    assert data["recommended_purchase_quantity"] == data["target_stock"]
    assert data["stock_condition"] == "CRITICAL"


def test_04_lead_time_increase_increases_purchase_recommendation(client):
    """Test 4: Longer supplier lead time increases coverage window, target stock, and purchase quantity."""
    base_payload = {
        "stock_code": "85123A",
        "current_stock": 200.0,
        "lead_time_days": 7,
        "review_period_days": 7,
        "safety_stock_days": 3.0
    }
    resp_7 = client.post("/api/v1/inventory/recommend", json=base_payload)
    assert resp_7.status_code == 200
    data_7 = resp_7.json()

    long_payload = dict(base_payload)
    long_payload["lead_time_days"] = 14
    resp_14 = client.post("/api/v1/inventory/recommend", json=long_payload)
    assert resp_14.status_code == 200
    data_14 = resp_14.json()

    assert data_14["coverage_period_days"] == 21  # 14 + 7
    assert data_14["coverage_period_days"] > data_7["coverage_period_days"]
    assert data_14["forecast_demand"] > data_7["forecast_demand"]
    assert data_14["target_stock"] > data_7["target_stock"]
    assert data_14["recommended_purchase_quantity"] > data_7["recommended_purchase_quantity"]


# =====================================================================
# SECTION 2: Error Handling & Validation
# =====================================================================

def test_05_invalid_negative_stock_rejected_with_422(client):
    """Test 5: Negative current stock fails Pydantic schema validation with HTTP 422."""
    payload = {
        "stock_code": "85123A",
        "current_stock": -25.0,
        "lead_time_days": 7,
        "review_period_days": 7
    }
    resp = client.post("/api/v1/inventory/recommend", json=payload)
    assert resp.status_code == 422


def test_06_unknown_sku_returns_404(client):
    """Test 6: Querying an unknown SKU returns HTTP 404 Not Found."""
    payload = {
        "stock_code": "NON_EXISTENT_SKU_99999",
        "current_stock": 100.0
    }
    resp = client.post("/api/v1/inventory/recommend", json=payload)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_07_insufficient_history_returns_422(client):
    """Test 7: SKU with fewer than 29 days of history returns HTTP 422."""
    payload = {
        "stock_code": "20877",  # Known 9-day SKU
        "current_stock": 100.0
    }
    resp = client.post("/api/v1/inventory/recommend", json=payload)
    assert resp.status_code == 422
    assert "insufficient historical sales data" in resp.json()["detail"].lower()


def test_08_missing_required_fields_rejected_with_422(client):
    """Test 8: Missing stock_code or current_stock returns HTTP 422."""
    resp1 = client.post("/api/v1/inventory/recommend", json={"current_stock": 10.0})
    assert resp1.status_code == 422

    resp2 = client.post("/api/v1/inventory/recommend", json={"stock_code": "85123A"})
    assert resp2.status_code == 422


def test_09_invalid_lead_or_review_period_rejected(client):
    """Test 9: Non-positive lead_time_days or review_period_days returns HTTP 422."""
    payload_bad_lead = {
        "stock_code": "85123A",
        "current_stock": 10.0,
        "lead_time_days": 0
    }
    assert client.post("/api/v1/inventory/recommend", json=payload_bad_lead).status_code == 422

    payload_bad_review = {
        "stock_code": "85123A",
        "current_stock": 10.0,
        "review_period_days": -5
    }
    assert client.post("/api/v1/inventory/recommend", json=payload_bad_review).status_code == 422


# =====================================================================
# SECTION 3: Mathematical Invariant Properties
# =====================================================================

def test_10_purchase_quantity_non_negativity_invariance(client):
    """Test 10: Recommended purchase quantity is strictly non-negative across all stock values."""
    for stock_val in [0.0, 10.0, 100.0, 500.0, 1000.0, 5000.0, 100000.0]:
        payload = {
            "stock_code": "85123A",
            "current_stock": stock_val,
            "lead_time_days": 7,
            "review_period_days": 7,
            "safety_stock_days": 3.0
        }
        resp = client.post("/api/v1/inventory/recommend", json=payload)
        assert resp.status_code == 200
        qty = resp.json()["recommended_purchase_quantity"]
        assert qty >= 0.0


def test_11_current_stock_monotonicity(client):
    """Test 11: Increasing current stock cannot increase recommended purchase quantity."""
    stock_levels = [0.0, 50.0, 200.0, 500.0, 1000.0, 2500.0, 10000.0]
    purchases = []

    for s in stock_levels:
        payload = {
            "stock_code": "85123A",
            "current_stock": s,
            "lead_time_days": 7,
            "review_period_days": 7
        }
        resp = client.post("/api/v1/inventory/recommend", json=payload)
        purchases.append(resp.json()["recommended_purchase_quantity"])

    # Verify monotonically non-increasing
    for i in range(len(purchases) - 1):
        assert purchases[i] >= purchases[i + 1], f"Monotonicity violated: {purchases[i]} < {purchases[i+1]}"


def test_12_forecast_reconciliation_exact_horizon(client):
    """Test 12: When coverage period equals exactly 7 days, demand matches 7-day model forecast."""
    # 1. Query forecast endpoint for 7-day horizon
    fc_resp = client.post("/api/v1/forecast/predict", json={"stock_code": "85123A", "horizons": [7]})
    assert fc_resp.status_code == 200
    expected_d7 = fc_resp.json()["predictions"]["7"]

    # 2. Query inventory recommendation with lead_time=4, review_period=3 (sum = 7 days)
    inv_resp = client.post("/api/v1/inventory/recommend", json={
        "stock_code": "85123A",
        "current_stock": 100.0,
        "lead_time_days": 4,
        "review_period_days": 3,
        "safety_stock_days": 0.0
    })
    assert inv_resp.status_code == 200
    inv_data = inv_resp.json()

    assert inv_data["coverage_period_days"] == 7
    assert abs(inv_data["forecast_demand"] - round(expected_d7, 2)) < 0.05


def test_13_task12_experimental_model_support(client):
    """Test 13: Verifies integration with Task 12 experimental models when use_experimental=True."""
    payload = {
        "stock_code": "85123A",
        "current_stock": 100.0,
        "lead_time_days": 7,
        "review_period_days": 7,
        "safety_stock_days": 3.0,
        "use_experimental": True
    }
    resp = client.post("/api/v1/inventory/recommend", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "Task 12 Experimental" in data["model_used"]
    assert data["forecast_demand"] > 0.0
    assert data["recommended_purchase_quantity"] >= 0.0

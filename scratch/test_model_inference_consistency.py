import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

import json
from fastapi.testclient import TestClient
from app.main import app
from app.services.experimental_prediction_service import experimental_prediction_service

print("=== TASK D: EXPERIMENTAL MODEL CONSISTENCY & INFERENCE AUDIT ===")

with TestClient(app) as client:
    # 1. Test Valid SKU 85123A (High volume)
    r_85123a = client.post("/api/v1/experimental/forecast/predict", json={"stock_code": "85123A"})
    print(f"\nSKU 85123A (Valid high-volume): HTTP {r_85123a.status_code}")
    assert r_85123a.status_code == 200
    p_85123a = r_85123a.json()
    print("  Unit Price resolved:", p_85123a.get("unit_price"))
    print("  Predictions:", p_85123a.get("predictions"))
    for h, pred in p_85123a.get("predictions", {}).items():
        print(f"  Horizon {h}: predicted_demand={pred}")
        assert pred >= 0.0

    # 2. Test Valid SKU 21777 (Medium volume, 371 days of history)
    r_21777 = client.post("/api/v1/experimental/forecast/predict", json={"stock_code": "21777"})
    print(f"\nSKU 21777 (Valid medium-volume): HTTP {r_21777.status_code}")
    assert r_21777.status_code == 200
    p_21777 = r_21777.json()
    print("  Unit Price resolved:", p_21777.get("unit_price"))
    print("  Predictions:", p_21777.get("predictions"))
    for h, pred in p_21777.get("predictions", {}).items():
        print(f"  Horizon {h}: predicted_demand={pred}")
        assert pred >= 0.0

    # 3. Test Additional Commercial SKU 22423 (Sufficient history)
    r_22423 = client.post("/api/v1/experimental/forecast/predict", json={"stock_code": "22423"})
    print(f"\nSKU 22423 (Valid high-volume): HTTP {r_22423.status_code}")
    assert r_22423.status_code == 200
    p_22423 = r_22423.json()
    print("  Unit Price resolved:", p_22423.get("unit_price"))
    print("  Predictions:", p_22423.get("predictions"))
    for h, pred in p_22423.get("predictions", {}).items():
        print(f"  Horizon {h}: predicted_demand={pred}")
        assert pred >= 0.0

    # 4. Test Additional Commercial SKU 84879 (Sufficient history)
    r_84879 = client.post("/api/v1/experimental/forecast/predict", json={"stock_code": "84879"})
    print(f"\nSKU 84879 (Valid): HTTP {r_84879.status_code}")
    assert r_84879.status_code == 200
    p_84879 = r_84879.json()
    print("  Unit Price resolved:", p_84879.get("unit_price"))
    print("  Predictions:", p_84879.get("predictions"))
    for h, pred in p_84879.get("predictions", {}).items():
        print(f"  Horizon {h}: predicted_demand={pred}")
        assert pred >= 0.0

    # 5. Test Insufficient History SKU 20877 (Expected HTTP 422)
    r_20877 = client.post("/api/v1/experimental/forecast/predict", json={"stock_code": "20877"})
    print(f"\nSKU 20877 (Insufficient history): HTTP {r_20877.status_code}")
    print("  Detail:", r_20877.json().get("detail"))
    assert r_20877.status_code == 422
    assert "Insufficient historical sales data" in r_20877.json().get("detail", "")

    # 6. Test Non-existent / Unknown SKU
    r_unknown = client.post("/api/v1/experimental/forecast/predict", json={"stock_code": "TOTALLY_NONEXISTENT_SKU_XYZ"})
    print(f"\nUnknown SKU (Non-existent): HTTP {r_unknown.status_code}")
    assert r_unknown.status_code == 404

print("\nTask D: ALL INFERENCE BEHAVIORS 100% VERIFIED!")

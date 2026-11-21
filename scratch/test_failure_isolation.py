import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

import json
from fastapi.testclient import TestClient
from app.main import app

print("=== VERIFYING FAILURE ISOLATION ===")
with TestClient(app) as client:
    # 1. Normal state: both ready
    r_prod = client.get("/ready")
    r_exp = client.get("/api/v1/experimental/ready")
    print("Normal State:")
    print("  /ready status:", r_prod.status_code, r_prod.json().get("status"))
    print("  /api/v1/experimental/ready status:", r_exp.status_code, r_exp.json().get("status"))
    assert r_prod.status_code == 200
    assert r_exp.status_code == 200

    # 2. Simulate experimental price service down
    from ml.src.point_in_time_price import pit_price_service
    orig_loaded = pit_price_service.is_loaded
    try:
        pit_price_service.is_loaded = False
        pit_price_service.load_error = "Simulated PIT price service database outage"

        # Check production readiness
        r_prod_isolated = client.get("/ready")
        print("\nExperimental Outage State:")
        print("  /ready status:", r_prod_isolated.status_code, r_prod_isolated.json().get("status"))
        # Production must remain 200!
        assert r_prod_isolated.status_code == 200, "Production must not fail when experimental is down!"

        # Experimental readiness must return 503
        r_exp_degraded = client.get("/api/v1/experimental/ready")
        print("  /api/v1/experimental/ready status:", r_exp_degraded.status_code, r_exp_degraded.json().get("status"))
        assert r_exp_degraded.status_code == 503, "Experimental must report 503 when degraded!"
        
        # Production predict must remain operational
        r_prod_predict = client.post("/api/v1/forecast/predict", json={"stock_code": "85123A"})
        print("  /api/v1/forecast/predict status:", r_prod_predict.status_code)
        assert r_prod_predict.status_code == 200, "Production predict must work even if PIT is down!"

    finally:
        pit_price_service.is_loaded = orig_loaded
        pit_price_service.load_error = None

print("\nFailure Isolation: 100% VERIFIED!")

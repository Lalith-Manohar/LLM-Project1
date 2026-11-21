import json
import urllib.request
import urllib.error
import ssl
import sys
import os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

LOCAL_BASE = "http://127.0.0.1:8000"
PUBLIC_BASE = "https://antonym-headband-harpist.ngrok-free.dev"
NGROK_HEADERS = {"ngrok-skip-browser-warning": "69420", "User-Agent": "Task31-Audit/1.0"}

def req(url, method="GET", payload=None, headers=None):
    if headers is None:
        headers = {}
    h = dict(headers)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, context=ctx, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = body
            return {"status": resp.status, "data": parsed, "raw": body}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return {"status": e.code, "data": parsed, "raw": body, "error": True}
    except Exception as e:
        return {"status": 0, "error_msg": str(e)}

def audit_all():
    report = {}

    print(">>> 1. AUDITING RUNNING DEPLOYMENT ENDPOINTS (LOCAL & PUBLIC) <<<")
    endpoints_s4 = [
        ("health", "/health", "GET", None),
        ("ready", "/ready", "GET", None),
        ("docs", "/docs", "GET", None),
        ("openapi", "/openapi.json", "GET", None),
        ("horizons", "/api/v1/forecast/horizons", "GET", None),
        ("model_metrics", "/api/v1/forecast/model-metrics", "GET", None),
    ]

    report["section4_deployment"] = {}
    for name, path, method, payload in endpoints_s4:
        loc = req(LOCAL_BASE + path, method, payload)
        pub = req(PUBLIC_BASE + path, method, payload, NGROK_HEADERS)
        report["section4_deployment"][name] = {
            "local_status": loc["status"],
            "public_status": pub["status"],
            "local_summary": loc["data"] if name in ["health", "ready", "horizons"] else "OK",
            "public_summary": pub["data"] if name in ["health", "ready", "horizons"] else "OK"
        }
        print(f"[{name}] Local: {loc['status']} | Public: {pub['status']}")

    # Check openapi schema paths
    loc_open = req(LOCAL_BASE + "/openapi.json")
    if loc_open["status"] == 200 and isinstance(loc_open["data"], dict):
        paths = loc_open["data"].get("paths", {})
        has_predict = "/api/v1/forecast/predict" in paths
        has_recommend = "/api/v1/inventory/recommend" in paths
        report["section4_deployment"]["openapi_check"] = {
            "total_paths": len(paths),
            "has_predict": has_predict,
            "has_recommend": has_recommend,
            "paths_list": sorted(list(paths.keys()))
        }
        print(f"OpenAPI paths: {len(paths)} | has_predict: {has_predict} | has_recommend: {has_recommend}")

    print("\n>>> 2. AUDITING FORECASTING API ENDPOINTS (SECTION 5) <<<")
    forecast_cases = [
        ("F01_sku85123A_h7", {"stock_code": "85123A", "horizon_days": 7}),
        ("F02_sku85123A_h30", {"stock_code": "85123A", "horizon_days": 30}),
        ("F03_sku22423_h7", {"stock_code": "22423", "horizon_days": 7}),
        ("F04_unknown_sku", {"stock_code": "NON_EXISTENT_SKU_99999", "horizon_days": 7}),
        ("F05_insufficient_history", {"stock_code": "20877", "horizon_days": 7}),
        ("F06_invalid_horizon_999", {"stock_code": "85123A", "horizon_days": 999}),
        ("F07_missing_stock_code", {"horizon_days": 7}),
        ("F08_invalid_request_data", {"stock_code": 12345, "horizon_days": "invalid"}),
    ]

    report["section5_forecast"] = {}
    for cid, payload in forecast_cases:
        loc = req(LOCAL_BASE + "/api/v1/forecast/predict", "POST", payload)
        pub = req(PUBLIC_BASE + "/api/v1/forecast/predict", "POST", payload, NGROK_HEADERS)
        report["section5_forecast"][cid] = {
            "payload": payload,
            "local_status": loc["status"],
            "public_status": pub["status"],
            "local_response": loc["data"],
            "public_response": pub["data"]
        }
        print(f"[{cid}] Local: {loc['status']} | Public: {pub['status']}")

    print("\n>>> 3. AUDITING INVENTORY API ENDPOINTS (SECTION 6) <<<")
    inventory_cases = [
        ("I01_sku85123A_stock100", {
            "stock_code": "85123A", "current_stock": 100.0,
            "lead_time_days": 7, "review_period_days": 7, "safety_stock_days": 3.0
        }),
        ("I02_sku85123A_high_stock", {
            "stock_code": "85123A", "current_stock": 50000.0,
            "lead_time_days": 7, "review_period_days": 7, "safety_stock_days": 3.0
        }),
        ("I03_sku85123A_zero_stock", {
            "stock_code": "85123A", "current_stock": 0.0,
            "lead_time_days": 7, "review_period_days": 7, "safety_stock_days": 3.0
        }),
        ("I04_sku85123A_longer_lead", {
            "stock_code": "85123A", "current_stock": 100.0,
            "lead_time_days": 14, "review_period_days": 7, "safety_stock_days": 3.0
        }),
        ("I05_negative_current_stock", {
            "stock_code": "85123A", "current_stock": -10.0,
            "lead_time_days": 7, "review_period_days": 7, "safety_stock_days": 3.0
        }),
        ("I06_unknown_sku", {
            "stock_code": "NON_EXISTENT_SKU_99999", "current_stock": 100.0,
            "lead_time_days": 7, "review_period_days": 7, "safety_stock_days": 3.0
        }),
        ("I07_insufficient_history", {
            "stock_code": "20877", "current_stock": 100.0,
            "lead_time_days": 7, "review_period_days": 7, "safety_stock_days": 3.0
        }),
    ]

    report["section6_inventory"] = {}
    for cid, payload in inventory_cases:
        loc = req(LOCAL_BASE + "/api/v1/inventory/recommend", "POST", payload)
        pub = req(PUBLIC_BASE + "/api/v1/inventory/recommend", "POST", payload, NGROK_HEADERS)
        report["section6_inventory"][cid] = {
            "payload": payload,
            "local_status": loc["status"],
            "public_status": pub["status"],
            "local_response": loc["data"],
            "public_response": pub["data"]
        }
        print(f"[{cid}] Local: {loc['status']} | Public: {pub['status']}")

    # Check multi-horizon forecast monotonicity for SKU 85123A
    print("\n>>> Checking Forecast Monotonicity across horizons [7, 15, 30, 90] for 85123A <<<")
    multi_fc = req(LOCAL_BASE + "/api/v1/forecast/predict", "POST", {
        "stock_code": "85123A", "horizons": [7, 15, 30, 90]
    })
    report["section6_inventory"]["multi_horizon_forecast_85123A"] = multi_fc["data"]
    if multi_fc["status"] == 200:
        preds = multi_fc["data"].get("predictions", {})
        print("Predictions for 85123A:", preds)

    with open("scratch/task31_audit_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("\nWrote results to scratch/task31_audit_results.json")

if __name__ == "__main__":
    audit_all()

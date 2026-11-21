import urllib.request
import urllib.error
import json
import ssl
import sys

def test_endpoint(name, url, method="GET", payload=None, headers=None, skip_ssl=False):
    print(f"\n==================================================")
    print(f"Testing {name}: {method} {url}")
    print(f"==================================================")
    if headers is None:
        headers = {}
    
    data_bytes = None
    if payload is not None:
        data_bytes = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    ctx = None
    if skip_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            status = resp.status
            body_bytes = resp.read()
            body_str = body_bytes.decode("utf-8", errors="replace")
            print(f"STATUS: {status}")
            try:
                parsed = json.loads(body_str)
                print(f"RESPONSE JSON:\n{json.dumps(parsed, indent=2)}")
                return {"status": status, "json": parsed, "body": body_str}
            except Exception:
                print(f"RESPONSE TEXT (first 500 chars):\n{body_str[:500]}")
                return {"status": status, "body": body_str}
    except urllib.error.HTTPError as e:
        status = e.code
        body_bytes = e.read()
        body_str = body_bytes.decode("utf-8", errors="replace")
        print(f"HTTP ERROR STATUS: {status}")
        try:
            parsed = json.loads(body_str)
            print(f"ERROR JSON:\n{json.dumps(parsed, indent=2)}")
            return {"status": status, "json": parsed, "body": body_str}
        except Exception:
            print(f"ERROR TEXT:\n{body_str[:500]}")
            return {"status": status, "body": body_str}
    except Exception as e:
        print(f"EXCEPTION: {type(e).__name__}: {e}")
        return {"error": str(e)}

def main():
    results = {}
    
    # ----------------- LOCAL (Step 3) -----------------
    print("\n>>> STEP 3: TESTING LOCAL ENDPOINTS (http://127.0.0.1:8000) <<<")
    results["local_health"] = test_endpoint("Local /health", "http://127.0.0.1:8000/health")
    results["local_ready"] = test_endpoint("Local /ready", "http://127.0.0.1:8000/ready")
    
    openapi_res = test_endpoint("Local /openapi.json", "http://127.0.0.1:8000/openapi.json")
    results["local_openapi"] = openapi_res
    if "json" in openapi_res:
        paths = list(openapi_res["json"].get("paths", {}).keys())
        print(f"\n--- OpenAPI Analysis ---")
        print(f"Total paths count: {len(paths)}")
        print(f"Paths list:\n" + "\n".join(f"  - {p}" for p in sorted(paths)))
        print(f"Is '/api/v1/inventory/recommend' in paths? {'/api/v1/inventory/recommend' in paths}")
    
    forecast_payload = {"stock_code": "85123A", "horizon_days": 7}
    results["local_forecast"] = test_endpoint(
        "Local /api/v1/forecast/predict",
        "http://127.0.0.1:8000/api/v1/forecast/predict",
        method="POST",
        payload=forecast_payload
    )

    inv_payload = {
        "stock_code": "85123A",
        "current_stock": 100,
        "lead_time_days": 7,
        "review_period_days": 7,
        "safety_stock_days": 3
    }
    results["local_inventory"] = test_endpoint(
        "Local /api/v1/inventory/recommend",
        "http://127.0.0.1:8000/api/v1/inventory/recommend",
        method="POST",
        payload=inv_payload
    )

    # ----------------- PUBLIC NGROK (Step 4) -----------------
    print("\n>>> STEP 4: TESTING PUBLIC NGROK ENDPOINTS <<<")
    pub_base = "https://antonym-headband-harpist.ngrok-free.dev"
    pub_headers = {
        "ngrok-skip-browser-warning": "69420",
        "User-Agent": "NEXORA-Audit/1.0"
    }
    
    results["public_health"] = test_endpoint(
        "Public /health",
        f"{pub_base}/health",
        headers=pub_headers,
        skip_ssl=True
    )
    results["public_ready"] = test_endpoint(
        "Public /ready",
        f"{pub_base}/ready",
        headers=pub_headers,
        skip_ssl=True
    )
    results["public_forecast"] = test_endpoint(
        "Public /api/v1/forecast/predict",
        f"{pub_base}/api/v1/forecast/predict",
        method="POST",
        payload=forecast_payload,
        headers=pub_headers,
        skip_ssl=True
    )
    results["public_inventory"] = test_endpoint(
        "Public /api/v1/inventory/recommend",
        f"{pub_base}/api/v1/inventory/recommend",
        method="POST",
        payload=inv_payload,
        headers=pub_headers,
        skip_ssl=True
    )

    with open("scratch/task30c_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nWrote all results to scratch/task30c_test_results.json")

if __name__ == "__main__":
    main()

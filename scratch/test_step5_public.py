import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = "https://antonym-headband-harpist.ngrok-free.dev"

# 1. /health
req1 = urllib.request.Request(
    f"{base}/health",
    headers={"ngrok-skip-browser-warning": "69420", "User-Agent": "Mozilla/5.0"}
)
with urllib.request.urlopen(req1, context=ctx, timeout=10) as r1:
    print(f"Public /health -> Status: {r1.status}")
    print("  Body:", r1.read().decode())

# 2. /ready
req2 = urllib.request.Request(
    f"{base}/ready",
    headers={"ngrok-skip-browser-warning": "69420", "User-Agent": "Mozilla/5.0"}
)
with urllib.request.urlopen(req2, context=ctx, timeout=10) as r2:
    data2 = json.loads(r2.read().decode())
    print(f"Public /ready -> Status: {r2.status}")
    print("  Status:", data2.get("status"), "| Models:", data2.get("models", {}).get("ready"), "| Data:", data2.get("historical_data", {}).get("ready"))

# 3. POST /api/v1/forecast/predict
payload = {"stock_code": "85123A", "horizon_days": 7}
req3 = urllib.request.Request(
    f"{base}/api/v1/forecast/predict",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "69420",
        "User-Agent": "Mozilla/5.0"
    }
)
with urllib.request.urlopen(req3, context=ctx, timeout=10) as r3:
    data3 = json.loads(r3.read().decode())
    print(f"Public /api/v1/forecast/predict -> Status: {r3.status}")
    print("  Predictions:", data3.get("predictions"))
    print("  Model version:", data3.get("model_version"))

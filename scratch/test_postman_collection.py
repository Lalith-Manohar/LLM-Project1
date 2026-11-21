import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

from fastapi.testclient import TestClient
from app.main import app

collection_path = Path("docs/postman/NEXORA_Experimental_API.postman_collection.json")
with open(collection_path, "r", encoding="utf-8") as f:
    col = json.load(f)

print(f"=== TESTING POSTMAN COLLECTION: {col['info']['name']} ===")

with TestClient(app) as client:
    items = col["item"]
    passed = 0
    failed = 0

    for idx, item in enumerate(items):
        name = item["name"]
        req = item["request"]
        method = req["method"]
        url_path = "/" + "/".join(req["url"]["path"])
        
        headers = {h["key"]: h["value"] for h in req.get("header", [])}
        body = None
        if "body" in req and req["body"].get("raw"):
            try:
                body = json.loads(req["body"]["raw"])
            except Exception:
                body = req["body"]["raw"]

        if method == "GET":
            resp = client.get(url_path, headers=headers)
        elif method == "POST":
            resp = client.post(url_path, json=body, headers=headers)
        elif method == "OPTIONS":
            resp = client.options(url_path, headers=headers)
        else:
            resp = client.request(method, url_path, headers=headers)

        test_ok = True
        test_msgs = []
        for ev in item.get("event", []):
            if ev.get("listen") == "test":
                script_lines = ev["script"]["exec"]
                for l in script_lines:
                    if "status(200)" in l and resp.status_code != 200:
                        test_ok = False
                        test_msgs.append(f"Expected status 200, got {resp.status_code}")
                    if "status(422)" in l and resp.status_code != 422:
                        test_ok = False
                        test_msgs.append(f"Expected status 422, got {resp.status_code}")
                    if "include(\"Insufficient historical sales data\")" in l:
                        detail = resp.json().get("detail", "")
                        if "Insufficient historical sales data" not in detail:
                            test_ok = False
                            test_msgs.append("Missing 'Insufficient historical sales data' in detail")

        if test_ok:
            passed += 1
            print(f"[{idx+1}/12] PASS: {name} -> HTTP {resp.status_code}")
        else:
            failed += 1
            print(f"[{idx+1}/12] FAIL: {name} -> HTTP {resp.status_code} | {test_msgs}")

    print(f"\nRESULTS: {passed} PASSED, {failed} FAILED out of {len(items)} requests.")
    if failed > 0:
        sys.exit(1)

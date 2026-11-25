import sys
import json
import re
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

from fastapi.testclient import TestClient
from app.main import app

collection_path = Path("docs/postman/NEXORA_Complete_Demonstration.postman_collection.json")
with open(collection_path, "r", encoding="utf-8") as f:
    col = json.load(f)

# Build variables map
variables = {v["key"]: v["value"] for v in col.get("variable", [])}

def resolve_vars(text: str) -> str:
    if not isinstance(text, str):
        return text
    for k, v in variables.items():
        text = text.replace(f"{{{{{k}}}}}", str(v))
    return text

print(f"=== TESTING POSTMAN COLLECTION: {col['info']['name']} ===")

# Flatten items
flat_items = []
for item in col["item"]:
    if "item" in item:  # folder
        for sub in item["item"]:
            flat_items.append((f"[{item['name']}] {sub['name']}", sub))
    else:
        flat_items.append((item["name"], item))

print(f"Total requests to execute: {len(flat_items)}")

passed = 0
failed = 0
results_summary = []

with TestClient(app) as client:
    for idx, (display_name, item) in enumerate(flat_items):
        req = item["request"]
        method = req["method"]
        
        # Resolve URL path
        raw_url = req["url"]["raw"]
        resolved_url = resolve_vars(raw_url)
        # Strip baseUrl if present
        url_path = resolved_url.replace(variables.get("baseUrl", "http://127.0.0.1:8000"), "")
        if not url_path.startswith("/"):
            url_path = "/" + url_path

        headers = {h["key"]: resolve_vars(h["value"]) for h in req.get("header", [])}
        
        body = None
        if "body" in req and req["body"].get("raw"):
            raw_body_text = resolve_vars(req["body"]["raw"])
            try:
                body = json.loads(raw_body_text)
            except Exception:
                body = raw_body_text

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
                        test_msgs.append(f"Expected 200, got {resp.status_code}")
                    if "status(404)" in l and resp.status_code != 404:
                        test_ok = False
                        test_msgs.append(f"Expected 404, got {resp.status_code}")
                    if "status(422)" in l and resp.status_code != 422:
                        test_ok = False
                        test_msgs.append(f"Expected 422, got {resp.status_code}")
                    if "include('not found')" in l and "not found" not in resp.text.lower():
                        test_ok = False
                        test_msgs.append("Missing 'not found' in detail")
                    if "Insufficient historical sales data" in l and "Insufficient historical sales data" not in resp.text:
                        test_ok = False
                        test_msgs.append("Missing 'Insufficient historical sales data' in detail")

        status_str = "PASS" if test_ok else "FAIL"
        if test_ok:
            passed += 1
            print(f"[{idx+1:02d}/19] PASS: {display_name} -> HTTP {resp.status_code}")
        else:
            failed += 1
            print(f"[{idx+1:02d}/19] FAIL: {display_name} -> HTTP {resp.status_code} | {test_msgs}")

        results_summary.append({
            "index": idx + 1,
            "name": display_name,
            "method": method,
            "path": url_path,
            "status_code": resp.status_code,
            "result": status_str,
            "response_sample": resp.json() if resp.headers.get("content-type") == "application/json" else resp.text[:100]
        })

print(f"\n========================================================")
print(f"RESULTS: {passed} PASSED, {failed} FAILED out of {len(flat_items)} requests.")
print(f"========================================================")

if failed > 0:
    sys.exit(1)

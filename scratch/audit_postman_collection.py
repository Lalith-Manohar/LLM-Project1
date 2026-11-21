import json
import re

with open("docs/postman/NEXORA_Complete_Demonstration.postman_collection.json", "r", encoding="utf-8") as f:
    coll = json.load(f)

items = coll.get("item", [])
print(f"Total Requests in Collection: {len(items)}")

variables = {v["key"]: v["value"] for v in coll.get("variable", [])}
print(f"Collection Variables ({len(variables)}):")
for k, v in variables.items():
    print(f"  {k} = {v}")

print("\n--- REQUEST INVENTORY ---")
for idx, it in enumerate(items, 1):
    req = it["request"]
    name = it["name"]
    method = req["method"]
    url = req["url"]["raw"]
    body = req.get("body", {}).get("raw", "")
    tests = []
    for ev in it.get("event", []):
        if ev.get("listen") == "test":
            tests = ev.get("script", {}).get("exec", [])
    print(f"\n{idx}. [{method}] {name}")
    print(f"   URL: {url}")
    if body:
        print(f"   Body: {body.strip()}")
    print(f"   Test assertions ({len(tests)} lines):")
    for t in tests:
        if "pm.test" in t:
            print(f"     - {t.strip()}")

# Inspect Guide
with open("docs/postman/NEXORA_Postman_Demonstration_Guide.md", "r", encoding="utf-8") as f:
    guide_text = f.read()

print("\n=== COMPARING WITH DEMONSTRATION GUIDE ===")
print("Guide mentions 'currentStock' / '100' / '50':")
for line in guide_text.splitlines():
    if any(k in line for k in ["currentStock", "current_stock", "50000", "5000", "leadTimeDays"]):
        print("  Guide line:", line.strip())

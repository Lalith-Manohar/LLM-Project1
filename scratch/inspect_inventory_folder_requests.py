import json

with open("docs/postman/NEXORA_Complete_Demonstration.postman_collection.json", "r", encoding="utf-8") as f:
    coll = json.load(f)

folder = coll["item"][12]
print(f"Folder name: {folder['name']}")
for idx, sub in enumerate(folder["item"], 1):
    req = sub["request"]
    name = sub["name"]
    method = req["method"]
    url = req["url"]["raw"]
    body = req.get("body", {}).get("raw", "")
    tests = []
    for ev in sub.get("event", []):
        if ev.get("listen") == "test":
            tests = [l.strip() for l in ev.get("script", {}).get("exec", []) if "pm.test" in l]
    print(f"\n--- {idx}. [{method}] {name} ---")
    print(f"URL: {url}")
    print(f"Body: {body.strip()}")
    print("Tests:")
    for t in tests:
        print("  *", t)

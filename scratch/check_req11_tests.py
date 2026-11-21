import json

path = "docs/postman/NEXORA_Experimental_API.postman_collection.json"
with open(path) as f:
    data = json.load(f)

req11 = data["item"][10]
print("Name:", req11["name"])
for ev in req11.get("event", []):
    if ev.get("listen") == "test":
        print("Test script:")
        print("\n".join(ev["script"]["exec"]))

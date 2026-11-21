import json

path = "docs/postman/NEXORA_Experimental_API.postman_collection.json"
with open(path) as f:
    data = json.load(f)

for idx, item in enumerate(data["item"]):
    name = item["name"]
    print(f"Req {idx+1}: {name}")
    if idx == 10:
        print("  raw body:", item["request"]["body"].get("raw"))

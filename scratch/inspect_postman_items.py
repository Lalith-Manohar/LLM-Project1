import json

with open("docs/postman/NEXORA_Complete_Demonstration.postman_collection.json", "r", encoding="utf-8") as f:
    coll = json.load(f)

items = coll.get("item", [])
print(f"Total top-level items: {len(items)}")
for i, it in enumerate(items, 1):
    if "request" in it:
        print(f"{i}. [Request] {it.get('name')}")
    elif "item" in it:
        print(f"{i}. [Folder] {it.get('name')} (contains {len(it.get('item', []))} items)")
        for j, sub in enumerate(it.get("item", []), 1):
            print(f"     {i}.{j}. [Request] {sub.get('name')}")
    else:
        print(f"{i}. [Unknown] keys: {list(it.keys())}")

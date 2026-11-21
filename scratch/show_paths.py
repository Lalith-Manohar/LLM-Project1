import json

d = json.load(open("scratch/task30c_test_results.json", encoding="utf-8"))
paths = list(d["local_openapi"]["json"]["paths"].keys())
print("Total paths:", len(paths))
for p in sorted(paths):
    print("  -", p)

import json

d = json.load(open("scratch/task30c_test_results.json", encoding="utf-8"))

print("=== LOCAL /health ===")
print("Status:", d["local_health"]["status"])
print("Body:", d["local_health"]["json"])

print("\n=== LOCAL /ready ===")
print("Status:", d["local_ready"]["status"])
print("Overall status:", d["local_ready"]["json"]["status"])
print("Models ready:", d["local_ready"]["json"]["models"]["ready"])
print("Historical data ready:", d["local_ready"]["json"]["historical_data"]["ready"])

print("\n=== LOCAL /api/v1/forecast/predict ===")
print("Status:", d["local_forecast"]["status"])
print("JSON:", json.dumps(d["local_forecast"]["json"], indent=2))

print("\n=== LOCAL /api/v1/inventory/recommend ===")
print("Status:", d["local_inventory"]["status"])
print("JSON:", json.dumps(d["local_inventory"]["json"], indent=2))

print("\n=== PUBLIC /health ===")
print("Status:", d["public_health"]["status"])
print("Body:", d["public_health"]["json"])

print("\n=== PUBLIC /ready ===")
print("Status:", d["public_ready"]["status"])
print("Overall status:", d["public_ready"]["json"]["status"])

print("\n=== PUBLIC /api/v1/forecast/predict ===")
print("Status:", d["public_forecast"]["status"])
print("JSON:", json.dumps(d["public_forecast"]["json"], indent=2))

print("\n=== PUBLIC /api/v1/inventory/recommend ===")
print("Status:", d["public_inventory"]["status"])
print("JSON:", json.dumps(d["public_inventory"]["json"], indent=2))

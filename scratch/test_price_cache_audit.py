import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

import json
from ml.src.point_in_time_price import pit_price_service
from ml.src.preprocessing import NON_MERCHANDISE_CODES

print("=== TASK G: PRICE CACHE REGENERATION & CONSISTENCY AUDIT ===")

cache_path = Path("backend/ml/data/processed/pit_sku_price_history.json")
assert cache_path.is_file(), "Cache file missing!"

with open(cache_path, "r", encoding="utf-8") as f:
    cache_data = json.load(f)

meta = cache_data.get("metadata", {})
print(f"Cache metadata: {meta}")
assert meta.get("source_file") == "clean_gross_sales.csv"
assert meta.get("total_skus") == 4905
assert meta.get("total_transactions") == 1037089

sku_dict = cache_data.get("skus", {})
skus = list(sku_dict.keys())
print(f"Total SKUs in price cache: {len(skus)}")
assert len(skus) == 4905, f"Expected 4905 SKUs, got {len(skus)}"

# Check service codes
found_service_codes = set(skus).intersection(NON_MERCHANDISE_CODES)
print(f"Non-merchandise codes found in cache: {found_service_codes}")
assert len(found_service_codes) == 0, f"Found non-merchandise codes in cache: {found_service_codes}"

# Verify PointInTimePriceService
pit_price_service.ensure_loaded()
print(f"PIT Price Service is_loaded: {pit_price_service.is_loaded}")
print(f"PIT Price Service status: {pit_price_service.get_status()}")

# SKU 85123A tests
price_operational = pit_price_service.get_price("85123A", as_of_date=None)
print(f"SKU 85123A operational (as_of_date=None): {price_operational}")
assert price_operational == 3.0749, f"Expected 3.0749, got {price_operational}"

price_backtest = pit_price_service.get_price("85123A", as_of_date="2011-12-09")
print(f"SKU 85123A backtest (as_of_date='2011-12-09'): {price_backtest}")
assert price_backtest == 3.0744, f"Expected 3.0744, got {price_backtest}"

price_2011_01_01 = pit_price_service.get_price("85123A", as_of_date="2011-01-01")
print(f"SKU 85123A prior year (as_of_date='2011-01-01'): {price_2011_01_01}")
assert price_2011_01_01 is not None and price_2011_01_01 > 0.0

# Service code queries should fall back cleanly to global median price
for sc in NON_MERCHANDISE_CODES:
    p = pit_price_service.get_price(sc, as_of_date=None)
    print(f"Non-merchandise code {sc} fallback price resolution: {p}")
    assert p is not None and p > 0.0

print("\nTask G: PRICE CACHE REGENERATION & CONSISTENCY 100% VERIFIED!")

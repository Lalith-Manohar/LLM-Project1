import json
import pandas as pd
from pathlib import Path

print("=== TASK 25: SKU COUNT RECONCILIATION & DATASET COMPARISON ===")

# 1. Load clean_gross_sales.csv
sales_path = Path("backend/ml/data/processed/clean_gross_sales.csv")
print(f"Loading {sales_path}...")
df_sales = pd.read_csv(sales_path, encoding="latin1", low_memory=False)

# 2. Load daily_product_demand.csv
demand_path = Path("backend/ml/data/processed/daily_product_demand.csv")
print(f"Loading {demand_path}...")
df_demand = pd.read_csv(demand_path, low_memory=False)

# 3. Load pit_sku_price_history.json
cache_path = Path("backend/ml/data/processed/pit_sku_price_history.json")
print(f"Loading {cache_path}...")
with open(cache_path, "r", encoding="utf-8") as f:
    cache = json.load(f)

# Inspect missing values
print(f"\nMissing StockCode in clean_gross_sales: {df_sales['StockCode'].isna().sum()}")
print(f"Missing StockCode in daily_product_demand: {df_demand['StockCode'].isna().sum()}")

# Inspect raw unique StockCode counts
raw_sales_skus = set(df_sales["StockCode"].dropna())
raw_demand_skus = set(df_demand["StockCode"].dropna())
raw_cache_skus = set(cache.get("skus", {}).keys())

print(f"\nRaw unique StockCode count:")
print(f"  clean_gross_sales:    {len(raw_sales_skus)}")
print(f"  daily_product_demand: {len(raw_demand_skus)}")
print(f"  pit price cache:      {len(raw_cache_skus)}")

# Inspect normalized (string, stripped, upper) StockCode counts
norm_sales_skus = set(df_sales["StockCode"].astype(str).str.strip().str.upper())
norm_demand_skus = set(df_demand["StockCode"].astype(str).str.strip().str.upper())
norm_cache_skus = set(str(k).strip().upper() for k in cache.get("skus", {}).keys())

print(f"\nNormalized (str.strip().upper()) unique StockCode count:")
print(f"  clean_gross_sales:    {len(norm_sales_skus)}")
print(f"  daily_product_demand: {len(norm_demand_skus)}")
print(f"  pit price cache:      {len(norm_cache_skus)}")

# Exact Set Comparisons:
# A. In clean_gross_sales but not daily_product_demand
diff_A_raw = raw_sales_skus - raw_demand_skus
diff_A_norm = norm_sales_skus - norm_demand_skus

print(f"\nA. SKUs in clean_gross_sales but not daily_product_demand:")
print(f"  Raw set difference count:        {len(diff_A_raw)}")
print(f"  Raw differing SKUs:              {diff_A_raw}")
print(f"  Normalized set difference count: {len(diff_A_norm)}")
print(f"  Normalized differing SKUs:       {diff_A_norm}")

# B. In daily_product_demand but not clean_gross_sales
diff_B_raw = raw_demand_skus - raw_sales_skus
diff_B_norm = norm_demand_skus - norm_sales_skus

print(f"\nB. SKUs in daily_product_demand but not clean_gross_sales:")
print(f"  Raw set difference count:        {len(diff_B_raw)}")
print(f"  Raw differing SKUs:              {diff_B_raw}")
print(f"  Normalized set difference count: {len(diff_B_norm)}")
print(f"  Normalized differing SKUs:       {diff_B_norm}")

# C. In clean_gross_sales but not price cache
diff_C_raw = raw_sales_skus - raw_cache_skus
diff_C_norm = norm_sales_skus - norm_cache_skus

print(f"\nC. SKUs in clean_gross_sales but not price cache:")
print(f"  Raw set difference count:        {len(diff_C_raw)}")
print(f"  Raw differing SKUs:              {diff_C_raw}")
print(f"  Normalized set difference count: {len(diff_C_norm)}")
print(f"  Normalized differing SKUs:       {diff_C_norm}")

# D. In price cache but not clean_gross_sales
diff_D_raw = raw_cache_skus - raw_sales_skus
diff_D_norm = norm_cache_skus - norm_sales_skus

print(f"\nD. SKUs in price cache but not clean_gross_sales:")
print(f"  Raw set difference count:        {len(diff_D_raw)}")
print(f"  Raw differing SKUs:              {diff_D_raw}")
print(f"  Normalized set difference count: {len(diff_D_norm)}")
print(f"  Normalized differing SKUs:       {diff_D_norm}")

# Check any differing representations in sales
print("\nChecking any specific SKUs with whitespace or case differences in clean_gross_sales:")
sku_counts = df_sales["StockCode"].astype(str).value_counts()
for s in diff_A_raw:
    print(f"  SKU '{s}': occurrences={sku_counts.get(s, 0)}, repr={repr(s)}")
    # Find matching normalized
    matches = [x for x in norm_sales_skus if str(x) == str(s).strip().upper()]
    print(f"    Normalized match: {matches}")

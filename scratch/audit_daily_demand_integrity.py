import sys
import pandas as pd
import numpy as np
from pathlib import Path

print("=== TASK 25: DAILY DEMAND DATASET INTEGRITY AUDIT ===")

demand_path = Path("backend/ml/data/processed/daily_product_demand.csv")
sales_path = Path("backend/ml/data/processed/clean_gross_sales.csv")
raw_path = Path("backend/ml/data/raw/online_retail_II.csv")

print(f"Loading {demand_path}...")
df_demand = pd.read_csv(demand_path, low_memory=False)

# 1. Total rows
total_rows = len(df_demand)
print(f"Total rows: {total_rows:,} (Expected: 2,287,495)")
assert total_rows == 2287495, f"Row count mismatch: {total_rows}"

# 2. Service codes check
NON_MERCHANDISE_CODES = {
    "POST", "DOT", "M", "BANK CHARGES", "PADS", "AMAZONFEE",
    "D", "CRUK", "ADJUST", "TEST001", "C2"
}
skus = set(df_demand["StockCode"].astype(str).str.strip().str.upper())
service_present = skus.intersection(NON_MERCHANDISE_CODES)
print(f"Service codes present: {service_present}")
assert len(service_present) == 0, f"Found service codes in daily demand: {service_present}"

# 3. Missing StockCode values
missing_skus = df_demand["StockCode"].isna().sum()
print(f"Missing StockCode values: {missing_skus}")
assert missing_skus == 0, f"Found {missing_skus} missing StockCodes"

# 4. Invalid dates
parsed_dates = pd.to_datetime(df_demand["date"], errors="coerce")
invalid_dates = parsed_dates.isna().sum()
print(f"Invalid dates count: {invalid_dates}")
assert invalid_dates == 0, f"Found {invalid_dates} invalid dates"
min_date = parsed_dates.min().date()
max_date = parsed_dates.max().date()
print(f"Date range: {min_date} to {max_date}")

# 5. Negative daily demand
neg_demand = (df_demand["daily_demand"] < 0).sum()
print(f"Negative daily demand records: {neg_demand}")
assert neg_demand == 0, f"Found {neg_demand} negative demand records"

# 6. Duplicate StockCode / date pairs
duplicates = df_demand.duplicated(subset=["StockCode", "date"]).sum()
print(f"Duplicate (StockCode, date) pairs: {duplicates}")
assert duplicates == 0, f"Found {duplicates} duplicate pairs"

# 7. Correct daily sorting (by StockCode, date)
# Check if dates are strictly ascending within each SKU
print("Checking daily sorting and date continuity within each SKU...")
df_demand["date_dt"] = parsed_dates

sorting_errors = 0
discontinuous_intervals = 0
total_demand_sum = df_demand["daily_demand"].sum()

for sku, group in df_demand.groupby("StockCode"):
    # Check monotonic increasing dates
    if not group["date_dt"].is_monotonic_increasing:
        sorting_errors += 1
    # Check step = 1 day
    date_diffs = group["date_dt"].diff().dropna()
    if not (date_diffs == pd.Timedelta(days=1)).all():
        discontinuous_intervals += 1

print(f"Sorting errors count: {sorting_errors}")
assert sorting_errors == 0, f"Found {sorting_errors} sorting errors"
print(f"Discontinuous calendar intervals count: {discontinuous_intervals}")
assert discontinuous_intervals == 0, f"Found {discontinuous_intervals} discontinuous intervals"

# 8. Reconcile total demand quantity with clean commercial transaction quantities
print(f"\nTotal daily demand volume: {total_demand_sum:,} units")

print(f"Loading {sales_path}...")
df_sales = pd.read_csv(sales_path, encoding="latin1", low_memory=False)
total_sales_qty = df_sales["Quantity"].sum()
print(f"Total clean_gross_sales Quantity: {total_sales_qty:,} units")
demand_qty_diff = abs(total_demand_sum - total_sales_qty)
print(f"Difference between daily demand and transaction quantity: {demand_qty_diff}")
assert demand_qty_diff < 1e-4, f"Mismatch between daily demand and sales quantity: {demand_qty_diff}"

# 9. Verify 17,563 removed service units reconcile with raw source
print(f"\nReconciling removed service units with raw online_retail_II.csv...")
df_raw = pd.read_csv(raw_path, encoding="latin1", low_memory=False)
# Identify raw positive sales records that have service codes
raw_gross_mask = (
    (df_raw["Quantity"] > 0) &
    (df_raw["Price"] > 0) &
    (~df_raw["Invoice"].astype(str).str.startswith("C", na=False))
)
raw_gross = df_raw[raw_gross_mask]
raw_service_mask = raw_gross["StockCode"].astype(str).str.strip().str.upper().isin(NON_MERCHANDISE_CODES)
raw_service_qty = raw_gross.loc[raw_service_mask, "Quantity"].sum()
raw_commercial_qty = raw_gross.loc[~raw_service_mask, "Quantity"].sum()
print(f"Raw gross sales total quantity:      {raw_gross['Quantity'].sum():,}")
print(f"Raw service transactions quantity:   {raw_service_qty:,} units (Expected: 17,563)")
print(f"Raw commercial merchandise quantity: {raw_commercial_qty:,} units (Expected: {total_sales_qty:,})")

assert raw_service_qty == 17563, f"Expected 17,563 service units, got {raw_service_qty}"
assert raw_commercial_qty == total_sales_qty, f"Commercial quantity mismatch: {raw_commercial_qty} vs {total_sales_qty}"

# 10. Summary statistics
pos_count = (df_demand["daily_demand"] > 0).sum()
zero_count = (df_demand["daily_demand"] == 0).sum()
mean_demand = df_demand["daily_demand"].mean()
std_demand = df_demand["daily_demand"].std()
max_demand = df_demand["daily_demand"].max()

print(f"\nSummary Statistics for daily_product_demand.csv:")
print(f"  Positive demand days: {pos_count:,} ({pos_count/total_rows*100:.2f}%)")
print(f"  Zero demand days:     {zero_count:,} ({zero_count/total_rows*100:.2f}%)")
print(f"  Mean daily demand:    {mean_demand:.4f}")
print(f"  Std daily demand:     {std_demand:.4f}")
print(f"  Max single-day demand:{max_demand:,}")

print("\n=== SECTION 3: ALL DATASET INTEGRITY CHECKS PASSED 100% ===")

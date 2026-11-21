import sys
from pathlib import Path
import pandas as pd
import numpy as np

backend_dir = Path("backend").resolve()
sys.path.insert(0, str(backend_dir))

from ml.src.preprocessing import NON_MERCHANDISE_CODES

print("NON_MERCHANDISE_CODES defined:", NON_MERCHANDISE_CODES)

daily_path = backend_dir / "ml" / "data" / "processed" / "daily_product_demand.csv"
print(f"\n--- INSPECTING {daily_path.name} ---")
df_daily = pd.read_csv(daily_path, dtype={"StockCode": str}, low_memory=False)
df_daily["StockCode_clean"] = df_daily["StockCode"].fillna("").astype(str).str.strip().str.upper()

total_daily_rows = len(df_daily)
total_daily_demand = df_daily["daily_demand"].sum()
total_daily_skus = df_daily["StockCode_clean"].nunique()

is_service_daily = df_daily["StockCode_clean"].isin(NON_MERCHANDISE_CODES)
service_daily_rows = int(is_service_daily.sum())
service_daily_demand = df_daily.loc[is_service_daily, "daily_demand"].sum()
service_daily_skus = df_daily.loc[is_service_daily, "StockCode_clean"].nunique()

print(f"Total rows in daily_product_demand.csv: {total_daily_rows:,}")
print(f"Total unique SKUs: {total_daily_skus:,}")
print(f"Total demand volume: {total_daily_demand:,.2f}")
print(f"Service rows found: {service_daily_rows:,} ({service_daily_rows/total_daily_rows*100:.4f}%)")
print(f"Service unique SKUs: {service_daily_skus}")
print(f"Service demand volume: {service_daily_demand:,.2f} ({service_daily_demand/total_daily_demand*100:.4f}%)")

service_sku_breakdown = df_daily[is_service_daily].groupby("StockCode_clean")["daily_demand"].agg(["count", "sum"])
print("\nBreakdown of service codes in daily_product_demand.csv:")
print(service_sku_breakdown)

# Check clean_gross_sales.csv if present on disk
sales_path = backend_dir / "ml" / "data" / "processed" / "clean_gross_sales.csv"
if sales_path.is_file():
    print(f"\n--- INSPECTING {sales_path.name} ON DISK ---")
    df_sales = pd.read_csv(sales_path, dtype={"StockCode": str}, low_memory=False, encoding="latin1")
    df_sales["StockCode_clean"] = df_sales["StockCode"].fillna("").astype(str).str.strip().str.upper()
    is_service_sales = df_sales["StockCode_clean"].isin(NON_MERCHANDISE_CODES)
    print(f"Total rows: {len(df_sales):,}")
    print(f"Service rows found in clean_gross_sales.csv on disk: {is_service_sales.sum():,}")
else:
    print(f"\n{sales_path.name} not on disk.")

# Check raw online_retail_II.csv
raw_path = backend_dir / "ml" / "data" / "raw" / "online_retail_II.csv"
print(f"\n--- INSPECTING {raw_path.name} ---")
df_raw = pd.read_csv(raw_path, dtype={"StockCode": str, "Invoice": str}, low_memory=False, encoding="latin1")
df_raw["StockCode_clean"] = df_raw["StockCode"].fillna("").astype(str).str.strip().str.upper()
is_service_raw = df_raw["StockCode_clean"].isin(NON_MERCHANDISE_CODES)
print(f"Total raw rows: {len(df_raw):,}")
print(f"Total raw service rows: {is_service_raw.sum():,}")

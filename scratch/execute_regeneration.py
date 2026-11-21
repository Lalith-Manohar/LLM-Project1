import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np

backend_dir = Path("backend").resolve()
sys.path.insert(0, str(backend_dir))

from ml.src.preprocessing import run_preprocessing_pipeline, NON_MERCHANDISE_CODES
from ml.src.feature_engineering import run_daily_aggregation_pipeline
from ml.src.point_in_time_price import PointInTimePriceService

proc_dir = backend_dir / "ml" / "data" / "processed"
raw_csv = backend_dir / "ml" / "data" / "raw" / "online_retail_II.csv"

print("==================================================================")
print("=== NEXORA TASK 24: CONTROLLED CLEAN DATASET REGENERATION ===")
print("==================================================================")

# Step 1: Execute Preprocessing Pipeline
t0 = time.time()
print("\n[Step 1/3] Executing Preprocessing Pipeline from raw data...")
prep_res = run_preprocessing_pipeline(raw_csv_path=str(raw_csv), output_dir=proc_dir)
print(f"Preprocessing completed in {time.time() - t0:.2f}s.")

# Verify clean_gross_sales.csv
sales_csv = proc_dir / "clean_gross_sales.csv"
df_sales = pd.read_csv(sales_csv, dtype={"StockCode": str}, encoding="latin1", low_memory=False)
df_sales["StockCode_clean"] = df_sales["StockCode"].fillna("").astype(str).str.strip().str.upper()
service_in_sales = df_sales["StockCode_clean"].isin(NON_MERCHANDISE_CODES).sum()
print(f"Verified clean_gross_sales.csv: {len(df_sales):,} rows, {df_sales['StockCode_clean'].nunique():,} unique SKUs.")
print(f"Service codes present in clean_gross_sales.csv: {service_in_sales}")
assert len(df_sales) == 1037089, f"Expected 1,037,089 merchandise rows, got {len(df_sales)}"
assert service_in_sales == 0, f"Expected 0 service rows, got {service_in_sales}"

# Step 2: Execute Daily Aggregation Pipeline
t1 = time.time()
print("\n[Step 2/3] Executing Daily Aggregation Pipeline from clean_gross_sales.csv...")
daily_df, daily_val = run_daily_aggregation_pipeline(sales_csv_path=str(sales_csv), output_dir=proc_dir)
print(f"Daily aggregation completed in {time.time() - t1:.2f}s.")

# Verify daily_product_demand.csv
daily_csv = proc_dir / "daily_product_demand.csv"
df_daily = pd.read_csv(daily_csv, dtype={"StockCode": str}, low_memory=False)
df_daily["StockCode_clean"] = df_daily["StockCode"].fillna("").astype(str).str.strip().str.upper()
service_in_daily = df_daily["StockCode_clean"].isin(NON_MERCHANDISE_CODES).sum()

print("\n--- REGENERATED DATASET PROFILE ---")
print(f"Total daily product rows: {len(df_daily):,}")
print(f"Unique commercial SKUs: {df_daily['StockCode_clean'].nunique():,}")
print(f"Date range: {df_daily['date'].min()} to {df_daily['date'].max()}")
print(f"Positive-demand rows: {(df_daily['daily_demand'] > 0).sum():,}")
print(f"Zero-demand rows: {(df_daily['daily_demand'] == 0).sum():,}")
print(f"Total commercial demand units: {df_daily['daily_demand'].sum():,}")
print(f"Service-code row count: {service_in_daily}")
print(f"Dataset file size: {daily_csv.stat().st_size:,} bytes")

import hashlib
h = hashlib.sha256(daily_csv.read_bytes()).hexdigest().upper()
print(f"Dataset SHA-256: {h}")

assert service_in_daily == 0, f"Expected 0 service rows in daily_product_demand.csv, got {service_in_daily}"

# Step 3: Rebuild Point-in-Time Price Cache
t2 = time.time()
print("\n[Step 3/3] Rebuilding Point-in-Time Price Cache from clean_gross_sales.csv...")
pit_svc = PointInTimePriceService(data_dir=proc_dir)
pit_svc.load_index()
print(f"Price cache rebuilt in {time.time() - t2:.2f}s.")

print("\n==================================================================")
print("=== DATASET REGENERATION SUCCESSFULLY COMPLETED & VERIFIED ===")
print("==================================================================")

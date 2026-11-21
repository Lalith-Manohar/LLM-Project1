import sys
from pathlib import Path
import pandas as pd
import numpy as np

backend_dir = Path("backend").resolve()
sys.path.insert(0, str(backend_dir))

from ml.src.preprocessing import NON_MERCHANDISE_CODES
from ml.src.point_in_time_price import PointInTimePriceService

# Let's inspect the 11 excluded service codes
print("Total NON_MERCHANDISE_CODES:", len(NON_MERCHANDISE_CODES))
print("Codes:", sorted(list(NON_MERCHANDISE_CODES)))

# Let's test price service with and without service codes
sales_path = backend_dir / "ml" / "data" / "processed" / "clean_gross_sales.csv"
df_sales = pd.read_csv(sales_path, dtype={"StockCode": str}, low_memory=False, encoding="latin1")
df_sales["StockCode_clean"] = df_sales["StockCode"].fillna("").astype(str).str.strip().str.upper()

all_skus = df_sales["StockCode_clean"].nunique()
commercial_skus = df_sales.loc[~df_sales["StockCode_clean"].isin(NON_MERCHANDISE_CODES), "StockCode_clean"].nunique()
service_skus_in_sales = df_sales.loc[df_sales["StockCode_clean"].isin(NON_MERCHANDISE_CODES), "StockCode_clean"].nunique()

print(f"\nAll SKUs in gross sales: {all_skus}")
print(f"Service SKUs in gross sales: {service_skus_in_sales}")
print(f"Commercial SKUs in gross sales: {commercial_skus}")
print(f"Difference (All - Commercial): {all_skus - commercial_skus}")

# Inspect SKU 85123A transactions
sku_txs = df_sales[df_sales["StockCode_clean"] == "85123A"].copy()
sku_txs["date"] = pd.to_datetime(sku_txs["InvoiceDate"]).dt.date
print(f"\nSKU 85123A transaction count: {len(sku_txs):,}")
print(f"SKU 85123A mean price: {sku_txs['Price'].mean():.6f}")

# Check price calculation for 85123A on observation date 2011-12-09
# 1. Using current cache or service
pit_svc = PointInTimePriceService(data_dir=backend_dir / "ml" / "data" / "processed")
pit_svc.ensure_loaded()
price_today = pit_svc.get_price("85123A", "2011-12-09")
price_no_date = pit_svc.get_price("85123A")
print(f"PointInTimePriceService get_price('85123A', '2011-12-09'): {price_today}")
print(f"PointInTimePriceService get_price('85123A'): {price_no_date}")

# Let's check why 3.0749 vs 3.0744 occurred
# Let's see: on 2011-12-09 (the final dataset date), are there transactions on 2011-12-09?
txs_before_dec9 = sku_txs[sku_txs["date"] < pd.to_datetime("2011-12-09").date()]
txs_all = sku_txs
print(f"Mean price strictly before 2011-12-09 (tx_date < 2011-12-09): {txs_before_dec9['Price'].mean():.6f}")
print(f"Mean price of all transactions (including 2011-12-09): {txs_all['Price'].mean():.6f}")

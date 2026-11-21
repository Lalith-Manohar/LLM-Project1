import sys
from pathlib import Path
import pandas as pd
import numpy as np

backend_dir = Path("backend").resolve()
sys.path.insert(0, str(backend_dir))

from ml.src.data_loader import load_raw_data
from ml.src.preprocessing import classify_transactions, NON_MERCHANDISE_CODES

raw_path = backend_dir / "ml" / "data" / "raw" / "online_retail_II.csv"
print(f"Loading raw data from: {raw_path}...")
df_raw = load_raw_data(raw_path)
total_raw = len(df_raw)
print(f"Total raw rows loaded: {total_raw:,}")

print("Classifying transactions...")
df_classified = classify_transactions(df_raw)

# Count streams
stream_counts = df_classified["transaction_stream"].value_counts().to_dict()
print("\nStream counts from classify_transactions:")
for k, v in stream_counts.items():
    print(f"  {k}: {v:,}")

# In gross_sales, split into merchandise vs service
gross_mask = df_classified["transaction_stream"] == "gross_sales"
df_gross = df_classified[gross_mask]

is_service = df_gross["StockCode"].fillna("").astype(str).str.strip().str.upper().isin(NON_MERCHANDISE_CODES)
n_service = int(is_service.sum())
n_merchandise = int((~is_service).sum())

n_cancel = stream_counts.get("cancellation", 0)
n_return = stream_counts.get("return_credit", 0)
n_exceptional = stream_counts.get("exceptional", 0)

print("\n--- FINAL INDEPENDENT RECONCILIATION ---")
print(f"1. Commercial Merchandise:  {n_merchandise:,}")
print(f"2. Service Transactions:     {n_service:,}")
print(f"3. Cancellations:            {n_cancel:,}")
print(f"4. Returns & Credits:        {n_return:,}")
print(f"5. Exceptional Records:      {n_exceptional:,}")
total_partitioned = n_merchandise + n_service + n_cancel + n_return + n_exceptional
print(f"Total Partitioned Sum:       {total_partitioned:,}")
print(f"Total Raw Rows:              {total_raw:,}")
print(f"Difference:                  {total_partitioned - total_raw}")
assert total_partitioned == total_raw == 1067371

# Verify mutual exclusivity
print("\nVerifying Mutual Exclusivity:")
print(f"Null classifications: {df_classified['transaction_stream'].isnull().sum()}")
assert df_classified["transaction_stream"].isnull().sum() == 0
assert len(df_classified) == total_raw
print("Mutual exclusivity and collective exhaustiveness: 100% VERIFIED!")

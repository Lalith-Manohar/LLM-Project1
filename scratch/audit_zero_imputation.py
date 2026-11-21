import pandas as pd
from pathlib import Path

daily_path = Path("backend/ml/data/processed/daily_product_demand.csv")
print(f"Loading {daily_path}...")
df = pd.read_csv(daily_path, dtype={"StockCode": str}, low_memory=False)

total_rows = len(df)
zero_rows = int((df["daily_demand"] == 0).sum())
nonzero_rows = int((df["daily_demand"] > 0).sum())
zero_pct = (zero_rows / total_rows) * 100

print(f"Total rows: {total_rows:,}")
print(f"Zero demand rows: {zero_rows:,} ({zero_pct:.2f}%)")
print(f"Positive demand rows: {nonzero_rows:,} ({nonzero_rows/total_rows*100:.2f}%)")

# Check bounding for a random sample of 50 SKUs
df["date"] = pd.to_datetime(df["date"]).dt.date
sample_skus = df["StockCode"].unique()[:50]

bounded_correctly = 0
for sku in sample_skus:
    sub = df[df["StockCode"] == sku]
    pos = sub[sub["daily_demand"] > 0]
    if len(pos) > 0:
        first_pos = pos["date"].min()
        last_pos = pos["date"].max()
        first_row = sub["date"].min()
        last_row = sub["date"].max()
        # Verify first_row == first_pos and last_row == last_pos
        if first_row == first_pos and last_row == last_pos:
            bounded_correctly += 1

print(f"\nLifespan bounding check on 50 sampled SKUs: {bounded_correctly}/50 SKUs strictly bounded between first and last positive sale.")

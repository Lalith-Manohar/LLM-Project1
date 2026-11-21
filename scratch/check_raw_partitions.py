import pandas as pd
from pathlib import Path

raw_path = Path("backend/ml/data/raw/online_retail_II.csv")
df = pd.read_csv(raw_path, dtype={"StockCode": str, "Invoice": str}, low_memory=False, encoding="latin1")

invoice_str = df["Invoice"].fillna("").astype(str).str.strip()
is_cancel_all = invoice_str.str.startswith("C")

qty = pd.to_numeric(df["Quantity"], errors="coerce")
price = pd.to_numeric(df["Price"], errors="coerce")

print(f"Total raw: {len(df):,}")
print(f"All invoices starting with C: {is_cancel_all.sum():,}")
print(f"All qty < 0 without C: {((~is_cancel_all) & (qty < 0)).sum():,}")
print(f"All qty > 0 and price > 0 without C: {((~is_cancel_all) & (qty > 0) & (price > 0)).sum():,}")
print(f"All remaining: {len(df) - is_cancel_all.sum() - ((~is_cancel_all) & (qty < 0)).sum() - ((~is_cancel_all) & (qty > 0) & (price > 0)).sum():,}")

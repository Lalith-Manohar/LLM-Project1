"""Verification script for the combined 2-year UCI Online Retail II dataset."""
import pandas as pd
from pathlib import Path

csv_path = Path("backend/ml/data/raw/online_retail_II.csv")
backup_path = Path("backend/ml/data/raw/online_retail_II_2010_2011_backup.csv")
xlsx_path = Path("backend/ml/data/raw/online_retail_II.xlsx")

print("=== Checking File Existence & Sizes ===")
print(f"Combined CSV: {csv_path.exists()} ({csv_path.stat().st_size:,} bytes)")
print(f"Backup 1-Year CSV: {backup_path.exists()} ({backup_path.stat().st_size:,} bytes)")
print(f"Original XLSX: {xlsx_path.exists()} ({xlsx_path.stat().st_size:,} bytes)")

print("\n=== Loading Combined CSV ===")
df = pd.read_csv(
    csv_path,
    dtype={"Invoice": str, "StockCode": str, "Customer ID": str},
    encoding="latin1",
    low_memory=False
)

total_rows = len(df)
print(f"Total Rows: {total_rows:,} (Expected: 1,067,371)")
assert total_rows == 1067371, f"Expected 1,067,371 rows, got {total_rows:,}"

print("\n=== Checking Columns ===")
expected_cols = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]
print(f"Columns: {list(df.columns)}")
assert list(df.columns) == expected_cols, f"Column mismatch: {list(df.columns)} vs {expected_cols}"

print("\n=== Checking Date Range ===")
dates = pd.to_datetime(df["InvoiceDate"])
min_date = dates.min()
max_date = dates.max()
unique_calendar_dates = dates.dt.date.nunique()
print(f"Min Date: {min_date}")
print(f"Max Date: {max_date}")
print(f"Unique Calendar Dates: {unique_calendar_dates}")
assert str(min_date).startswith("2009-12-01"), f"Unexpected min date: {min_date}"
assert str(max_date).startswith("2011-12-09"), f"Unexpected max date: {max_date}"

print("\n=== Missing Value Profile ===")
missing_summary = {}
for col in df.columns:
    cnt = int(df[col].isnull().sum())
    pct = (cnt / total_rows) * 100
    missing_summary[col] = (cnt, pct)
    print(f"  {col}: {cnt:,} nulls ({pct:.2f}%)")

print("\n=== Key Entity Counts ===")
n_invoices = df["Invoice"].nunique()
n_skus = df["StockCode"].nunique()
n_countries = df["Country"].nunique()
n_customers = df["Customer ID"].nunique()
print(f"Unique Invoices: {n_invoices:,}")
print(f"Unique StockCodes: {n_skus:,}")
print(f"Unique Countries: {n_countries:,}")
print(f"Unique Customer IDs: {n_customers:,}")

print("\n=== Numerical Ranges ===")
qty_min, qty_max = df["Quantity"].min(), df["Quantity"].max()
price_min, price_max = df["Price"].min(), df["Price"].max()
print(f"Quantity Range: [{qty_min:,}, {qty_max:,}]")
print(f"Price Range: [{price_min}, {price_max}]")

print("\n=== Duplicate Analysis ===")
dup_rows = int(df.duplicated().sum())
print(f"Full Row Duplicates: {dup_rows:,} ({(dup_rows/total_rows)*100:.2f}%)")

print("\n=== Validation Result: 100% PASSED ===")

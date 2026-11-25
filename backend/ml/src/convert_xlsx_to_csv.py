"""Reproducible XLSX-to-CSV Conversion Pipeline for UCI Online Retail II.

Task 10: Original Dataset Recovery
Reads both historical worksheets ('Year 2009-2010' and 'Year 2010-2011') from
backend/ml/data/raw/online_retail_II.xlsx, validates their structure, combines
them into a single authoritative 2-year dataset (1,067,371 records), and validates
data integrity without record loss or column distortion.
"""

import os
import sys
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np


def get_raw_data_dir() -> Path:
    """Returns absolute path to backend/ml/data/raw/."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "raw"


def convert_xlsx_to_csv(
    xlsx_path: Path = None,
    output_csv_path: Path = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Converts multi-sheet Online Retail II Excel workbook to a single consolidated CSV."""
    raw_dir = get_raw_data_dir()
    if xlsx_path is None:
        xlsx_path = raw_dir / "online_retail_II.xlsx"
    if output_csv_path is None:
        output_csv_path = raw_dir / "online_retail_II.csv"

    if not xlsx_path.is_file():
        raise FileNotFoundError(f"Original Excel workbook not found at: {xlsx_path}")

    print(f"[Conversion] Loading original Excel workbook from: {xlsx_path}...")
    dtype_spec = {
        "Invoice": str,
        "StockCode": str,
        "Description": str,
        "Customer ID": str,
        "Country": str
    }

    print("[Conversion] Reading Sheet 1: 'Year 2009-2010'...")
    df_2009 = pd.read_excel(
        xlsx_path,
        sheet_name="Year 2009-2010",
        dtype=dtype_spec
    )
    rows_2009 = len(df_2009)
    print(f"  -> Sheet 1 loaded: {rows_2009:,} records.")

    print("[Conversion] Reading Sheet 2: 'Year 2010-2011'...")
    df_2010 = pd.read_excel(
        xlsx_path,
        sheet_name="Year 2010-2011",
        dtype=dtype_spec
    )
    rows_2010 = len(df_2010)
    print(f"  -> Sheet 2 loaded: {rows_2010:,} records.")

    # 1. Column consistency verification
    cols_2009 = df_2009.columns.tolist()
    cols_2010 = df_2010.columns.tolist()
    if cols_2009 != cols_2010:
        raise ValueError(
            f"Worksheet column mismatch!\nSheet 1: {cols_2009}\nSheet 2: {cols_2010}"
        )

    # 2. Date normalization to ISO format 'YYYY-MM-DD HH:MM:SS'
    print("[Conversion] Normalizing dates and verifying temporal coverage...")
    df_2009["InvoiceDate"] = pd.to_datetime(df_2009["InvoiceDate"])
    df_2010["InvoiceDate"] = pd.to_datetime(df_2010["InvoiceDate"])

    min_date_2009, max_date_2009 = df_2009["InvoiceDate"].min(), df_2009["InvoiceDate"].max()
    min_date_2010, max_date_2010 = df_2010["InvoiceDate"].min(), df_2010["InvoiceDate"].max()

    print(f"  -> Sheet 1 Date Range: {min_date_2009} to {max_date_2009}")
    print(f"  -> Sheet 2 Date Range: {min_date_2010} to {max_date_2010}")

    # 3. Concatenate worksheets
    print("[Conversion] Concatenating worksheets into unified 2-year dataset...")
    df_combined = pd.concat([df_2009, df_2010], ignore_index=True)
    total_combined_rows = len(df_combined)
    expected_total_rows = rows_2009 + rows_2010

    if total_combined_rows != expected_total_rows:
        raise ValueError(
            f"Concatenation error! Expected {expected_total_rows:,} rows, but got {total_combined_rows:,}."
        )

    # 4. Format InvoiceDate as standard string 'YYYY-MM-DD HH:MM:SS' for unambiguous CSV serialization
    df_combined["InvoiceDate"] = df_combined["InvoiceDate"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # 5. Write to temporary CSV first to verify before replacing
    temp_csv_path = raw_dir / "online_retail_II_combined_temp.csv"
    print(f"[Conversion] Serializing combined records to temporary CSV: {temp_csv_path}...")
    df_combined.to_csv(
        temp_csv_path,
        index=False,
        encoding="latin1"
    )

    # 6. Verify written CSV
    print("[Conversion] Verifying serialized CSV integrity...")
    df_verify = pd.read_csv(
        temp_csv_path,
        dtype=dtype_spec,
        encoding="latin1",
        low_memory=False
    )
    if len(df_verify) != expected_total_rows:
        raise RuntimeError(
            f"Verification failed: Written CSV has {len(df_verify):,} rows; expected {expected_total_rows:,}."
        )

    # 7. Atomically replace target online_retail_II.csv
    print(f"[Conversion] Replacing {output_csv_path.name} with verified 2-year combined dataset...")
    if output_csv_path.exists():
        # Ensure backup exists
        backup_path = raw_dir / "online_retail_II_2010_2011_backup.csv"
        if not backup_path.exists():
            import shutil
            shutil.copy2(output_csv_path, backup_path)
            print(f"  -> Backed up original 1-year CSV to: {backup_path.name}")
        output_csv_path.unlink()

    temp_csv_path.rename(output_csv_path)
    print(f"[Conversion] Successfully generated {output_csv_path.name} ({output_csv_path.stat().st_size:,} bytes)!")

    # Compile conversion metadata
    metadata = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_file": str(xlsx_path.name),
        "target_file": str(output_csv_path.name),
        "sheet_1_name": "Year 2009-2010",
        "sheet_1_rows": rows_2009,
        "sheet_1_min_date": str(min_date_2009),
        "sheet_1_max_date": str(max_date_2009),
        "sheet_2_name": "Year 2010-2011",
        "sheet_2_rows": rows_2010,
        "sheet_2_min_date": str(min_date_2010),
        "sheet_2_max_date": str(max_date_2010),
        "combined_total_rows": total_combined_rows,
        "overall_min_date": str(min(min_date_2009, min_date_2010)),
        "overall_max_date": str(max(max_date_2009, max_date_2010)),
        "columns": cols_2009,
        "reconciliation_passed": (total_combined_rows == expected_total_rows)
    }

    return df_combined, metadata


if __name__ == "__main__":
    df_comb, meta = convert_xlsx_to_csv()
    print("\n==========================================================================")
    print("CONVERSION SUMMARY")
    print("==========================================================================")
    for k, v in meta.items():
        print(f"  {k}: {v}")

"""Data loader and exploratory data analysis (EDA) module for NEXORA.

This module provides reusable, student-friendly functions for loading the raw
UCI Online Retail II dataset and performing comprehensive exploratory data analysis.

It inspects transaction types, cancellations, returns, data quality anomalies,
and outputs a structured markdown report and summary CSV tables into
backend/ml/data/processed/ without modifying the raw dataset.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


def get_default_raw_data_path() -> Path:
    """Returns the absolute path to the default raw dataset CSV."""
    # Anchored relative to this file: backend/ml/src/data_loader.py -> backend/ml/data/raw/online_retail_II.csv
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "data" / "raw" / "online_retail_II.csv"


def get_default_processed_data_dir() -> Path:
    """Returns the path to the processed data directory, creating it if needed."""
    base_dir = Path(__file__).resolve().parent.parent
    processed_dir = base_dir / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    return processed_dir


def load_raw_data(file_path: Optional[str] = None) -> pd.DataFrame:
    """Loads the raw retail dataset from CSV into a pandas DataFrame.
    
    Args:
        file_path: Optional custom path. If None, uses backend/ml/data/raw/online_retail_II.csv.
        
    Returns:
        pd.DataFrame: Unmodified raw transaction dataset.
        
    Raises:
        FileNotFoundError: If the CSV file does not exist.
    """
    path = Path(file_path) if file_path else get_default_raw_data_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"Raw dataset not found at expected path: {path}. "
            f"Please place 'online_retail_II.csv' inside backend/ml/data/raw/."
        )

    print(f"[NEXORA Data Loader] Loading raw dataset from: {path}...")
    # Read CSV preserving original string identifiers for Invoice and StockCode.
    # Note: The UCI Online Retail II dataset contains the UK Pound sign (£ = 0xa3),
    # which requires 'latin1' (ISO-8859-1) or 'cp1252' encoding rather than standard UTF-8.
    df = pd.read_csv(
        path,
        dtype={
            "Invoice": str,
            "StockCode": str,
            "Customer ID": str
        },
        encoding="latin1",
        low_memory=False
    )
    print(f"[NEXORA Data Loader] Successfully loaded {len(df):,} records.")
    return df


def explore_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """Performs comprehensive exploratory data analysis on the raw transactions.
    
    Calculates:
    - Dimensions, columns, and data types
    - Missing values (counts and percentages)
    - Duplicate rows
    - Unique invoices, StockCodes, customers, countries
    - Temporal date coverage and parsing checks
    - Quantity and Price distributions (min, max, percentiles, negative/zero counts)
    - Detailed cancellation ('C') and return analysis
    - Top products by frequency and gross quantity sold
    
    Args:
        df: Raw DataFrame loaded by load_raw_data().
        
    Returns:
        dict: Structured dictionary containing all calculated metrics.
    """
    print("[NEXORA EDA] Performing statistical and transaction profiling...")
    total_rows, total_cols = df.shape

    # 1. Column analysis and missing values
    missing_counts = df.isnull().sum()
    missing_pct = (missing_counts / total_rows) * 100
    missing_summary = pd.DataFrame({
        "column": df.columns,
        "dtype": [str(t) for t in df.dtypes],
        "missing_count": missing_counts.values,
        "missing_percentage": missing_pct.values
    })

    # 2. Duplicate records
    duplicate_count = int(df.duplicated().sum())
    duplicate_pct = (duplicate_count / total_rows) * 100

    # 3. Entity cardinalities
    unique_invoices = int(df["Invoice"].nunique(dropna=True))
    unique_stock_codes = int(df["StockCode"].nunique(dropna=True))
    unique_customers = int(df["Customer ID"].nunique(dropna=True))
    unique_countries = int(df["Country"].nunique(dropna=True))
    countries_list = df["Country"].dropna().unique().tolist()
    top_countries = df["Country"].value_counts().head(10).to_dict()

    # 4. Date parsing & temporal range
    # Parse InvoiceDate with explicit UK day-first format ('%d-%m-%y %H:%M')
    parsed_dates = pd.to_datetime(df["InvoiceDate"], format="%d-%m-%y %H:%M", errors="coerce")
    if parsed_dates.isnull().any():
        fallback_mask = parsed_dates.isnull()
        parsed_dates[fallback_mask] = pd.to_datetime(df.loc[fallback_mask, "InvoiceDate"], errors="coerce", dayfirst=True)
    invalid_dates_count = int(parsed_dates.isnull().sum())
    min_date = parsed_dates.min()
    max_date = parsed_dates.max()

    # 5. Quantity distribution & anomaly profiling
    q_numeric = pd.to_numeric(df["Quantity"], errors="coerce")
    q_invalid_count = int(q_numeric.isnull().sum())
    q_zero_count = int((q_numeric == 0).sum())
    q_negative_count = int((q_numeric < 0).sum())
    q_positive_count = int((q_numeric > 0).sum())

    q_stats = {
        "min": float(q_numeric.min()),
        "max": float(q_numeric.max()),
        "mean": float(q_numeric.mean()),
        "median": float(q_numeric.median()),
        "std": float(q_numeric.std()),
        "p25": float(q_numeric.quantile(0.25)),
        "p75": float(q_numeric.quantile(0.75)),
        "p99": float(q_numeric.quantile(0.99)),
        "negative_count": q_negative_count,
        "negative_pct": (q_negative_count / total_rows) * 100,
        "zero_count": q_zero_count,
        "positive_count": q_positive_count,
        "positive_pct": (q_positive_count / total_rows) * 100,
        "invalid_numeric_count": q_invalid_count
    }

    # 6. Price distribution & anomaly profiling
    p_numeric = pd.to_numeric(df["Price"], errors="coerce")
    p_invalid_count = int(p_numeric.isnull().sum())
    p_zero_count = int((p_numeric == 0).sum())
    p_negative_count = int((p_numeric < 0).sum())
    p_positive_count = int((p_numeric > 0).sum())

    p_stats = {
        "min": float(p_numeric.min()),
        "max": float(p_numeric.max()),
        "mean": float(p_numeric.mean()),
        "median": float(p_numeric.median()),
        "std": float(p_numeric.std()),
        "p25": float(p_numeric.quantile(0.25)),
        "p75": float(p_numeric.quantile(0.75)),
        "p99": float(p_numeric.quantile(0.99)),
        "negative_count": p_negative_count,
        "zero_count": p_zero_count,
        "positive_count": p_positive_count,
        "invalid_numeric_count": p_invalid_count
    }

    # 7. In-depth Cancellation ('C') & Return Analysis
    # Ensure invoice is treated as string
    invoice_str = df["Invoice"].astype(str).str.strip()
    is_cancellation = invoice_str.str.startswith("C", na=False)
    cancellation_count = int(is_cancellation.sum())
    cancellation_pct = (cancellation_count / total_rows) * 100

    # Cross-tabulate cancellation flag with negative quantities
    is_neg_qty = q_numeric < 0
    is_pos_qty = q_numeric > 0
    is_zero_qty = q_numeric == 0

    cancellation_and_neg_qty = int((is_cancellation & is_neg_qty).sum())
    cancellation_and_pos_qty = int((is_cancellation & is_pos_qty).sum())
    cancellation_and_zero_qty = int((is_cancellation & is_zero_qty).sum())

    neg_qty_without_c = int((is_neg_qty & (~is_cancellation)).sum())

    # Valid positive demand candidates: Quantity > 0, Price > 0, and not 'C'
    is_valid_sales = is_pos_qty & (p_numeric > 0) & (~is_cancellation)
    valid_sales_count = int(is_valid_sales.sum())
    valid_sales_pct = (valid_sales_count / total_rows) * 100

    # 8. Top SKUs by transaction frequency and gross quantity (among positive sales)
    valid_df = df[is_valid_sales].copy()
    valid_df["Quantity_num"] = q_numeric[is_valid_sales]
    
    top_skus_by_freq = (
        valid_df["StockCode"]
        .value_counts()
        .head(10)
        .reset_index()
    )
    top_skus_by_freq.columns = ["StockCode", "TransactionCount"]

    top_skus_by_qty = (
        valid_df.groupby("StockCode")["Quantity_num"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_skus_by_qty.columns = ["StockCode", "TotalQuantitySold"]

    return {
        "total_rows": total_rows,
        "total_cols": total_cols,
        "columns": df.columns.tolist(),
        "missing_summary": missing_summary,
        "duplicate_count": duplicate_count,
        "duplicate_pct": duplicate_pct,
        "unique_invoices": unique_invoices,
        "unique_stock_codes": unique_stock_codes,
        "unique_customers": unique_customers,
        "unique_countries": unique_countries,
        "countries_list": countries_list,
        "top_countries": top_countries,
        "min_date": str(min_date),
        "max_date": str(max_date),
        "invalid_dates_count": invalid_dates_count,
        "quantity_stats": q_stats,
        "price_stats": p_stats,
        "cancellation_count": cancellation_count,
        "cancellation_pct": cancellation_pct,
        "cancellation_and_neg_qty": cancellation_and_neg_qty,
        "cancellation_and_pos_qty": cancellation_and_pos_qty,
        "cancellation_and_zero_qty": cancellation_and_zero_qty,
        "neg_qty_without_c": neg_qty_without_c,
        "valid_sales_count": valid_sales_count,
        "valid_sales_pct": valid_sales_pct,
        "top_skus_by_freq": top_skus_by_freq,
        "top_skus_by_qty": top_skus_by_qty
    }


def generate_eda_report(metrics: Dict[str, Any], output_dir: Optional[Path] = None) -> Path:
    """Generates a structured markdown report and summary CSV tables.
    
    Args:
        metrics: Dictionary returned by explore_dataset().
        output_dir: Destination directory. Defaults to backend/ml/data/processed/.
        
    Returns:
        Path: Filepath to the generated eda_report.md.
    """
    target_dir = output_dir or get_default_processed_data_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    report_path = target_dir / "eda_report.md"

    # Export supporting CSV summaries
    metrics["missing_summary"].to_csv(target_dir / "eda_missing_summary.csv", index=False)
    metrics["top_skus_by_freq"].to_csv(target_dir / "eda_top_skus_by_frequency.csv", index=False)
    metrics["top_skus_by_qty"].to_csv(target_dir / "eda_top_skus_by_quantity.csv", index=False)

    q = metrics["quantity_stats"]
    p = metrics["price_stats"]

    # Construct clean markdown report
    markdown_content = f"""# NEXORA — Exploratory Data Analysis (EDA) Report
**Dataset:** UCI Online Retail II (`online_retail_II.csv`)  
**Generated Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Module:** Phase 1, Task 1 — Data Ingestion & Statistical Exploration

---

## 1. Executive Summary & Dataset Dimensions

- **Total Transaction Rows:** {metrics['total_rows']:,}
- **Total Columns:** {metrics['total_cols']}
- **Temporal Range:** {metrics['min_date']} to {metrics['max_date']}
- **Duplicate Rows:** {metrics['duplicate_count']:,} ({metrics['duplicate_pct']:.2f}%)
- **Unique Invoices:** {metrics['unique_invoices']:,}
- **Unique Products (StockCode):** {metrics['unique_stock_codes']:,}
- **Unique Customers:** {metrics['unique_customers']:,} (excluding nulls)
- **Countries Represented:** {metrics['unique_countries']}

---

## 2. Column Profiles & Missing-Value Analysis

| Column Name | Data Type | Missing Count | Missing Percentage | Interpretation |
| :--- | :--- | :---: | :---: | :--- |
"""

    for _, row in metrics["missing_summary"].iterrows():
        col = row["column"]
        dtype = row["dtype"]
        m_cnt = row["missing_count"]
        m_pct = row["missing_percentage"]
        
        note = "Fully populated"
        if col == "Customer ID":
            note = "High missing rate; customer-level features cannot be universal"
        elif col == "Description":
            note = "Minor missing names; fallback to StockCode required"
        elif m_cnt > 0:
            note = f"Contains {m_cnt} null values"

        markdown_content += f"| `{col}` | `{dtype}` | {m_cnt:,} | {m_pct:.2f}% | {note} |\n"

    markdown_content += f"""
---

## 3. Transaction Stream Classification & Integrity Analysis

NEXORA strictly segregates gross demand from post-purchase friction (cancellations and returns):

| Transaction Category | Record Count | % of Total Dataset | Handling Rule in NEXORA |
| :--- | :---: | :---: | :--- |
| **Gross Positive Sales** (`Qty > 0`, `Price > 0`, no 'C') | **{metrics['valid_sales_count']:,}** | **{metrics['valid_sales_pct']:.2f}%** | **Used exclusively for training demand forecasting models.** |
| **Invoice Cancellations** (`Invoice` starts with 'C') | **{metrics['cancellation_count']:,}** | **{metrics['cancellation_pct']:.2f}%** | Tracked in Module 9 & 10 (Product Health & Anomaly Alerts). |
| **Returns without 'C'** (`Qty < 0` & no 'C') | **{metrics['neg_qty_without_c']:,}** | **{(metrics['neg_qty_without_c'] / metrics['total_rows']) * 100:.2f}%** | Credit adjustments and inventory restocks tracked in Module 9. |
| **Zero Quantities** (`Qty == 0`) | **{q['zero_count']:,}** | **{(q['zero_count'] / metrics['total_rows']) * 100:.2f}%** | Informational or administrative entries; filtered from demand. |
| **Zero / Negative Prices** (`Price <= 0`) | **{p['zero_count'] + p['negative_count']:,}** | **{((p['zero_count'] + p['negative_count']) / metrics['total_rows']) * 100:.2f}%** | Administrative adjustments, gifts, or errors; filtered from demand. |

### Cancellation & Negative Quantity Verification
- **Invoices starting with 'C' having negative quantity:** {metrics['cancellation_and_neg_qty']:,}
- **Invoices starting with 'C' having positive quantity:** {metrics['cancellation_and_pos_qty']:,}
- **Invoices starting with 'C' having zero quantity:** {metrics['cancellation_and_zero_qty']:,}
- **Negative quantity records WITHOUT 'C' prefix:** {metrics['neg_qty_without_c']:,}

> [!NOTE]
> **Key Finding:** While virtually all 'C' invoices have negative quantities, there are records with negative quantities that lack the 'C' prefix. NEXORA correctly avoids assuming that every negative quantity is a cancellation.

---

## 4. Quantity Distribution

- **Minimum Quantity:** {q['min']:,} (extreme return or cancellation)
- **25th Percentile (P25):** {q['p25']}
- **Median (P50):** {q['median']}
- **Mean:** {q['mean']:.2f}
- **75th Percentile (P75):** {q['p75']}
- **99th Percentile (P99):** {q['p99']}
- **Maximum Quantity:** {q['max']:,} (bulk wholesale order)
- **Standard Deviation:** {q['std']:.2f}

---

## 5. Price Distribution

- **Minimum Price:** £{p['min']:.2f}
- **25th Percentile (P25):** £{p['p25']:.2f}
- **Median (P50):** £{p['median']:.2f}
- **Mean:** £{p['mean']:.2f}
- **75th Percentile (P75):** £{p['p75']:.2f}
- **99th Percentile (P99):** £{p['p99']:.2f}
- **Maximum Price:** £{p['max']:.2f}
- **Standard Deviation:** £{p['std']:.2f}

---

## 6. Top Countries by Transaction Volume

| Country | Transaction Count | % of Total |
| :--- | :---: | :---: |
"""

    for country, count in metrics["top_countries"].items():
        pct = (count / metrics["total_rows"]) * 100
        markdown_content += f"| {country} | {count:,} | {pct:.2f}% |\n"

    markdown_content += f"""
---

## 7. Top SKUs by Demand Frequency & Volume (Positive Sales Only)

### Top 10 Most Frequently Purchased SKUs
| StockCode | Transaction Frequency |
| :--- | :---: |
"""
    for _, row in metrics["top_skus_by_freq"].iterrows():
        markdown_content += f"| `{row['StockCode']}` | {row['TransactionCount']:,} |\n"

    markdown_content += f"""
### Top 10 SKUs by Total Quantity Sold
| StockCode | Total Quantity Sold (Units) |
| :--- | :---: |
"""
    for _, row in metrics["top_skus_by_qty"].iterrows():
        markdown_content += f"| `{row['StockCode']}` | {row['TotalQuantitySold']:,} |\n"

    markdown_content += f"""
---

## 8. Data-Quality & Modeling Implications for Phase 1

1. **Missing Customer IDs:** Approximately 24% of transactions lack a `Customer ID`. Because product demand aggregation occurs at the daily `StockCode` level, missing customer IDs will not hinder demand forecasting models.
2. **Duplicate Rows:** {metrics['duplicate_count']:,} duplicate rows exist in the raw dataset. Preprocessing will define whether duplicate transactions represent identical repeated checkout items or genuine double logging.
3. **Extreme Outliers:** Heavy tails exist in Quantity (from {q['min']} to {q['max']}) and Price (up to £{p['max']}). Robust metrics like MAE and WAPE will be necessary during model evaluation to prevent undue distortion by extreme bulk transactions.
4. **Sparse Product Activity:** Many SKUs trade intermittently. In Phase 1 Task 3, daily time-series aggregation must generate continuous calendar days and impute missing product-days with `0` demand.
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"[NEXORA EDA] Report successfully written to: {report_path}")
    return report_path


def run_eda_pipeline(raw_csv_path: Optional[str] = None) -> Dict[str, Any]:
    """Orchestrates end-to-end data loading, exploration, and report generation."""
    df = load_raw_data(raw_csv_path)
    metrics = explore_dataset(df)
    generate_eda_report(metrics)
    return metrics


if __name__ == "__main__":
    print("=== NEXORA Phase 1 Task 1: Dataset Exploration Pipeline ===")
    run_eda_pipeline()

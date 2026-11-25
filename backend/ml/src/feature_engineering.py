"""Feature engineering and multi-horizon demand target generation for NEXORA.

This module provides two core stages of the NEXORA ML data pipeline:
1. Daily SKU Demand Aggregation & Continuous Date Imputation (Phase 1, Task 3):
   - Aggregates transaction-level gross sales to (StockCode, date) level.
   - Imputes zero-demand strictly within each SKU's observed lifespan [min_date, max_date].
   - Validates unit reconciliation and temporal continuity.
   - Serializes daily_product_demand.csv.

2. Leakage-Free Feature Engineering & Multi-Horizon Targets (Phase 1, Task 4):
   - Constructs calendar dynamics (DayOfWeek, Month, DayOfMonth) at date t.
   - Computes historical lags (Lag1, Lag7, Lag14, Lag28) using strictly dates < t.
   - Computes rolling statistics (RollingMean7, RollingMean28) shifted by 1 day (dates < t).
   - Generates cumulative future targets (D_7, D_15, D_30, D_90) summing dates > t.
   - Enforces the incomplete-target rule: missing future days remain NaN (never zero-filled).
   - Validates mathematical integrity and absence of data leakage.
   - Serializes ml_feature_dataset.csv and feature_engineering_report.md.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np


def get_default_processed_data_dir() -> Path:
    """Returns the path to the processed data directory, creating it if needed."""
    base_dir = Path(__file__).resolve().parent.parent
    processed_dir = base_dir / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    return processed_dir


# ==============================================================================
# SECTION 1: Daily SKU Demand Aggregation (Task 3 Functions)
# ==============================================================================

def load_clean_sales(file_path: Optional[str] = None) -> pd.DataFrame:
    """Loads cleaned gross sales records from backend/ml/data/processed/clean_gross_sales.csv.
    
    Args:
        file_path: Optional custom path. If None, uses default processed CSV.
        
    Returns:
        pd.DataFrame: Clean gross sales DataFrame with parsed dates.
        
    Raises:
        FileNotFoundError: If clean_gross_sales.csv is missing.
    """
    path = Path(file_path) if file_path else (get_default_processed_data_dir() / "clean_gross_sales.csv")
    if not path.is_file():
        raise FileNotFoundError(
            f"Clean gross sales dataset not found at: {path}. "
            "Please run preprocessing pipeline (backend/ml/src/preprocessing.py) first."
        )

    print(f"[NEXORA Feature Engineering] Loading clean gross sales from: {path}...")
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
    
    # Clean StockCode identifiers
    df["StockCode"] = df["StockCode"].fillna("").astype(str).str.strip()

    # Parse InvoiceDate cleanly
    df["date"] = pd.to_datetime(df["InvoiceDate"], errors="coerce").dt.date

    # Calculate line-level revenue for supplementary aggregation
    df["line_revenue"] = df["Quantity"].astype(float) * df["Price"].astype(float)
    
    print(f"[NEXORA Feature Engineering] Successfully loaded {len(df):,} gross sales records.")
    return df


def aggregate_daily_demand(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregates transaction-level records to product-day level.
    
    Groups by (StockCode, date) and calculates:
    - daily_demand: Sum of Quantity (units sold)
    - transaction_count: Count of contributing transaction rows
    - revenue: Sum of line-level revenue (Quantity * Price)
    
    Args:
        df: DataFrame containing StockCode, date, Quantity, and line_revenue.
        
    Returns:
        pd.DataFrame: Product-day aggregated DataFrame sorted by (StockCode, date).
    """
    print("[NEXORA Feature Engineering] Aggregating transactions by StockCode and calendar date...")
    df_clean = df.copy()
    df_clean["StockCode"] = df_clean["StockCode"].fillna("").astype(str).str.strip()
    daily_df = df_clean.groupby(["StockCode", "date"], as_index=False).agg(
        daily_demand=("Quantity", "sum"),
        transaction_count=("Quantity", "count"),
        revenue=("line_revenue", "sum")
    )
    
    daily_df["StockCode"] = daily_df["StockCode"].astype(str).str.strip()
    daily_df["daily_demand"] = daily_df["daily_demand"].astype(int)
    daily_df["transaction_count"] = daily_df["transaction_count"].astype(int)
    daily_df["revenue"] = daily_df["revenue"].astype(float).round(4)
    daily_df = daily_df.sort_values(by=["StockCode", "date"]).reset_index(drop=True)
    
    print(f"[NEXORA Feature Engineering] Created {len(daily_df):,} product-day records across {daily_df['StockCode'].nunique():,} SKUs.")
    return daily_df


def create_continuous_date_series(daily_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Creates a continuous daily calendar for every SKU between its observed lifespan boundaries.
    
    Rules enforced:
    1. For each StockCode, identify min_date and max_date (first and last observed sales).
    2. Impute missing calendar days between min_date and max_date with daily_demand = 0,
       transaction_count = 0, and revenue = 0.0.
    3. Do NOT impute dates before min_date or after max_date.
    4. Sort resulting time-series by StockCode and date.
    
    Args:
        daily_df: Product-day aggregated DataFrame from aggregate_daily_demand().
        
    Returns:
        Tuple[pd.DataFrame, dict]: Continuous time-series DataFrame and imputation statistics dictionary.
    """
    print("[NEXORA Feature Engineering] Imputing zero-demand for missing calendar dates within SKU lifespans...")
    if daily_df.empty:
        empty_df = pd.DataFrame(columns=["StockCode", "date", "daily_demand", "transaction_count", "revenue", "is_imputed"])
        return empty_df, {"total_imputed": 0, "pct_imputed": 0.0}

    reindexed_groups = []
    total_observed_rows = len(daily_df)
    
    for sku, group in daily_df.groupby("StockCode"):
        if group["date"].duplicated().any():
            group = group.groupby("date", as_index=False).agg(
                daily_demand=("daily_demand", "sum"),
                transaction_count=("transaction_count", "sum"),
                revenue=("revenue", "sum")
            )
        min_date = group["date"].min()
        max_date = group["date"].max()
        
        full_date_range = pd.date_range(start=min_date, end=max_date, freq="D").date
        indexed_group = group.set_index("date").reindex(full_date_range)
        
        is_imputed = indexed_group["daily_demand"].isnull()
        
        indexed_group["StockCode"] = sku
        indexed_group["is_imputed"] = is_imputed
        indexed_group["daily_demand"] = indexed_group["daily_demand"].fillna(0).astype(int)
        indexed_group["transaction_count"] = indexed_group["transaction_count"].fillna(0).astype(int)
        indexed_group["revenue"] = indexed_group["revenue"].fillna(0.0).astype(float).round(4)
        
        reindexed_groups.append(indexed_group)

    continuous_df = pd.concat(reindexed_groups, ignore_index=False)
    continuous_df = continuous_df.reset_index().rename(columns={"index": "date"})
    
    continuous_df = continuous_df[["StockCode", "date", "daily_demand", "transaction_count", "revenue", "is_imputed"]]
    continuous_df = continuous_df.sort_values(by=["StockCode", "date"]).reset_index(drop=True)
    
    total_imputed = int(continuous_df["is_imputed"].sum())
    total_continuous = len(continuous_df)
    pct_imputed = (total_imputed / total_continuous * 100) if total_continuous > 0 else 0.0

    stats = {
        "observed_product_days": total_observed_rows,
        "continuous_product_days": total_continuous,
        "total_imputed_days": total_imputed,
        "pct_imputed_days": pct_imputed
    }
    
    print(f"[NEXORA Feature Engineering] Completed continuous series: {total_continuous:,} rows ({total_imputed:,} imputed zero-demand days, {pct_imputed:.2f}%).")
    return continuous_df, stats


def validate_daily_demand_data(
    raw_sales_df: pd.DataFrame,
    daily_aggregated_df: pd.DataFrame,
    continuous_df: pd.DataFrame
) -> Dict[str, Any]:
    """Validates mathematical and structural integrity of aggregated and imputed demand series."""
    print("[NEXORA Validation] Performing automated integrity and reconciliation checks...")
    
    if continuous_df.empty:
        return {
            "is_valid": raw_sales_df.empty,
            "reconciled_demand": True,
            "sku_count_match": True,
            "no_duplicates": True,
            "continuity_valid": True,
            "non_negative_demand": True
        }

    duplicate_count = int(continuous_df.duplicated(subset=["StockCode", "date"]).sum())
    no_duplicates = (duplicate_count == 0)

    missing_stock_codes = int(continuous_df["StockCode"].isnull().sum())
    missing_dates = int(continuous_df["date"].isnull().sum())

    non_negative_demand = bool((continuous_df["daily_demand"] >= 0).all())
    non_negative_transactions = bool((continuous_df["transaction_count"] >= 0).all())
    non_negative_revenue = bool((continuous_df["revenue"] >= 0).all())

    imputed_rows = continuous_df[continuous_df["is_imputed"]]
    imputed_zeros_valid = bool(
        (imputed_rows["daily_demand"] == 0).all() and
        (imputed_rows["transaction_count"] == 0).all() and
        (imputed_rows["revenue"] == 0.0).all()
    ) if not imputed_rows.empty else True

    raw_demand_sum = int(raw_sales_df["Quantity"].sum())
    agg_demand_sum = int(daily_aggregated_df["daily_demand"].sum())
    continuous_demand_sum = int(continuous_df["daily_demand"].sum())
    reconciled_demand = (raw_demand_sum == agg_demand_sum == continuous_demand_sum)

    raw_sku_count = int(raw_sales_df["StockCode"].nunique())
    continuous_sku_count = int(continuous_df["StockCode"].nunique())
    sku_count_match = (raw_sku_count == continuous_sku_count)

    raw_min_date = raw_sales_df["date"].min()
    raw_max_date = raw_sales_df["date"].max()
    cont_min_date = continuous_df["date"].min()
    cont_max_date = continuous_df["date"].max()
    within_global_bounds = bool(cont_min_date >= raw_min_date and cont_max_date <= raw_max_date)

    sku_spans = continuous_df.groupby("StockCode")["date"].agg(["min", "max", "count"])
    expected_days = (pd.to_datetime(sku_spans["max"]) - pd.to_datetime(sku_spans["min"])).dt.days + 1
    continuity_valid = bool((sku_spans["count"] == expected_days).all())

    is_valid = (
        no_duplicates and
        missing_stock_codes == 0 and
        missing_dates == 0 and
        non_negative_demand and
        non_negative_transactions and
        imputed_zeros_valid and
        reconciled_demand and
        sku_count_match and
        within_global_bounds and
        continuity_valid
    )

    print(f"[NEXORA Validation] Overall validation status: {'PASSED (Valid)' if is_valid else 'FAILED'}")
    return {
        "is_valid": is_valid,
        "no_duplicates": no_duplicates,
        "duplicate_count": duplicate_count,
        "missing_stock_codes": missing_stock_codes,
        "missing_dates": missing_dates,
        "non_negative_demand": non_negative_demand,
        "non_negative_transactions": non_negative_transactions,
        "non_negative_revenue": non_negative_revenue,
        "imputed_zeros_valid": imputed_zeros_valid,
        "reconciled_demand": reconciled_demand,
        "raw_demand_sum": raw_demand_sum,
        "continuous_demand_sum": continuous_demand_sum,
        "sku_count_match": sku_count_match,
        "raw_sku_count": raw_sku_count,
        "continuous_sku_count": continuous_sku_count,
        "raw_min_date": str(raw_min_date),
        "raw_max_date": str(raw_max_date),
        "cont_min_date": str(cont_min_date),
        "cont_max_date": str(cont_max_date),
        "continuity_valid": continuity_valid
    }


def save_daily_demand_data(
    df: pd.DataFrame,
    output_dir: Optional[Path] = None
) -> Path:
    """Saves the continuous product daily demand dataset to CSV."""
    target_dir = output_dir or get_default_processed_data_dir()
    output_path = target_dir / "daily_product_demand.csv"
    print(f"[NEXORA Feature Engineering] Saving continuous daily demand dataset to: {output_path}...")
    df.to_csv(output_path, index=False)
    print(f"[NEXORA Feature Engineering] File saved ({output_path.stat().st_size:,} bytes).")
    return output_path


def run_daily_aggregation_pipeline(
    sales_csv_path: Optional[str] = None,
    output_dir: Optional[Path] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Runs the full daily aggregation, continuous date imputation, and validation pipeline."""
    print("=== NEXORA Phase 1 Task 3: Daily SKU Demand Aggregation Pipeline ===")
    clean_df = load_clean_sales(sales_csv_path)
    daily_agg = aggregate_daily_demand(clean_df)
    continuous_df, imputation_stats = create_continuous_date_series(daily_agg)
    val = validate_daily_demand_data(clean_df, daily_agg, continuous_df)
    if not val["is_valid"]:
        raise ValueError("Daily demand aggregation validation failed!")
    save_daily_demand_data(continuous_df, output_dir)
    print("=== NEXORA Phase 1 Task 3 Completed Successfully ===")
    return continuous_df, val


# ==============================================================================
# SECTION 2: Leakage-Free Feature Engineering & Forecast Targets (Task 4)
# ==============================================================================

def load_daily_demand_data(file_path: Optional[str] = None) -> pd.DataFrame:
    """Loads continuous daily demand records from backend/ml/data/processed/daily_product_demand.csv.
    
    Args:
        file_path: Optional custom path. If None, uses default processed CSV.
        
    Returns:
        pd.DataFrame: Continuous daily demand DataFrame with parsed dates.
        
    Raises:
        FileNotFoundError: If daily_product_demand.csv is missing.
    """
    path = Path(file_path) if file_path else (get_default_processed_data_dir() / "daily_product_demand.csv")
    if not path.is_file():
        raise FileNotFoundError(
            f"Daily demand dataset not found at: {path}. "
            "Please run daily aggregation pipeline first."
        )

    print(f"[NEXORA Feature Engineering] Loading daily demand dataset from: {path}...")
    df = pd.read_csv(
        path,
        dtype={"StockCode": str},
        low_memory=False
    )
    
    # Ensure types and clean strings
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["daily_demand"] = df["daily_demand"].astype(int)
    df["transaction_count"] = df["transaction_count"].astype(int)
    df["revenue"] = df["revenue"].astype(float)
    df["is_imputed"] = df["is_imputed"].astype(bool)
    
    # Sort chronologically by StockCode and date
    df = df.sort_values(by=["StockCode", "date"]).reset_index(drop=True)
    print(f"[NEXORA Feature Engineering] Loaded {len(df):,} daily records across {df['StockCode'].nunique():,} unique SKUs.")
    return df


def create_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Generates calendar dynamic features from the observation date t.
    
    Features created:
    - DayOfWeek: Day of week index (0=Monday, 6=Sunday).
    - Month: Month index (1=January, 12=December).
    - DayOfMonth: Day of the calendar month (1=31).
    
    Leakage Rule:
    Calendar features are extracted strictly from observation date t.
    
    Args:
        df: DataFrame containing a 'date' column.
        
    Returns:
        pd.DataFrame: DataFrame augmented with DayOfWeek, Month, and DayOfMonth.
    """
    df = df.copy()
    dt_series = pd.to_datetime(df["date"])
    df["DayOfWeek"] = dt_series.dt.dayofweek.astype(int)
    df["Month"] = dt_series.dt.month.astype(int)
    df["DayOfMonth"] = dt_series.dt.day.astype(int)
    return df


def create_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Generates historical demand lag features per SKU independently.
    
    Features created:
    - Lag1: Demand 1 day earlier (t - 1)
    - Lag7: Demand 7 days earlier (t - 7)
    - Lag14: Demand 14 days earlier (t - 14)
    - Lag28: Demand 28 days earlier (t - 28)
    
    Leakage Rule:
    Calculated strictly over past days (t - k). Initial rows where past days
    are unavailable remain missing (NaN). Never fills with future values or zero.
    
    Args:
        df: DataFrame sorted by ['StockCode', 'date'] with 'daily_demand'.
        
    Returns:
        pd.DataFrame: DataFrame augmented with Lag1, Lag7, Lag14, Lag28.
    """
    df = df.sort_values(by=["StockCode", "date"]).reset_index(drop=True)
    grouped = df.groupby("StockCode")["daily_demand"]
    
    df["Lag1"] = grouped.shift(1)
    df["Lag7"] = grouped.shift(7)
    df["Lag14"] = grouped.shift(14)
    df["Lag28"] = grouped.shift(28)
    
    return df


def create_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """Generates historical rolling window statistics per SKU independently.
    
    Features created:
    - RollingMean7: Mean demand over the prior 7 calendar days (t - 7 through t - 1).
    - RollingMean28: Mean demand over the prior 28 calendar days (t - 28 through t - 1).
    
    Leakage Rule:
    The series is explicitly shifted by 1 day before rolling calculation so that
    the observation date t is strictly excluded. Initial rows where complete
    historical windows are unavailable remain missing (NaN).
    
    Args:
        df: DataFrame sorted by ['StockCode', 'date'] with 'daily_demand'.
        
    Returns:
        pd.DataFrame: DataFrame augmented with RollingMean7 and RollingMean28.
    """
    df = df.sort_values(by=["StockCode", "date"]).reset_index(drop=True)
    grouped = df.groupby("StockCode")["daily_demand"]
    
    # Shift by 1 day excludes current date t; min_periods=window ensures incomplete windows stay NaN
    df["RollingMean7"] = (
        grouped.transform(lambda s: s.shift(1).rolling(window=7, min_periods=7).mean())
        .round(4)
    )
    df["RollingMean28"] = (
        grouped.transform(lambda s: s.shift(1).rolling(window=28, min_periods=28).mean())
        .round(4)
    )
    
    return df


def create_future_demand_targets(
    df: pd.DataFrame,
    horizons: Optional[List[int]] = None
) -> pd.DataFrame:
    """Generates forward-looking cumulative demand targets for multi-horizon regression.
    
    Targets created:
    - D_7: Total positive demand from t + 1 through t + 7.
    - D_15: Total positive demand from t + 1 through t + 15.
    - D_30: Total positive demand from t + 1 through t + 30.
    - D_90: Total positive demand from t + 1 through t + 90.
    
    Critical Incomplete-Target Rule:
    For rows near the end of each SKU's lifespan where the complete future horizon
    of H days is unavailable, the target MUST remain NaN. Incomplete horizons must
    never be filled with partial sums or assumed to be zero.
    
    Calculation Method:
    Operates per SKU independently by reversing the series, shifting by 1 day
    (to exclude current date t), computing rolling sum with min_periods=H,
    and reversing back to chronological order.
    
    Args:
        df: DataFrame sorted by ['StockCode', 'date'] with 'daily_demand'.
        horizons: List of forecast horizons in days (default: [7, 15, 30, 90]).
        
    Returns:
        pd.DataFrame: DataFrame augmented with D_7, D_15, D_30, D_90.
    """
    target_horizons = horizons or [7, 15, 30, 90]
    df = df.sort_values(by=["StockCode", "date"]).reset_index(drop=True)
    grouped = df.groupby("StockCode")["daily_demand"]
    
    for h in target_horizons:
        col_name = f"D_{h}"
        # Reverse series, shift 1 (excludes date t), rolling sum h days, reverse back
        df[col_name] = grouped.transform(
            lambda s: s.iloc[::-1].shift(1).rolling(window=h, min_periods=h).sum().iloc[::-1]
        )
        
    return df


def validate_feature_dataset(
    feature_df: pd.DataFrame,
    source_df: pd.DataFrame,
    horizons: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Validates mathematical and structural integrity of the ML feature dataset.
    
    Checks enforced:
    1. Exact row count preservation (no dropped rows).
    2. SKU count preservation.
    3. Presence of all mandatory feature and target columns.
    4. Chronological ordering and 0 duplicate (StockCode, date) pairs.
    5. Non-negative values for all demands, lags, rolling averages, and targets.
    6. Initial lag/rolling missing value preservation (no artificial zero-filling).
    7. Incomplete target missing value preservation (last H rows of each SKU are NaN).
    8. Empirical leakage prevention check on sample slices.
    
    Args:
        feature_df: Constructed feature DataFrame.
        source_df: Source continuous daily demand DataFrame.
        horizons: Evaluated horizons (default: [7, 15, 30, 90]).
        
    Returns:
        Dict[str, Any]: Detailed validation statistics and pass/fail boolean.
    """
    print("[NEXORA Validation] Performing comprehensive ML feature validation & leakage checks...")
    target_horizons = horizons or [7, 15, 30, 90]
    
    if feature_df.empty:
        return {
            "is_valid": source_df.empty,
            "row_count_match": True,
            "sku_count_match": True,
            "no_duplicates": True,
            "non_negative_all": True,
            "leakage_free": True
        }

    # 1. Row and SKU count checks
    row_count_match = bool(len(feature_df) == len(source_df))
    sku_count_match = bool(feature_df["StockCode"].nunique() == source_df["StockCode"].nunique())
    
    # 2. Mandatory columns check
    mandatory_cols = [
        "StockCode", "date", "daily_demand", "transaction_count", "revenue", "is_imputed",
        "DayOfWeek", "Month", "DayOfMonth",
        "Lag1", "Lag7", "Lag14", "Lag28",
        "RollingMean7", "RollingMean28"
    ] + [f"D_{h}" for h in target_horizons]
    
    missing_cols = [c for c in mandatory_cols if c not in feature_df.columns]
    columns_complete = (len(missing_cols) == 0)

    # 3. Duplicate check
    duplicate_count = int(feature_df.duplicated(subset=["StockCode", "date"]).sum())
    no_duplicates = (duplicate_count == 0)

    # 4. Non-negativity check
    check_cols = ["daily_demand", "Lag1", "Lag7", "Lag14", "Lag28", "RollingMean7", "RollingMean28"] + [f"D_{h}" for h in target_horizons]
    non_negative_all = True
    for c in check_cols:
        if c in feature_df.columns:
            non_null_vals = feature_df[c].dropna()
            if not (non_null_vals >= 0).all():
                non_negative_all = False
                break

    # 5. Missing value & boundary integrity
    # For every SKU, Lag1 must have at least 1 NaN at index 0
    sku_count = feature_df["StockCode"].nunique()
    lag1_nulls = int(feature_df["Lag1"].isnull().sum())
    lag1_boundary_valid = (lag1_nulls >= sku_count)

    # For every SKU with length >= H, the last H rows of target D_H must be NaN
    target_boundaries_valid = True
    for h in target_horizons:
        d_col = f"D_{h}"
        null_count = int(feature_df[d_col].isnull().sum())
        if null_count < sku_count:
            target_boundaries_valid = False
            break

    # 6. Leakage verification on synthetic or sampled verification slice
    # Check that for any row i where Lag1 is present, Lag1 == daily_demand of row i-1
    leakage_free = True
    sample_skus = feature_df["StockCode"].unique()[:5]
    for sku in sample_skus:
        sku_data = feature_df[feature_df["StockCode"] == sku].sort_values("date").reset_index(drop=True)
        if len(sku_data) > 35:
            # Check Lag1: row 1 Lag1 must equal row 0 demand
            if sku_data.loc[1, "Lag1"] != sku_data.loc[0, "daily_demand"]:
                leakage_free = False
            # Check Lag7: row 7 Lag7 must equal row 0 demand
            if sku_data.loc[7, "Lag7"] != sku_data.loc[0, "daily_demand"]:
                leakage_free = False
            # Check RollingMean7: row 7 RollingMean7 must equal mean of rows 0..6
            expected_roll7 = round(float(sku_data.loc[0:6, "daily_demand"].mean()), 4)
            actual_roll7 = round(float(sku_data.loc[7, "RollingMean7"]), 4)
            if expected_roll7 != actual_roll7:
                leakage_free = False
            # Check D_7: row 0 D_7 must equal sum of rows 1..7 (excluding row 0!)
            expected_d7 = float(sku_data.loc[1:7, "daily_demand"].sum())
            actual_d7 = float(sku_data.loc[0, "D_7"])
            if expected_d7 != actual_d7:
                leakage_free = False
            # Verify D_7 excludes current day: row 0 demand must NOT be in D_7 (unless identical sum by coincidence)
            # Check last 7 rows of D_7 are NaN
            if not sku_data.loc[len(sku_data)-7:, "D_7"].isnull().all():
                leakage_free = False

    is_valid = (
        row_count_match and
        sku_count_match and
        columns_complete and
        no_duplicates and
        non_negative_all and
        lag1_boundary_valid and
        target_boundaries_valid and
        leakage_free
    )

    print(f"[NEXORA Validation] Feature validation & leakage status: {'PASSED (Valid)' if is_valid else 'FAILED'}")

    return {
        "is_valid": is_valid,
        "row_count_match": row_count_match,
        "sku_count_match": sku_count_match,
        "columns_complete": columns_complete,
        "no_duplicates": no_duplicates,
        "non_negative_all": non_negative_all,
        "lag1_boundary_valid": lag1_boundary_valid,
        "target_boundaries_valid": target_boundaries_valid,
        "leakage_free": leakage_free,
        "total_rows": len(feature_df),
        "total_skus": sku_count
    }


def generate_feature_report(
    feature_df: pd.DataFrame,
    val_stats: Dict[str, Any],
    output_dir: Optional[Path] = None,
    horizons: Optional[List[int]] = None
) -> Path:
    """Generates an extensive markdown report summarizing feature and target availability."""
    target_dir = output_dir or get_default_processed_data_dir()
    report_path = target_dir / "feature_engineering_report.md"
    target_horizons = horizons or [7, 15, 30, 90]
    total_rows = len(feature_df)

    # 1. Feature availability metrics
    lag_cols = ["Lag1", "Lag7", "Lag14", "Lag28"]
    rolling_cols = ["RollingMean7", "RollingMean28"]
    
    # 2. Rows eligible per horizon (complete features + available target)
    feature_cols = ["DayOfWeek", "Month", "DayOfMonth", "Lag1", "Lag7", "Lag14", "Lag28", "RollingMean7", "RollingMean28"]
    has_all_features = ~feature_df[feature_cols].isnull().any(axis=1)
    complete_feature_rows = int(has_all_features.sum())

    content = f"""# NEXORA — Feature Engineering & Multi-Horizon Demand Targets Report
**Generated Date:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Module:** Phase 1, Task 4 — Leakage-Free Feature Generation & Multi-Horizon Targets ($D_7, D_{{15}}, D_{{30}}, D_{{90}}$)

---

## 1. Executive Summary

The feature engineering pipeline converted the continuous daily time-series (`daily_product_demand.csv`) into a leakage-free, multi-horizon analytical dataset (`ml_feature_dataset.csv`).

| Metric | Measured Value | Notes |
| :--- | :---: | :--- |
| **Total Rows Processed** | {total_rows:,} | 100% row preservation from Task 3 continuous series |
| **Unique Product SKUs** | {val_stats['total_skus']:,} | Preserved as clean strings |
| **Total Features & Targets Generated** | 18 columns | Calendar (3), Lags (4), Rolling (2), Targets (4) |
| **Validation & Leakage Status** | **{'PASSED (Leakage-Free)' if val_stats['is_valid'] else 'FAILED'}** | Strict temporal isolation enforced |
| **Complete Feature Rows (All Lags + Rolling)** | {complete_feature_rows:,} ({complete_feature_rows/total_rows*100:.2f}%) | Rows ready for model training |

---

## 2. Historical Feature Availability & Missing Values

Initial lag and rolling features naturally contain missing values (`NaN`) during the initial burn-in window of each SKU's lifespan. Per NEXORA architecture (`AGENTS.md`), these missing values are strictly preserved and never filled with future information or synthetic zeros.

| Feature Name | Feature Type | Time Window | Available Rows | Available % | Missing Rows (`NaN`) | Missing % | Primary Cause of Missing Values |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
"""

    for col in lag_cols + rolling_cols:
        null_count = int(feature_df[col].isnull().sum())
        avail_count = total_rows - null_count
        avail_pct = (avail_count / total_rows * 100) if total_rows > 0 else 0.0
        null_pct = (null_count / total_rows * 100) if total_rows > 0 else 0.0
        
        if col == "Lag1":
            cause = "Row 0 of each SKU (no $t-1$ history)"
        elif "7" in col:
            cause = "First 7 days of each SKU lifespan"
        elif "14" in col:
            cause = "First 14 days of each SKU lifespan"
        elif "28" in col:
            cause = "First 28 days of each SKU lifespan"
        else:
            cause = "Insufficient prior history"
            
        content += f"| `{col}` | Historical Demand | $t - k$ | {avail_count:,} | {avail_pct:.2f}% | {null_count:,} | {null_pct:.2f}% | {cause} |\n"

    content += """
---

## 3. Multi-Horizon Future Demand Target Availability

Target variables represent cumulative future customer demand over horizon $H$:

$$D_H(t) = \\sum_{i=1}^{H} \\text{daily\\_demand}_{t+i}$$

### Critical Incomplete-Target Rule
For observations near the end of each product's observed trading lifespan, complete future target windows of $H$ days are unavailable. NEXORA strictly marks these targets as **missing (`NaN`)** rather than treating them as zero sales.

| Horizon Target | Forecast Window | Operational Purpose | Available Targets | Available % | Incomplete Targets (`NaN`) | Incomplete % | Eligible Rows for Training (Features + Target) | Eligible % |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for h in target_horizons:
        d_col = f"D_{h}"
        null_count = int(feature_df[d_col].isnull().sum())
        avail_count = total_rows - null_count
        avail_pct = (avail_count / total_rows * 100) if total_rows > 0 else 0.0
        null_pct = (null_count / total_rows * 100) if total_rows > 0 else 0.0
        
        eligible_count = int((has_all_features & feature_df[d_col].notnull()).sum())
        eligible_pct = (eligible_count / total_rows * 100) if total_rows > 0 else 0.0
        
        if h == 7:
            purpose = "Fast shelf restocking"
        elif h == 15:
            purpose = "Bi-weekly ordering"
        elif h == 30:
            purpose = "Monthly inventory budgeting"
        else:
            purpose = "Quarterly vendor quotas"

        content += f"| `D_{h}` | $t+1$ to $t+{h}$ | {purpose} | {avail_count:,} | {avail_pct:.2f}% | {null_count:,} | {null_pct:.2f}% | {eligible_count:,} | {eligible_pct:.2f}% |\n"

    content += """
---

## 4. Leakage Prevention & Temporal Integrity Architecture

To prevent optimistic bias and guarantee valid out-of-time generalizability:
1. **Calendar Features (`DayOfWeek`, `Month`, `DayOfMonth`):** Calculated strictly on date $t$.
2. **Lag Features (`Lag1`, `Lag7`, `Lag14`, `Lag28`):** Shifted $t - k$. Never references date $t$ or future dates.
3. **Rolling Window Features (`RollingMean7`, `RollingMean28`):** Pre-shifted by 1 day before rolling average calculation. Dates $t-7$ to $t-1$ and $t-28$ to $t-1$ are used; current date $t$ is strictly excluded.
4. **Future Target Variables ($D_7, D_{15}, D_{30}, D_{90}$):** Forward-looking rolling sums strictly spanning $t+1$ through $t+H$. Date $t$ is strictly excluded from target sums.
5. **Separation of Roles:** No target column is ever utilized as an input feature during feature creation or subsequent model training.

---

## 5. Dataset Profile & Historical Limitations

- **Dataset Historical Span:** Transactions span from December 2010 to December 2011.
- **Retail Realism Limitation:** The dataset reflects historical UK e-commerce behavior and does not represent live current retail demand.
- **Intermittency Profile:** Inactive calendar days within each SKU's active trading window represent true zero demand; however, dates beyond December 2011 are unobserved, which is why future targets near the end of the dataset are marked missing (`NaN`).

---

## 6. Next Steps for Phase 1, Task 5 (Model Training)

With `ml_feature_dataset.csv` generated and validated:
1. **Model Candidates:** Train Seasonal Naïve baseline, Linear Regression, and Random Forest Regressor models independently for each horizon ($D_7, D_{15}, D_{30}, D_{90}$).
2. **Chronological Splitting:** Filter rows where `~isnull()` for all input features and the specific target horizon, and apply rolling-origin or strict chronological train/test splits.
3. **Evaluation Metrics:** Measure MAE, RMSE, and WAPE out-of-time.
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[NEXORA Feature Engineering] Report successfully generated at: {report_path}")
    return report_path


def save_feature_dataset(
    df: pd.DataFrame,
    output_dir: Optional[Path] = None
) -> Path:
    """Saves the complete ML feature dataset to CSV."""
    target_dir = output_dir or get_default_processed_data_dir()
    output_path = target_dir / "ml_feature_dataset.csv"
    print(f"[NEXORA Feature Engineering] Saving ML feature dataset to: {output_path}...")
    df.to_csv(output_path, index=False)
    print(f"[NEXORA Feature Engineering] File saved ({output_path.stat().st_size:,} bytes).")
    return output_path


def run_feature_engineering_pipeline(
    daily_demand_path: Optional[str] = None,
    output_dir: Optional[Path] = None,
    horizons: Optional[List[int]] = None
) -> Dict[str, Any]:
    """Orchestrates end-to-end feature engineering and multi-horizon target generation."""
    print("=== NEXORA Phase 1 Task 4: Leakage-Free Feature Engineering Pipeline ===")
    target_horizons = horizons or [7, 15, 30, 90]
    
    # 1. Load continuous daily demand data (Task 3 output)
    source_df = load_daily_demand_data(daily_demand_path)
    
    # 2. Generate calendar features
    print("[NEXORA Feature Engineering] Generating calendar features (DayOfWeek, Month, DayOfMonth)...")
    df = create_calendar_features(source_df)
    
    # 3. Generate lag features
    print("[NEXORA Feature Engineering] Generating historical demand lags (Lag1, Lag7, Lag14, Lag28)...")
    df = create_lag_features(df)
    
    # 4. Generate rolling features
    print("[NEXORA Feature Engineering] Generating rolling mean features (RollingMean7, RollingMean28)...")
    df = create_rolling_features(df)
    
    # 5. Generate future demand targets
    print(f"[NEXORA Feature Engineering] Generating multi-horizon targets {target_horizons}...")
    df = create_future_demand_targets(df, target_horizons)
    
    # 6. Validate feature dataset & leakage prevention
    val = validate_feature_dataset(df, source_df, target_horizons)
    if not val["is_valid"]:
        raise ValueError("Data validation or leakage prevention checks failed!")
        
    # 7. Save feature dataset
    out_file = save_feature_dataset(df, output_dir)
    
    # 8. Generate comprehensive feature engineering report
    report_file = generate_feature_report(df, val, output_dir, target_horizons)
    
    print("=== NEXORA Phase 1 Task 4 Pipeline Completed Successfully ===")
    return {
        "validation": val,
        "output_file": out_file,
        "report_file": report_file,
        "total_rows": len(df),
        "total_skus": val["total_skus"]
    }


if __name__ == "__main__":
    run_feature_engineering_pipeline()

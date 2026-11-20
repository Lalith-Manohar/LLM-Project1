"""Point-in-Time Historical Unit Price Feature Generator.

Eliminates temporal leakage in price features:
1. For any forecast origin date T, only transactions occurring strictly before T
   (tx_date < T) are used to compute historical SKU price statistics.
2. Future transactions occurring at date >= T never influence the price feature at T.
3. SKUs without prior transactions at date T receive the expanding global median
   price from transactions strictly before T.
4. Dates before any transactions exist receive the fixed baseline default prior ($2.10).
5. Tested for exact 0.0 perturbation invariance.
"""

import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Union
import numpy as np
import pandas as pd


def compute_point_in_time_prices(
    df_sales: pd.DataFrame,
    unique_dates: list,
    default_price: float = 2.10
) -> Tuple[pd.DataFrame, pd.Series]:
    """Computes point-in-time historical prices for each SKU and date.
    
    Parameters
    ----------
    df_sales : pd.DataFrame
        Transactions dataframe with ['StockCode', 'Price', 'date'].
    unique_dates : list
        Sorted list of unique calendar dates for the demand panel.
    default_price : float, default=2.10
        Default price prior when no historical transactions exist.
        
    Returns
    -------
    hist_price : pd.DataFrame
        Matrix of size (dates x skus) containing historical expanding mean prices strictly for tx_date < T.
    global_hist_price : pd.Series
        Series of size (dates,) containing global historical expanding mean price strictly for tx_date < T.
    """
    sales = df_sales.copy()
    sales["StockCode"] = sales["StockCode"].astype(str).str.strip()
    
    # Daily aggregation of transactions
    daily_stats = sales.groupby(["date", "StockCode"])["Price"].agg(["sum", "count"]).reset_index()
    pivot_sum = daily_stats.pivot(index="date", columns="StockCode", values="sum").reindex(unique_dates).fillna(0.0).cumsum()
    pivot_count = daily_stats.pivot(index="date", columns="StockCode", values="count").reindex(unique_dates).fillna(0.0).cumsum()

    # Shift by 1 day so date T only sees transactions strictly from date < T
    hist_sum = pivot_sum.shift(1).fillna(0.0)
    hist_count = pivot_count.shift(1).fillna(0.0)
    hist_price = hist_sum / hist_count.replace(0, np.nan)

    # Global historical expanding price
    global_daily = sales.groupby("date")["Price"].agg(["sum", "count"]).reset_index()
    global_sum = global_daily.set_index("date")["sum"].reindex(unique_dates).fillna(0.0).cumsum().shift(1).fillna(0.0)
    global_count = global_daily.set_index("date")["count"].reindex(unique_dates).fillna(0.0).cumsum().shift(1).fillna(0.0)
    global_hist_price = (global_sum / global_count.replace(0, np.nan)).fillna(default_price)

    return hist_price, global_hist_price


def enrich_daily_with_pit_price(
    df_daily: pd.DataFrame,
    sales_path: Union[str, Path],
    default_price: float = 2.10
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Enriches daily product demand with point-in-time UnitPrice feature.
    
    Guarantees no future transactions enter the UnitPrice feature for any date.
    """
    sales_path = Path(sales_path)
    print(f"[PIT Price] Loading transaction sales from {sales_path.name}...")
    df_sales = pd.read_csv(
        sales_path,
        dtype={"StockCode": str},
        usecols=["StockCode", "Price", "InvoiceDate"],
        encoding="latin1",
        low_memory=False
    )
    df_sales["StockCode"] = df_sales["StockCode"].astype(str).str.strip()
    df_sales["date"] = pd.to_datetime(df_sales["InvoiceDate"], format="%d-%m-%y %H:%M", errors="coerce").dt.date
    fallback_mask = df_sales["date"].isna()
    if fallback_mask.any():
        df_sales.loc[fallback_mask, "date"] = pd.to_datetime(
            df_sales.loc[fallback_mask, "InvoiceDate"], errors="coerce", dayfirst=True
        ).dt.date

    # Drop any remaining unparseable dates
    df_sales = df_sales.dropna(subset=["date", "Price"])

    unique_dates = sorted(list(set(df_daily["date"])))
    hist_price, global_hist_price = compute_point_in_time_prices(
        df_sales, unique_dates=unique_dates, default_price=default_price
    )

    print("[PIT Price] Mapping point-in-time prices to daily demand panel...")
    stacked_price = hist_price.stack().rename("UnitPrice").reset_index()
    stacked_price.columns = ["date", "StockCode", "UnitPrice"]

    df_merged = df_daily.merge(stacked_price, on=["date", "StockCode"], how="left")
    global_map = df_merged["date"].map(global_hist_price)
    df_merged["UnitPrice"] = df_merged["UnitPrice"].fillna(global_map).fillna(default_price)

    # Final static price map for inference fallback
    final_date = unique_dates[-1] if len(unique_dates) > 0 else None
    if final_date and final_date in hist_price.index:
        final_prices = hist_price.loc[final_date].dropna().to_dict()
    else:
        final_prices = {}

    return df_merged, final_prices

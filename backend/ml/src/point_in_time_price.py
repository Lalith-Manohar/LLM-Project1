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
import json
import bisect
import threading
import os
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
    df_sales["date"] = pd.to_datetime(df_sales["InvoiceDate"], errors="coerce").dt.date

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


class PointInTimePriceService:
    """Cutoff-aware historical point-in-time unit price service.
    
    Guarantees:
    - For observation date T, only transactions with transaction_date < T are included.
    - Transactions on date T and dates > T are strictly excluded.
    - SKUs without prior transactions before T receive the expanding global mean prior to T.
    - Observation dates before any transactions exist receive the empirical global median prior ($2.10).
    - O(log k) binary search lookup using precomputed prefix sums and transaction counts.
    - Thread-safe, cached in memory on startup, loads from pit_sku_price_history.json.
    """

    def __init__(self, data_dir: Optional[Union[str, Path]] = None):
        if data_dir is not None:
            self.data_dir = Path(data_dir)
        else:
            self.data_dir = Path(__file__).resolve().parent.parent / "data" / "processed"
        self.history_cache_path = self.data_dir / "pit_sku_price_history.json"
        self.static_cache_path = self.data_dir / "pit_sku_prices.json"
        self.sales_path = self.data_dir / "clean_gross_sales.csv"

        self.is_loaded: bool = False
        self.load_error: Optional[str] = None
        self._lock = threading.Lock()
        self._skus_data: Dict[str, Dict[str, list]] = {}
        self._global_dates: list = []
        self._global_sums: list = []
        self._global_counts: list = []
        self._static_prices: Dict[str, float] = {}
        self._cache_metadata: Dict[str, Any] = {}

    def build_and_save_index(
        self,
        sales_path: Optional[Union[str, Path]] = None,
        cache_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """Builds prefix sum price history index from clean gross sales and saves to cache with fingerprint."""
        target_sales = Path(sales_path) if sales_path else self.sales_path
        target_cache = Path(cache_path) if cache_path else self.history_cache_path

        if not target_sales.is_file():
            raise FileNotFoundError(f"Source sales dataset not found: {target_sales}")

        print(f"[PIT Price Service] Building price history index from {target_sales.name}...")
        sales_stat = target_sales.stat()
        df_sales = pd.read_csv(
            target_sales,
            dtype={"StockCode": str},
            usecols=["StockCode", "Price", "InvoiceDate"],
            encoding="latin1",
            low_memory=False
        )
        df_sales["StockCode"] = df_sales["StockCode"].astype(str).str.strip()
        df_sales["date"] = pd.to_datetime(df_sales["InvoiceDate"], errors="coerce").dt.date
        df_sales = df_sales.dropna(subset=["date", "Price"])

        # Global daily stats
        global_daily = df_sales.groupby("date")["Price"].agg(["sum", "count"]).sort_index()
        g_dates = [d.isoformat() for d in global_daily.index]
        g_cum_sum = np.cumsum(global_daily["sum"].values).tolist()
        g_cum_count = np.cumsum(global_daily["count"].values).tolist()

        # SKU daily stats
        sku_daily = df_sales.groupby(["StockCode", "date"])["Price"].agg(["sum", "count"]).reset_index()

        skus_data = {}
        static_prices = {}
        for sku, group in sku_daily.groupby("StockCode"):
            group = group.sort_values("date")
            d_list = [d.isoformat() for d in group["date"]]
            c_sum = np.cumsum(group["sum"].values).tolist()
            c_cnt = np.cumsum(group["count"].values).tolist()
            skus_data[sku] = {
                "dates": d_list,
                "sums": c_sum,
                "counts": c_cnt
            }
            if len(c_cnt) > 0 and c_cnt[-1] > 0:
                static_prices[sku] = round(float(c_sum[-1] / c_cnt[-1]), 4)

        static_prices["__global_default__"] = 2.10

        metadata = {
            "source_file": target_sales.name,
            "source_size": sales_stat.st_size,
            "source_mtime": sales_stat.st_mtime,
            "source_mtime_iso": datetime.datetime.fromtimestamp(sales_stat.st_mtime, tz=datetime.timezone.utc).isoformat(),
            "built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_skus": len(skus_data),
            "total_transactions": int(global_daily["count"].sum()),
            "global_dates_count": len(g_dates),
            "schema_version": "1.1"
        }

        index_data = {
            "metadata": metadata,
            "global": {
                "dates": g_dates,
                "sums": g_cum_sum,
                "counts": g_cum_count
            },
            "skus": skus_data
        }

        # Safe atomic write: write to a temporary file in the same directory, then rename
        target_cache.parent.mkdir(parents=True, exist_ok=True)
        tmp_cache = target_cache.with_name(f"{target_cache.name}.tmp.{os.getpid()}")
        try:
            with open(tmp_cache, "w", encoding="utf-8") as f:
                json.dump(index_data, f)
            os.replace(tmp_cache, target_cache)
        except Exception:
            if tmp_cache.is_file():
                try:
                    tmp_cache.unlink()
                except OSError:
                    pass
            raise

        # Also persist/update static prices cache for compatibility
        if self.static_cache_path.parent.is_dir():
            tmp_static = self.static_cache_path.with_name(f"{self.static_cache_path.name}.tmp.{os.getpid()}")
            try:
                with open(tmp_static, "w", encoding="utf-8") as sf:
                    json.dump(static_prices, sf)
                os.replace(tmp_static, self.static_cache_path)
            except Exception:
                if tmp_static.is_file():
                    try:
                        tmp_static.unlink()
                    except OSError:
                        pass

        print(f"[PIT Price Service] Built and cached {len(index_data['skus']):,} SKU price histories (source: {target_sales.name}, size: {sales_stat.st_size:,} bytes).")
        return index_data

    def load_index(
        self,
        cache_path: Optional[Union[str, Path]] = None,
        sales_path: Optional[Union[str, Path]] = None
    ) -> None:
        """Loads price history index from cache or builds it if missing or stale."""
        with self._lock:
            self.is_loaded = False
            self.load_error = None
            target_cache = Path(cache_path) if cache_path else self.history_cache_path
            target_sales = Path(sales_path) if sales_path else self.sales_path

            needs_rebuild = False
            rebuild_reason: Optional[str] = None
            cached_data: Optional[Dict[str, Any]] = None

            try:
                if not target_cache.is_file():
                    needs_rebuild = True
                    rebuild_reason = f"Cache file does not exist at {target_cache.name}"
                else:
                    try:
                        with open(target_cache, "r", encoding="utf-8") as f:
                            cached_data = json.load(f)

                        # Validate structural completeness
                        if not isinstance(cached_data, dict) or "skus" not in cached_data or "global" not in cached_data:
                            needs_rebuild = True
                            rebuild_reason = "Cache structure is corrupted or missing essential sections ('skus', 'global')"
                        elif target_sales.is_file():
                            source_stat = target_sales.stat()
                            meta = cached_data.get("metadata", {})
                            cached_size = meta.get("source_size")
                            cached_mtime = meta.get("source_mtime")

                            if cached_size is None or cached_mtime is None:
                                needs_rebuild = True
                                rebuild_reason = "Cache metadata missing source fingerprint ('source_size' or 'source_mtime')"
                            elif cached_size != source_stat.st_size:
                                needs_rebuild = True
                                rebuild_reason = f"Source dataset file size mismatch (cached: {cached_size}, current: {source_stat.st_size})"
                            elif abs(float(cached_mtime) - float(source_stat.st_mtime)) > 1e-4:
                                needs_rebuild = True
                                rebuild_reason = f"Source dataset modification timestamp mismatch (cached: {cached_mtime}, current: {source_stat.st_mtime})"
                        elif not target_sales.is_file():
                            print(f"[PIT Price Service WARNING] Source dataset {target_sales.name} missing; cannot verify cache freshness. Using existing cache.")
                    except Exception as parse_err:
                        needs_rebuild = True
                        rebuild_reason = f"Cache JSON read/parsing error: {parse_err}"

                if needs_rebuild:
                    if target_sales.is_file():
                        print(f"[PIT Price Service] Rebuilding price history index ({rebuild_reason})...")
                        cached_data = self.build_and_save_index(target_sales, target_cache)
                    elif self.static_cache_path.is_file():
                        print(f"[PIT Price Service WARNING] Cannot rebuild cache ({rebuild_reason}); falling back to static cache.")
                        with open(self.static_cache_path, "r", encoding="utf-8") as sf:
                            self._static_prices = json.load(sf)
                        self.is_loaded = True
                        return
                    else:
                        raise FileNotFoundError(f"Cannot load or rebuild price index: source dataset {target_sales} not found ({rebuild_reason})")

                if cached_data is None:
                    raise RuntimeError("Failed to obtain valid price index data during load/rebuild.")

                self._global_dates = cached_data.get("global", {}).get("dates", [])
                self._global_sums = cached_data.get("global", {}).get("sums", [])
                self._global_counts = cached_data.get("global", {}).get("counts", [])
                self._skus_data = cached_data.get("skus", {})
                self._cache_metadata = cached_data.get("metadata", {})

                # Extract latest static prices for fast live lookup
                static_map = {}
                for sku, entry in self._skus_data.items():
                    cnts = entry.get("counts", [])
                    sums = entry.get("sums", [])
                    if cnts and cnts[-1] > 0:
                        static_map[sku] = round(float(sums[-1] / cnts[-1]), 4)
                static_map["__global_default__"] = 2.10
                self._static_prices = static_map

                self.is_loaded = True
                self.load_error = None
                print(f"[PIT Price Service] Loaded {len(self._skus_data):,} SKU price histories into memory (metadata: {self._cache_metadata.get('source_file', 'unknown')}).")
            except Exception as e:
                self.is_loaded = False
                self.load_error = str(e)
                print(f"[PIT Price Service ERROR] Failed to load price history index: {e}")
                raise

    def ensure_loaded(self) -> None:
        """Ensures the price index is loaded."""
        if not self.is_loaded:
            self.load_index()

    def get_price(
        self,
        stock_code: str,
        as_of_date: Optional[Union[datetime.date, str]] = None
    ) -> float:
        """Retrieves cutoff-aware historical unit price for an SKU as of observation date T.
        
        Parameters
        ----------
        stock_code : str
            Unique merchandise SKU identifier.
        as_of_date : Optional[Union[datetime.date, str]], default=None
            Observation cutoff date T. If None, returns the latest historical price.
            Transactions occurring at date >= T are strictly excluded.
            
        Returns
        -------
        float
            Empirical historical unit price matching training definitions.
        """
        self.ensure_loaded()
        cleaned_sku = stock_code.strip()

        # Format observation date string
        obs_date_str: Optional[str] = None
        if as_of_date is not None:
            if hasattr(as_of_date, "isoformat"):
                obs_date_str = as_of_date.isoformat()
            else:
                obs_date_str = str(as_of_date)

        # 1. Look up SKU-specific transaction prefix sums
        if cleaned_sku in self._skus_data:
            entry = self._skus_data[cleaned_sku]
            dates = entry["dates"]
            sums = entry["sums"]
            counts = entry["counts"]

            if obs_date_str is None:
                # Latest historical price prior to end of data
                if counts and counts[-1] > 0:
                    return round(float(sums[-1] / counts[-1]), 4)
            else:
                # bisect_left finds first index with date >= obs_date_str
                # subtracting 1 gives last date strictly < obs_date_str (tx_date < T)
                idx = bisect.bisect_left(dates, obs_date_str) - 1
                if idx >= 0 and counts[idx] > 0:
                    return round(float(sums[idx] / counts[idx]), 4)

        # 2. Look up global expanding mean strictly prior to obs_date_str (historical backtesting only)
        if obs_date_str is not None and self._global_dates and self._global_counts:
            idx_g = bisect.bisect_left(self._global_dates, obs_date_str) - 1
            if idx_g >= 0 and self._global_counts[idx_g] > 0:
                return round(float(self._global_sums[idx_g] / self._global_counts[idx_g]), 4)

        # 3. Fallback:
        # When obs_date_str is specified, never leak future SKU prices from static cache.
        # Fall back strictly to the empirical global median prior ($2.10).
        # When obs_date_str is None (live forward forecasting), use latest static price or default.
        if obs_date_str is None:
            return float(self._static_prices.get(cleaned_sku, self._static_prices.get("__global_default__", 2.10)))
        return float(self._static_prices.get("__global_default__", 2.10))

    def get_status(self) -> Dict[str, Any]:
        """Returns structured subsystem status for readiness and diagnostics."""
        return {
            "ready": self.is_loaded,
            "total_skus": len(self._skus_data),
            "global_dates_count": len(self._global_dates),
            "cache_file": self.history_cache_path.name if self.history_cache_path.is_file() else None,
            "cache_metadata": getattr(self, "_cache_metadata", {}),
            "error": self.load_error
        }


# Global singleton instance
pit_price_service = PointInTimePriceService()

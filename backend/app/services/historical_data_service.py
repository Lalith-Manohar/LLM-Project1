"""Historical Sales Data Service for NEXORA Automated Demand Forecasting.

Loads and indexes historical product-day sales data from the processed retail CSV
dataset (daily_product_demand.csv). Provides thread-safe, sub-millisecond SKU
lookup and dynamically calculates the nine required historical lag and rolling
demand features at the latest historical observation date with exact mathematical
parity to the training pipeline.
"""

import threading
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import pandas as pd
import numpy as np

from app.schemas.forecast import HistoricalFeatures


class HistoricalDataError(Exception):
    """Base exception for historical sales data errors."""
    pass


class HistoricalDataNotFoundError(HistoricalDataError):
    """Raised when an SKU has no records in the historical dataset."""
    pass


class InsufficientHistoryError(HistoricalDataError):
    """Raised when an SKU has fewer than 29 days of historical records."""
    pass


class DatasetUnavailableError(HistoricalDataError):
    """Raised when the historical dataset cannot be loaded or is corrupted."""
    pass


class HistoricalDataService:
    """In-memory index and feature generator for historical daily demand records."""

    def __init__(self, data_path: Optional[str] = None):
        self._data_path = Path(data_path) if data_path else None
        self._sku_records: Dict[str, pd.DataFrame] = {}
        self._is_loaded: bool = False
        self._lock = threading.Lock()
        
        self.total_skus: int = 0
        self.total_records: int = 0
        self.global_min_date: Optional[datetime.date] = None
        self.global_max_date: Optional[datetime.date] = None
        self.loaded_file: Optional[str] = None

    def _resolve_data_path(self) -> Path:
        """Resolves the authoritative path to the processed historical CSV dataset."""
        if self._data_path and self._data_path.is_file():
            return self._data_path

        # Standard repository location: backend/ml/data/processed/daily_product_demand.csv
        base_dir = Path(__file__).resolve().parent.parent.parent
        primary_path = base_dir / "ml" / "data" / "processed" / "daily_product_demand.csv"
        if primary_path.is_file():
            return primary_path

        fallback_path = base_dir / "ml" / "data" / "processed" / "clean_gross_sales.csv"
        if fallback_path.is_file():
            return fallback_path

        raise DatasetUnavailableError(
            f"Historical sales dataset not found. Looked for primary '{primary_path}' "
            f"and fallback '{fallback_path}'. Ensure data preprocessing has executed."
        )

    def load_dataset(self, file_path: Optional[str] = None) -> None:
        """Loads and indexes daily demand records into memory.
        
        Thread-safe; executes once at application startup.
        """
        with self._lock:
            if file_path:
                self._data_path = Path(file_path)

            resolved_path = self._resolve_data_path()
            print(f"[NEXORA HistoricalDataService] Loading historical demand dataset from: {resolved_path}...")

            try:
                # Primary source: pre-aggregated daily demand
                if resolved_path.name == "daily_product_demand.csv":
                    df = pd.read_csv(
                        resolved_path,
                        dtype={"StockCode": str},
                        low_memory=False
                    )
                    df["StockCode"] = df["StockCode"].astype(str).str.strip()
                    df["date"] = pd.to_datetime(df["date"]).dt.date
                    df["daily_demand"] = df["daily_demand"].astype(int)
                elif resolved_path.name == "clean_gross_sales.csv":
                    # Fallback source: aggregate clean gross sales strictly using training formulas
                    print("[NEXORA HistoricalDataService] Aggregating fallback gross sales dataset...")
                    from ml.src.feature_engineering import aggregate_daily_demand, create_continuous_date_series
                    clean_df = pd.read_csv(
                        resolved_path,
                        dtype={"StockCode": str, "Invoice": str},
                        encoding="latin1",
                        low_memory=False
                    )
                    clean_df["date"] = pd.to_datetime(clean_df["InvoiceDate"], errors="coerce").dt.date
                    clean_df["line_revenue"] = clean_df["Quantity"].astype(float) * clean_df["Price"].astype(float)
                    daily_agg = aggregate_daily_demand(clean_df)
                    df, _ = create_continuous_date_series(daily_agg)
                else:
                    raise DatasetUnavailableError(f"Unsupported dataset format: {resolved_path}")

                # Index records per SKU, sorted strictly chronologically
                records: Dict[str, pd.DataFrame] = {}
                for sku, group in df.groupby("StockCode"):
                    sorted_group = group.sort_values("date").reset_index(drop=True)
                    records[sku] = sorted_group

                self._sku_records = records
                self.total_skus = len(records)
                self.total_records = len(df)
                self.global_min_date = df["date"].min()
                self.global_max_date = df["date"].max()
                self.loaded_file = str(resolved_path.name)
                self._is_loaded = True

                print(
                    f"[NEXORA HistoricalDataService] Successfully indexed {self.total_skus:,} SKUs "
                    f"({self.total_records:,} daily records) spanning {self.global_min_date} to {self.global_max_date}."
                )
            except Exception as e:
                self._is_loaded = False
                if isinstance(e, DatasetUnavailableError):
                    raise
                raise DatasetUnavailableError(f"Failed to load or parse historical sales data: {e}") from e

    def ensure_loaded(self) -> None:
        """Ensures the historical dataset is loaded; triggers loading if uninitialized."""
        if not self._is_loaded:
            self.load_dataset()

    def has_sku(self, stock_code: str) -> bool:
        """Checks if an SKU exists in the historical dataset."""
        self.ensure_loaded()
        cleaned_sku = stock_code.strip()
        return cleaned_sku in self._sku_records

    def get_features_for_sku(self, stock_code: str) -> Tuple[HistoricalFeatures, Dict[str, Any]]:
        """Dynamically calculates the 9 lag, rolling, and calendar features for an SKU.
        
        Features are calculated relative to the latest available historical observation date
        for that SKU, matching the exact definitions from model training:
        - DayOfWeek, Month, DayOfMonth: Calendar dynamics from observation date t.
        - Lag1: Actual daily demand at t - 1.
        - Lag7: Actual daily demand at t - 7.
        - Lag14: Actual daily demand at t - 14.
        - Lag28: Actual daily demand at t - 28.
        - RollingMean7: Mean daily demand over t - 7 through t - 1 (shifted by 1 day).
        - RollingMean28: Mean daily demand over t - 28 through t - 1 (shifted by 1 day).

        Args:
            stock_code: Unique product SKU.

        Returns:
            Tuple[HistoricalFeatures, Dict[str, Any]]:
                - Validated HistoricalFeatures schema.
                - Context metadata dictionary (observation date, history span, record count).

        Raises:
            HistoricalDataNotFoundError: If the SKU is not present in the historical dataset.
            InsufficientHistoryError: If the SKU has fewer than 29 days of records.
        """
        self.ensure_loaded()
        cleaned_sku = stock_code.strip()

        if cleaned_sku not in self._sku_records:
            raise HistoricalDataNotFoundError(
                f"Product SKU '{cleaned_sku}' was not found in historical sales records. "
                "Ensure the SKU exists in the UCI Online Retail II catalog."
            )

        sku_df = self._sku_records[cleaned_sku]
        record_count = len(sku_df)

        # Minimum history required to compute Lag28 and RollingMean28: 29 continuous days (t - 28 to t)
        if record_count < 29:
            raise InsufficientHistoryError(
                f"Insufficient historical sales data for SKU '{cleaned_sku}' "
                f"({record_count} calendar days available; minimum 29 days required to compute "
                "28-day lag and rolling average features)."
            )

        # The prediction origin is strictly the latest available observation date for this SKU
        latest_row = sku_df.iloc[-1]
        observation_date: datetime.date = latest_row["date"]
        
        # Continuous daily demand array including all days up to observation date t
        demands = sku_df["daily_demand"].values

        # Vectorized extraction matching training pipeline formulas:
        # demands[-1] is date t demand (excluded from past lags and rolling features)
        lag_1 = float(demands[-2])
        lag_7 = float(demands[-8])
        lag_14 = float(demands[-15])
        lag_28 = float(demands[-29])
        rolling_mean_7 = round(float(demands[-8:-1].mean()), 4)
        rolling_mean_28 = round(float(demands[-29:-1].mean()), 4)

        calendar_dow = int(observation_date.weekday())  # 0=Monday, 6=Sunday
        calendar_month = int(observation_date.month)
        calendar_dom = int(observation_date.day)

        features = HistoricalFeatures(
            day_of_week=calendar_dow,
            month=calendar_month,
            day_of_month=calendar_dom,
            lag_1=lag_1,
            lag_7=lag_7,
            lag_14=lag_14,
            lag_28=lag_28,
            rolling_mean_7=rolling_mean_7,
            rolling_mean_28=rolling_mean_28
        )

        context_metadata = {
            "observation_date": observation_date.isoformat(),
            "history_days": record_count,
            "history_start_date": sku_df.iloc[0]["date"].isoformat(),
            "history_end_date": observation_date.isoformat(),
            "is_auto_generated": True,
            "data_source": self.loaded_file or "daily_product_demand.csv"
        }

        return features, context_metadata

    def get_service_metadata(self) -> Dict[str, Any]:
        """Returns diagnostic metadata about the loaded historical dataset."""
        self.ensure_loaded()
        return {
            "status": "ready" if self._is_loaded else "uninitialized",
            "loaded_file": self.loaded_file,
            "total_skus": self.total_skus,
            "total_records": self.total_records,
            "global_min_date": self.global_min_date.isoformat() if self.global_min_date else None,
            "global_max_date": self.global_max_date.isoformat() if self.global_max_date else None,
        }


# Singleton service instance
historical_data_service = HistoricalDataService()

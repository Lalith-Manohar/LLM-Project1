"""Data Access Repository & Replaceable Adapters for M06 — Business Intelligence.

Defines a clean repository protocol aligned with DATABASE_SCHEMA.md v2.9 entities
(`transactions`, `transaction_items`, `products`, `categories`, `inventory`).

Current parallel-development adapters:
1. UCI Historical Adapter (`uci_historical`, `GBP`): lazily loads and caches the
   4-stream classified UCI Online Retail II dataset (`online_retail_II.csv`) using
   the exact `ml.src.preprocessing.classify_transactions` and non-merchandise rules.
2. Operational Store Adapter (`operational`, `INR`): empty by default until live
   MySQL operational tables (Phase 2) replace this adapter. Test fixtures can inject
   operational rows to verify immediate live reflection and GBP/INR separation.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import threading
from typing import Dict, List, Literal, Optional, Protocol

import numpy as np
import pandas as pd

TransactionStreamType = Literal["standard", "cancellation", "return", "exceptional"]
SourceOrigin = Literal["uci_historical", "operational"]

MONEY_SCALE = Decimal("0.01")
QTY_SCALE = Decimal("0.0001")
# Scale factor for exact fixed-point integer sums (0.0001 precision avoids IEEE-754 drift)
FIXED_POINT_SCALE = 10_000


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)


def quantize_qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_SCALE, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class OperationalSaleRecord:
    """In-memory representation of a joined `transactions` + `transaction_items` row."""

    invoice_number: str
    transaction_date: date
    country: str
    transaction_type: TransactionStreamType
    product_id: int
    stock_code: str
    description: str
    category_id: Optional[int]
    category_name: Optional[str]
    quantity: Decimal
    base_uom_quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    currency_code: Literal["INR"] = "INR"
    status: Literal["completed", "cancelled", "reversed"] = "completed"


@dataclass(frozen=True)
class OperationalCatalogItem:
    """Active operational catalog + inventory row for slow-moving zero-sale detection."""

    product_id: int
    stock_code: str
    description: str
    category_id: Optional[int]
    category_name: Optional[str]
    current_quantity: Decimal
    is_active: bool = True


class AnalyticsRepositoryProtocol(Protocol):
    """Replaceable data-access contract for M06 Business Intelligence."""

    def get_uci_dataframe(self) -> pd.DataFrame:
        """Returns normalized 4-stream UCI historical DataFrame (GBP)."""

    def get_operational_dataframe(self) -> pd.DataFrame:
        """Returns normalized operational sales DataFrame (INR)."""

    def get_operational_catalog(self) -> List[OperationalCatalogItem]:
        """Returns active operational catalog items with current inventory quantities."""


class AnalyticsDataUnavailableError(RuntimeError):
    """Raised when the underlying analytics data source cannot be loaded."""


def _empty_normalized_dataframe() -> pd.DataFrame:
    """Creates an empty DataFrame with the canonical normalized analytics schema."""
    return pd.DataFrame(
        {
            "invoice_number": pd.Series(dtype="object"),
            "transaction_date": pd.Series(dtype="object"),
            "country": pd.Series(dtype="object"),
            "transaction_type": pd.Series(dtype="object"),
            "product_id": pd.Series(dtype="object"),
            "stock_code": pd.Series(dtype="object"),
            "description": pd.Series(dtype="object"),
            "category_id": pd.Series(dtype="object"),
            "category_name": pd.Series(dtype="object"),
            "qty_scaled": pd.Series(dtype="int64"),
            "amount_scaled": pd.Series(dtype="int64"),
            "currency_code": pd.Series(dtype="object"),
            "status": pd.Series(dtype="object"),
        }
    )


def _to_scaled_int(series: pd.Series) -> np.ndarray:
    """Converts numeric series to exact int64 scaled by 10_000 for drift-free aggregation."""
    numeric = pd.to_numeric(series, errors="coerce").fillna(0.0).to_numpy(dtype=np.float64)
    return np.rint(numeric * FIXED_POINT_SCALE).astype(np.int64)


class HybridAnalyticsRepository:
    """Thread-safe repository combining lazy UCI CSV caching with an operational INR store."""

    def __init__(
        self,
        raw_uci_path: Optional[Path] = None,
        uci_override_df: Optional[pd.DataFrame] = None,
    ) -> None:
        self._raw_uci_path = raw_uci_path
        self._uci_lock = threading.Lock()
        self._op_lock = threading.Lock()
        self._uci_df: Optional[pd.DataFrame] = uci_override_df
        self._operational_records: List[OperationalSaleRecord] = []
        self._operational_catalog: Dict[str, OperationalCatalogItem] = {}

    def _resolve_uci_path(self) -> Path:
        if self._raw_uci_path is not None:
            if self._raw_uci_path.is_file():
                return self._raw_uci_path
            raise AnalyticsDataUnavailableError(
                f"Configured UCI dataset not found: {self._raw_uci_path.name}"
            )

        base_dir = Path(__file__).resolve().parent.parent.parent
        raw_path = base_dir / "ml" / "data" / "raw" / "online_retail_II.csv"
        if raw_path.is_file():
            return raw_path

        raise AnalyticsDataUnavailableError(
            "UCI historical dataset 'online_retail_II.csv' not found under backend/ml/data/raw/."
        )

    def _load_uci_dataframe(self) -> pd.DataFrame:
        """Loads and normalizes raw UCI CSV using NEXORA's exact 4-stream rules."""
        from ml.src.preprocessing import NON_MERCHANDISE_CODES, classify_transactions

        csv_path = self._resolve_uci_path()
        raw_df = pd.read_csv(
            csv_path,
            dtype={"Invoice": str, "StockCode": str, "Description": str, "Country": str},
            encoding="latin1",
            low_memory=False,
        )

        classified = classify_transactions(raw_df)

        # Map preprocessing stream labels to DATABASE_SCHEMA.md v2.9 transactions.transaction_type
        stream_to_schema_type = {
            "gross_sales": "standard",
            "cancellation": "cancellation",
            "return_credit": "return",
            "exceptional": "exceptional",
        }
        classified["transaction_type"] = classified["transaction_stream"].map(stream_to_schema_type).fillna("exceptional")

        # Exclude non-merchandise service codes from standard merchandise sales (matches preprocessing.py)
        stock_codes = classified["StockCode"].fillna("").astype(str).str.strip()
        is_service = stock_codes.str.upper().isin(NON_MERCHANDISE_CODES)
        classified.loc[(classified["transaction_type"] == "standard") & is_service, "transaction_type"] = "exceptional"

        # Parse dates cleanly
        parsed_dates = pd.to_datetime(classified["InvoiceDate"], errors="coerce").dt.date
        valid_date_mask = parsed_dates.notna()
        classified = classified[valid_date_mask].copy()
        parsed_dates = parsed_dates[valid_date_mask]

        qty_num = pd.to_numeric(classified["Quantity"], errors="coerce").fillna(0.0)
        price_num = pd.to_numeric(classified["Price"], errors="coerce").fillna(0.0)
        line_amount = qty_num * price_num

        # Keep only commercial streams relevant to BI (standard, cancellation, return)
        relevant = classified["transaction_type"].isin(["standard", "cancellation", "return"])
        filtered = classified[relevant]

        normalized = pd.DataFrame(
            {
                "invoice_number": filtered["Invoice"].fillna("").astype(str).str.strip(),
                "transaction_date": parsed_dates[relevant].to_numpy(),
                "country": filtered["Country"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown"),
                "transaction_type": filtered["transaction_type"].to_numpy(),
                "product_id": None,
                "stock_code": filtered["StockCode"].fillna("").astype(str).str.strip(),
                "description": filtered["Description"].fillna("Unnamed Product").astype(str).str.strip().replace("", "Unnamed Product"),
                "category_id": None,
                "category_name": None,
                "qty_scaled": _to_scaled_int(qty_num[relevant]),
                "amount_scaled": _to_scaled_int(line_amount[relevant]),
                "currency_code": "GBP",
                "status": "completed",
            }
        )
        return normalized.reset_index(drop=True)

    def get_uci_dataframe(self) -> pd.DataFrame:
        if self._uci_df is not None:
            return self._uci_df
        with self._uci_lock:
            if self._uci_df is None:
                self._uci_df = self._load_uci_dataframe()
            return self._uci_df

    def get_operational_dataframe(self) -> pd.DataFrame:
        with self._op_lock:
            if not self._operational_records:
                return _empty_normalized_dataframe()

            rows = []
            for rec in self._operational_records:
                qty_scaled = int((rec.base_uom_quantity * Decimal(FIXED_POINT_SCALE)).to_integral_value(rounding=ROUND_HALF_UP))
                amt_scaled = int((rec.line_total * Decimal(FIXED_POINT_SCALE)).to_integral_value(rounding=ROUND_HALF_UP))
                rows.append(
                    {
                        "invoice_number": rec.invoice_number,
                        "transaction_date": rec.transaction_date,
                        "country": rec.country,
                        "transaction_type": rec.transaction_type,
                        "product_id": rec.product_id,
                        "stock_code": rec.stock_code,
                        "description": rec.description,
                        "category_id": rec.category_id,
                        "category_name": rec.category_name,
                        "qty_scaled": qty_scaled,
                        "amount_scaled": amt_scaled,
                        "currency_code": rec.currency_code,
                        "status": rec.status,
                    }
                )
            return pd.DataFrame(rows)

    def get_operational_catalog(self) -> List[OperationalCatalogItem]:
        with self._op_lock:
            return list(self._operational_catalog.values())

    def add_operational_records(self, records: List[OperationalSaleRecord]) -> None:
        """Injects operational INR records (for integration hooks and automated tests)."""
        with self._op_lock:
            self._operational_records.extend(records)

    def upsert_operational_catalog(self, items: List[OperationalCatalogItem]) -> None:
        """Registers operational catalog + inventory items (for slow-moving zero-sale tests)."""
        with self._op_lock:
            for item in items:
                self._operational_catalog[item.stock_code] = item

    def clear_operational_data(self) -> None:
        """Resets in-memory operational store cleanly (used in tests)."""
        with self._op_lock:
            self._operational_records.clear()
            self._operational_catalog.clear()


def build_normalized_df_from_records(
    records: List[Dict[str, object]],
    currency_code: Literal["GBP", "INR"] = "GBP",
) -> pd.DataFrame:
    """Helper for tests to construct a normalized analytics DataFrame deterministically."""
    if not records:
        return _empty_normalized_dataframe()

    rows = []
    for rec in records:
        qty = Decimal(str(rec["quantity"]))
        price = Decimal(str(rec["unit_price"]))
        line_total = Decimal(str(rec.get("line_total", qty * price)))
        rows.append(
            {
                "invoice_number": str(rec["invoice_number"]),
                "transaction_date": rec["transaction_date"],
                "country": str(rec.get("country", "United Kingdom")),
                "transaction_type": str(rec.get("transaction_type", "standard")),
                "product_id": rec.get("product_id"),
                "stock_code": str(rec["stock_code"]),
                "description": str(rec.get("description", "Test Product")),
                "category_id": rec.get("category_id"),
                "category_name": rec.get("category_name"),
                "qty_scaled": int((qty * Decimal(FIXED_POINT_SCALE)).to_integral_value(rounding=ROUND_HALF_UP)),
                "amount_scaled": int((line_total * Decimal(FIXED_POINT_SCALE)).to_integral_value(rounding=ROUND_HALF_UP)),
                "currency_code": currency_code,
                "status": str(rec.get("status", "completed")),
            }
        )
    return pd.DataFrame(rows)


# Default singleton repository instance (swappable with SQLAlchemy MySQL repository in Phase 2)
analytics_repository = HybridAnalyticsRepository()

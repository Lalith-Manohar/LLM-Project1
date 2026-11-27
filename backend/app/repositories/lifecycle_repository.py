"""Data Access Repository & Replaceable Adapters for M08 — Product Lifecycle Intelligence.

Aligned 1:1 with DATABASE_SCHEMA.md v2.9 entities:
  - `products` (cached `lifecycle_stage`, `current_unit_price`, `currency_code`, `is_active`, `created_at`)
  - `inventory` (`current_quantity` in `base_uom`)
  - `product_lifecycle_snapshots` (append-only, immutable, `chk_pls_no_auto_discontinued`)
  - `operational_settings` (`domain = 'lifecycle'`, system defaults + `min_bound`/`max_bound`)

Supports genuine historical UCI SKU trajectories (anchored to 2011-12-09) alongside
operational INR products, and enforces atomic rollback when Tier 1 audit writes fail
(`DDR-10`) so the repository contract drops straight into Phase 2 SQLAlchemy/MySQL.
"""

import copy
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import threading
from typing import Any, Callable, Dict, List, Literal, Optional, Protocol, Tuple, Union

from app.core.interfaces import AuditLoggerProtocol, AuditWriteError, audit_logger
from app.core.provenance import ActionSource, RequestProvenance, WorkspaceCode
from app.schemas.lifecycle import LifecycleStage, SettingValueType, SnapshotTriggerType

UCI_ANCHOR_DATE = date(2011, 12, 9)
MONEY_SCALE = Decimal("0.01")
QTY_SCALE = Decimal("0.0001")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)


def quantize_qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_SCALE, rounding=ROUND_HALF_UP)


@dataclass
class ProductLifecycleRecord:
    """In-memory projection of `products` + `inventory` + daily sales series."""

    product_id: int
    stock_code: str
    description: str
    category_name: Optional[str]
    source_origin: Literal["uci_historical", "operational"]
    currency_code: Literal["GBP", "INR"]
    current_unit_price: Decimal
    current_quantity: Decimal
    is_active: bool
    onboarded_date: date
    lifecycle_stage: LifecycleStage = "Introduction"
    # Mapping of sale_date -> (units_sold: Decimal, order_count: int)
    daily_sales: Dict[date, Tuple[Decimal, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class LifecycleSnapshotRecord:
    """Immutable append-only record matching `product_lifecycle_snapshots` DDL."""

    id: int
    product_id: int
    stock_code: str
    lifecycle_stage: LifecycleStage
    previous_stage: Optional[LifecycleStage]
    rolling_velocity: Decimal
    order_frequency: Decimal
    sku_age_days: int
    days_since_last_sale: Optional[int]
    is_dormant_stock: bool
    trigger_type: SnapshotTriggerType
    applied_settings_snapshot: Optional[Dict[str, Any]]
    selected_workspace: Optional[WorkspaceCode]
    action_source: ActionSource
    operator_ref: Optional[str]
    evaluated_at: str


@dataclass(frozen=True)
class DiscontinueIdempotencyRecord:
    """In-memory idempotency record for manual discontinuation retries."""

    idempotency_key: str
    product_id: int
    confirm_discontinue: bool
    reason: str
    operator_ref: Optional[str]
    previous_stage: LifecycleStage
    snapshot: LifecycleSnapshotRecord
    audit_log_id: int


@dataclass
class BoundedSettingRecord:
    """Mutable config entry matching `operational_settings` (`domain = 'lifecycle'`)."""

    setting_key: str
    setting_value: Union[int, Decimal]
    default_value: Union[int, Decimal]
    min_bound: Decimal
    max_bound: Decimal
    value_type: SettingValueType
    description: str
    selected_workspace: Optional[WorkspaceCode] = None
    action_source: ActionSource = "SYSTEM"
    operator_ref: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def build_default_lifecycle_settings() -> Dict[str, BoundedSettingRecord]:
    """Approved DDR-08 bounded lifecycle defaults (includes Schema v2.9 seeded keys)."""
    now_iso = datetime.now(timezone.utc).isoformat()
    defs = [
        BoundedSettingRecord(
            setting_key="lifecycle_hysteresis_windows",
            setting_value=2,
            default_value=2,
            min_bound=Decimal("1"),
            max_bound=Decimal("12"),
            value_type="INTEGER",
            description="Consecutive evaluation windows required before committing an automated stage transition (DDR-08).",
            updated_at=now_iso,
        ),
        BoundedSettingRecord(
            setting_key="lifecycle_inactivity_days",
            setting_value=90,
            default_value=90,
            min_bound=Decimal("14"),
            max_bound=Decimal("365"),
            value_type="INTEGER",
            description="Days without sales before an established SKU enters Decline and triggers dormant/dead-stock review.",
            updated_at=now_iso,
        ),
        BoundedSettingRecord(
            setting_key="lifecycle_intro_max_age_days",
            setting_value=60,
            default_value=60,
            min_bound=Decimal("7"),
            max_bound=Decimal("180"),
            value_type="INTEGER",
            description="Maximum SKU age in days during which newly onboarded SKUs remain in Introduction.",
            updated_at=now_iso,
        ),
        BoundedSettingRecord(
            setting_key="lifecycle_velocity_window_days",
            setting_value=30,
            default_value=30,
            min_bound=Decimal("7"),
            max_bound=Decimal("180"),
            value_type="INTEGER",
            description="Rolling lookback window (days) used to compare current vs. prior sales velocity and order frequency.",
            updated_at=now_iso,
        ),
        BoundedSettingRecord(
            setting_key="lifecycle_growth_velocity_pct",
            setting_value=Decimal("15.00"),
            default_value=Decimal("15.00"),
            min_bound=Decimal("1.00"),
            max_bound=Decimal("200.00"),
            value_type="DECIMAL",
            description="Minimum positive rolling velocity % increase required for Growth stage classification.",
            updated_at=now_iso,
        ),
        BoundedSettingRecord(
            setting_key="lifecycle_decline_velocity_pct",
            setting_value=Decimal("20.00"),
            default_value=Decimal("20.00"),
            min_bound=Decimal("1.00"),
            max_bound=Decimal("95.00"),
            value_type="DECIMAL",
            description="Minimum negative rolling velocity % drop required for Decline stage classification.",
            updated_at=now_iso,
        ),
        BoundedSettingRecord(
            setting_key="lifecycle_min_order_frequency",
            setting_value=Decimal("0.0500"),
            default_value=Decimal("0.0500"),
            min_bound=Decimal("0.0000"),
            max_bound=Decimal("10.0000"),
            value_type="DECIMAL",
            description="Minimum daily order frequency required to qualify for Growth stage classification.",
            updated_at=now_iso,
        ),
    ]
    return {item.setting_key: item for item in defs}


class LifecycleRepositoryProtocol(Protocol):
    """Replaceable repository contract for M08 Product Lifecycle Intelligence."""

    def list_products(
        self,
        source_origin: Literal["uci_historical", "operational", "all"] = "all",
    ) -> List[ProductLifecycleRecord]:
        ...

    def get_product(self, identifier: Union[int, str]) -> Optional[ProductLifecycleRecord]:
        ...

    def get_snapshots(self, product_id: int) -> List[LifecycleSnapshotRecord]:
        ...

    def get_latest_snapshot(self, product_id: int) -> Optional[LifecycleSnapshotRecord]:
        ...

    def get_pending_hysteresis(self, product_id: int) -> Tuple[Optional[LifecycleStage], int]:
        ...

    def set_pending_hysteresis(
        self,
        product_id: int,
        pending_stage: Optional[LifecycleStage],
        consecutive_count: int,
    ) -> None:
        ...

    def append_evaluation_snapshot(
        self,
        *,
        product_id: int,
        new_stage: LifecycleStage,
        previous_stage: Optional[LifecycleStage],
        rolling_velocity: Decimal,
        order_frequency: Decimal,
        sku_age_days: int,
        days_since_last_sale: Optional[int],
        is_dormant_stock: bool,
        applied_settings_snapshot: Dict[str, Any],
        provenance: RequestProvenance,
        action_source: ActionSource = "SYSTEM",
    ) -> LifecycleSnapshotRecord:
        ...

    def discontinue_product_atomic(
        self,
        *,
        product_id: int,
        rolling_velocity: Decimal,
        order_frequency: Decimal,
        sku_age_days: int,
        days_since_last_sale: Optional[int],
        is_dormant_stock: bool,
        applied_settings_snapshot: Dict[str, Any],
        reason: str,
        provenance: RequestProvenance,
        operator_ref: Optional[str],
        idempotency_key: Optional[str] = None,
    ) -> Tuple[LifecycleSnapshotRecord, int]:
        ...

    def get_discontinue_idempotency(
        self, idempotency_key: str
    ) -> Optional[DiscontinueIdempotencyRecord]:
        ...

    def get_settings(self) -> Dict[str, BoundedSettingRecord]:
        ...

    def update_settings_atomic(
        self,
        *,
        updates: Dict[str, Union[int, Decimal]],
        provenance: RequestProvenance,
        operator_ref: Optional[str],
        action: Literal["LIFECYCLE_CONFIG_UPDATED", "LIFECYCLE_CONFIG_RESET"],
    ) -> Tuple[Dict[str, BoundedSettingRecord], int]:
        ...


class HybridLifecycleRepository:
    """Thread-safe repository combining lazy UCI baseline catalog with transactional in-memory governance.

    - Lazily indexes real UCI SKUs from `daily_product_demand.csv` (already tracked in repo)
      without blocking startup or `/ready`.
    - Supports injecting operational INR products & stock balances cleanly.
    - Enforces `chk_pls_no_auto_discontinued` and atomic rollback if Tier 1 audit fails (`DDR-10`).
    """

    def __init__(
        self,
        *,
        audit: AuditLoggerProtocol = audit_logger,
        load_uci_on_demand: bool = True,
        uci_sku_limit: Optional[int] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._audit = audit
        self._load_uci_on_demand = load_uci_on_demand
        self._uci_sku_limit = uci_sku_limit
        self._uci_loaded = False

        self._products_by_id: Dict[int, ProductLifecycleRecord] = {}
        self._id_by_stock_code: Dict[str, int] = {}
        self._snapshots_by_product: Dict[int, List[LifecycleSnapshotRecord]] = {}
        # Transient consecutive-period hysteresis buffer kept outside applied_settings_snapshot JSON
        # so product_lifecycle_snapshots.applied_settings_snapshot holds strictly threshold settings.
        self._pending_hysteresis: Dict[int, Tuple[Optional[LifecycleStage], int]] = {}
        self._discontinue_idempotency: Dict[str, DiscontinueIdempotencyRecord] = {}
        self._settings: Dict[str, BoundedSettingRecord] = build_default_lifecycle_settings()
        self._next_product_id: int = 1
        self._next_snapshot_id: int = 1

    def _ensure_uci_loaded(self) -> None:
        if not self._load_uci_on_demand or self._uci_loaded:
            return
        with self._lock:
            if self._uci_loaded:
                return
            self._load_uci_from_processed_csv()
            self._uci_loaded = True

    def _load_uci_from_processed_csv(self) -> None:
        """Lazily populates UCI baseline SKUs from tracked `daily_product_demand.csv`."""
        from pathlib import Path
        import pandas as pd

        base_dir = Path(__file__).resolve().parent.parent.parent
        csv_path = base_dir / "ml" / "data" / "processed" / "daily_product_demand.csv"
        if not csv_path.is_file():
            return

        df = pd.read_csv(
            csv_path,
            dtype={"StockCode": str},
            low_memory=False,
        )
        if df.empty:
            return

        df["StockCode"] = df["StockCode"].astype(str).str.strip()
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df = df[df["date"].notna()]

        # Focus on actual non-zero sales rows for compact memory footprint + exact min_date lifespan
        sku_min_dates = df.groupby("StockCode")["date"].min().to_dict()
        sales_only = df[df["daily_demand"] > 0]

        sku_codes = sorted(sku_min_dates.keys())
        if self._uci_sku_limit is not None:
            sku_codes = sku_codes[: self._uci_sku_limit]
            sales_only = sales_only[sales_only["StockCode"].isin(sku_codes)]

        # Pre-group sales_only per SKU
        grouped_sales: Dict[str, Dict[date, Tuple[Decimal, int]]] = {}
        sku_prices: Dict[str, Decimal] = {}
        for sku, grp in sales_only.groupby("StockCode", sort=False):
            daily_map: Dict[date, Tuple[Decimal, int]] = {}
            total_rev = 0.0
            total_qty = 0
            for row in grp.itertuples(index=False):
                qty_val = Decimal(str(int(row.daily_demand)))
                tx_cnt = int(row.transaction_count) if hasattr(row, "transaction_count") else 1
                daily_map[row.date] = (quantize_qty(qty_val), max(1, tx_cnt))
                if hasattr(row, "revenue"):
                    total_rev += float(row.revenue)
                total_qty += int(row.daily_demand)
            grouped_sales[str(sku)] = daily_map
            avg_price = (total_rev / total_qty) if total_qty > 0 else 0.0
            sku_prices[str(sku)] = quantize_money(Decimal(str(round(max(0.0, avg_price), 2))))

        for code in sku_codes:
            if code in self._id_by_stock_code:
                continue
            pid = self._next_product_id
            self._next_product_id += 1
            record = ProductLifecycleRecord(
                product_id=pid,
                stock_code=code,
                description=f"UCI Catalog SKU {code}",
                category_name="UCI Historical Baseline",
                source_origin="uci_historical",
                currency_code="GBP",
                current_unit_price=sku_prices.get(code, Decimal("0.00")),
                # UCI dataset does not contain live warehouse inventory (Blueprint Section 5)
                current_quantity=Decimal("0.0000"),
                is_active=True,
                onboarded_date=sku_min_dates[code],
                lifecycle_stage="Introduction",
                daily_sales=grouped_sales.get(code, {}),
            )
            self._products_by_id[pid] = record
            self._id_by_stock_code[code] = pid

    def register_product(self, record: ProductLifecycleRecord) -> ProductLifecycleRecord:
        """Registers or replaces a product record (used by operational adapters & tests)."""
        with self._lock:
            if record.product_id <= 0:
                record.product_id = self._next_product_id
            self._next_product_id = max(self._next_product_id, record.product_id + 1)
            self._products_by_id[record.product_id] = record
            self._id_by_stock_code[record.stock_code] = record.product_id
            return record

    def list_products(
        self,
        source_origin: Literal["uci_historical", "operational", "all"] = "all",
    ) -> List[ProductLifecycleRecord]:
        if source_origin in ("uci_historical", "all"):
            self._ensure_uci_loaded()
        with self._lock:
            items = list(self._products_by_id.values())
            if source_origin != "all":
                items = [p for p in items if p.source_origin == source_origin]
            items.sort(key=lambda p: p.product_id)
            return items

    def get_product(self, identifier: Union[int, str]) -> Optional[ProductLifecycleRecord]:
        self._ensure_uci_loaded()
        with self._lock:
            if isinstance(identifier, int):
                return self._products_by_id.get(identifier)
            cleaned = identifier.strip()
            if cleaned.isdigit():
                by_id = self._products_by_id.get(int(cleaned))
                if by_id is not None:
                    return by_id
            pid = self._id_by_stock_code.get(cleaned)
            if pid is None:
                # Case-insensitive stock_code fallback
                lower_target = cleaned.lower()
                for code, candidate_id in self._id_by_stock_code.items():
                    if code.lower() == lower_target:
                        pid = candidate_id
                        break
            return self._products_by_id.get(pid) if pid is not None else None

    def get_snapshots(self, product_id: int) -> List[LifecycleSnapshotRecord]:
        with self._lock:
            return list(self._snapshots_by_product.get(product_id, []))

    def get_latest_snapshot(self, product_id: int) -> Optional[LifecycleSnapshotRecord]:
        with self._lock:
            snaps = self._snapshots_by_product.get(product_id)
            return snaps[-1] if snaps else None

    def get_pending_hysteresis(self, product_id: int) -> Tuple[Optional[LifecycleStage], int]:
        with self._lock:
            return self._pending_hysteresis.get(product_id, (None, 0))

    def get_discontinue_idempotency(
        self, idempotency_key: str
    ) -> Optional[DiscontinueIdempotencyRecord]:
        with self._lock:
            return self._discontinue_idempotency.get(idempotency_key)

    def set_pending_hysteresis(
        self,
        product_id: int,
        pending_stage: Optional[LifecycleStage],
        consecutive_count: int,
    ) -> None:
        with self._lock:
            if pending_stage is None or consecutive_count <= 0:
                self._pending_hysteresis.pop(product_id, None)
            else:
                self._pending_hysteresis[product_id] = (pending_stage, consecutive_count)

    def append_evaluation_snapshot(
        self,
        *,
        product_id: int,
        new_stage: LifecycleStage,
        previous_stage: Optional[LifecycleStage],
        rolling_velocity: Decimal,
        order_frequency: Decimal,
        sku_age_days: int,
        days_since_last_sale: Optional[int],
        is_dormant_stock: bool,
        applied_settings_snapshot: Dict[str, Any],
        provenance: RequestProvenance,
        action_source: ActionSource = "SYSTEM",
    ) -> LifecycleSnapshotRecord:
        # Mirror DATABASE_SCHEMA.md v2.9 CHECK constraint `chk_pls_no_auto_discontinued`
        if new_stage == "Discontinued":
            raise ValueError(
                "Constraint violation (chk_pls_no_auto_discontinued): "
                "scheduled_evaluation cannot assign 'Discontinued'."
            )

        with self._lock:
            product = self._products_by_id.get(product_id)
            if product is None:
                raise KeyError(f"Product {product_id} not found.")

            snap = LifecycleSnapshotRecord(
                id=self._next_snapshot_id,
                product_id=product_id,
                stock_code=product.stock_code,
                lifecycle_stage=new_stage,
                previous_stage=previous_stage,
                rolling_velocity=quantize_qty(rolling_velocity),
                order_frequency=quantize_qty(order_frequency),
                sku_age_days=max(0, int(sku_age_days)),
                days_since_last_sale=days_since_last_sale,
                is_dormant_stock=bool(is_dormant_stock),
                trigger_type="scheduled_evaluation",
                applied_settings_snapshot=copy.deepcopy(applied_settings_snapshot),
                selected_workspace=provenance.selected_workspace,
                action_source=action_source,
                operator_ref=provenance.operator_ref,
                evaluated_at=datetime.now(timezone.utc).isoformat(),
            )
            self._next_snapshot_id += 1
            self._snapshots_by_product.setdefault(product_id, []).append(snap)
            product.lifecycle_stage = new_stage
            return snap

    def discontinue_product_atomic(
        self,
        *,
        product_id: int,
        rolling_velocity: Decimal,
        order_frequency: Decimal,
        sku_age_days: int,
        days_since_last_sale: Optional[int],
        is_dormant_stock: bool,
        applied_settings_snapshot: Dict[str, Any],
        reason: str,
        provenance: RequestProvenance,
        operator_ref: Optional[str],
        idempotency_key: Optional[str] = None,
    ) -> Tuple[LifecycleSnapshotRecord, int]:
        """Atomically discontinues a SKU with Tier 1 fail-closed audit rollback (`DDR-08`, `DDR-10`)."""
        with self._lock:
            if idempotency_key:
                existing = self._discontinue_idempotency.get(idempotency_key)
                if existing is not None:
                    if (existing.product_id, existing.reason, existing.operator_ref) != (
                        product_id,
                        reason,
                        operator_ref,
                    ):
                        raise ValueError(
                            f"Idempotency key '{idempotency_key}' conflicts with an earlier discontinuation request."
                        )
                    return existing.snapshot, existing.audit_log_id

            product = self._products_by_id.get(product_id)
            if product is None:
                raise KeyError(f"Product {product_id} not found.")
            if product.lifecycle_stage == "Discontinued":
                raise ValueError(
                    f"Product '{product.stock_code}' is already in 'Discontinued' lifecycle stage."
                )

            prev_stage = product.lifecycle_stage
            prev_next_snap_id = self._next_snapshot_id
            prev_hysteresis = self._pending_hysteresis.get(product_id)
            effective_operator = operator_ref or provenance.operator_ref

            snap = LifecycleSnapshotRecord(
                id=self._next_snapshot_id,
                product_id=product_id,
                stock_code=product.stock_code,
                lifecycle_stage="Discontinued",
                previous_stage=prev_stage,
                rolling_velocity=quantize_qty(rolling_velocity),
                order_frequency=quantize_qty(order_frequency),
                sku_age_days=max(0, int(sku_age_days)),
                days_since_last_sale=days_since_last_sale,
                is_dormant_stock=bool(is_dormant_stock),
                trigger_type="manual_discontinued",
                applied_settings_snapshot=copy.deepcopy(applied_settings_snapshot),
                selected_workspace=provenance.selected_workspace,
                action_source=provenance.action_source,
                operator_ref=effective_operator,
                evaluated_at=datetime.now(timezone.utc).isoformat(),
            )

            # Mutate in-memory state, then execute mandatory Tier 1 audit; roll back on any failure
            self._next_snapshot_id += 1
            self._snapshots_by_product.setdefault(product_id, []).append(snap)
            self._pending_hysteresis.pop(product_id, None)
            product.lifecycle_stage = "Discontinued"

            try:
                audit_entry = self._audit.record(
                    module="M08_LIFECYCLE",
                    action="PRODUCT_DISCONTINUED",
                    entity_type="products",
                    entity_id=str(product_id),
                    outcome="SUCCESS",
                    audit_tier="TIER_1_FAIL_CLOSED",
                    action_source=provenance.action_source,
                    selected_workspace=provenance.selected_workspace,
                    operator_ref=effective_operator,
                    correlation_id=provenance.correlation_id,
                    idempotency_key=idempotency_key,
                    before_values={"lifecycle_stage": prev_stage, "stock_code": product.stock_code},
                    after_values={
                        "lifecycle_stage": "Discontinued",
                        "stock_code": product.stock_code,
                        "snapshot_id": snap.id,
                        "reason": reason,
                    },
                )
            except Exception as exc:
                # DDR-10 Tier 1 fail-closed rollback
                product.lifecycle_stage = prev_stage
                self._snapshots_by_product[product_id].pop()
                self._next_snapshot_id = prev_next_snap_id
                if prev_hysteresis is not None:
                    self._pending_hysteresis[product_id] = prev_hysteresis
                raise AuditWriteError(f"Tier 1 audit failed; manual discontinuation rolled back: {exc}") from exc

            if idempotency_key:
                self._discontinue_idempotency[idempotency_key] = DiscontinueIdempotencyRecord(
                    idempotency_key=idempotency_key,
                    product_id=product_id,
                    confirm_discontinue=True,
                    reason=reason,
                    operator_ref=operator_ref,
                    previous_stage=prev_stage,
                    snapshot=snap,
                    audit_log_id=audit_entry.id,
                )

            return snap, audit_entry.id

    def get_settings(self) -> Dict[str, BoundedSettingRecord]:
        with self._lock:
            return {k: copy.deepcopy(v) for k, v in self._settings.items()}

    def update_settings_atomic(
        self,
        *,
        updates: Dict[str, Union[int, Decimal]],
        provenance: RequestProvenance,
        operator_ref: Optional[str],
        action: Literal["LIFECYCLE_CONFIG_UPDATED", "LIFECYCLE_CONFIG_RESET"],
    ) -> Tuple[Dict[str, BoundedSettingRecord], int]:
        """Atomically updates bounded lifecycle settings with Tier 1 fail-closed audit rollback."""
        with self._lock:
            backup = copy.deepcopy(self._settings)
            before_values: Dict[str, Any] = {}
            after_values: Dict[str, Any] = {}
            now_iso = datetime.now(timezone.utc).isoformat()
            effective_operator = operator_ref or provenance.operator_ref

            for key, new_val in updates.items():
                setting = self._settings[key]
                before_values[key] = str(setting.setting_value)
                after_values[key] = str(new_val)
                setting.setting_value = new_val
                setting.selected_workspace = provenance.selected_workspace
                setting.action_source = provenance.action_source
                setting.operator_ref = effective_operator
                setting.updated_at = now_iso

            try:
                audit_entry = self._audit.record(
                    module="M08_LIFECYCLE",
                    action=action,
                    entity_type="operational_settings",
                    entity_id="domain:lifecycle",
                    outcome="SUCCESS",
                    audit_tier="TIER_1_FAIL_CLOSED",
                    action_source=provenance.action_source,
                    selected_workspace=provenance.selected_workspace,
                    operator_ref=effective_operator,
                    correlation_id=provenance.correlation_id,
                    before_values=before_values,
                    after_values=after_values,
                )
            except Exception as exc:
                # DDR-10 Tier 1 fail-closed rollback
                self._settings = backup
                raise AuditWriteError(f"Tier 1 audit failed; lifecycle settings update rolled back: {exc}") from exc

            return {k: copy.deepcopy(v) for k, v in self._settings.items()}, audit_entry.id


# Default singleton repository (swappable with SQLAlchemy MySQL repository in Phase 2)
lifecycle_repository = HybridLifecycleRepository()

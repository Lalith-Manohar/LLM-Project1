"""Business Logic Service for M08 — Product Lifecycle Intelligence.

Implements DDR-08 lifecycle classification across the five canonical stages:
  Introduction -> Growth -> Maturity -> Decline -> (manual) Discontinued
with:
  - Rolling sales velocity, order frequency, and SKU age computation
  - Zero-baseline division safety (returns None instead of Inf/NaN)
  - UCI historical anchor pinned cleanly to 2011-12-09
  - Anti-flicker consecutive-period hysteresis evaluated against prior snapshots
  - Strict non-auto-discontinuation guard (chk_pls_no_auto_discontinued)
  - Dead-stock capital valuation (DECIMAL, EXCL-04 compliant)
  - Bounded operational_settings updates + reset-to-default (forward-only, Tier 1 audit)
  - Deduplicated SYS-03 Smart Alert dispatch on confirmed negative transitions / dormancy
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from app.core.interfaces import AlertPublisherProtocol, alert_publisher
from app.core.provenance import ActionSource, RequestProvenance
from app.repositories.lifecycle_repository import (
    BoundedSettingRecord,
    LifecycleRepositoryProtocol,
    LifecycleSnapshotRecord,
    ProductLifecycleRecord,
    UCI_ANCHOR_DATE,
    build_default_lifecycle_settings,
    lifecycle_repository,
    quantize_money,
    quantize_qty,
)
from app.schemas.lifecycle import (
    DeadStockItem,
    DeadStockResponse,
    DiscontinueProductRequest,
    DiscontinueProductResponse,
    LifecycleDetailResponse,
    LifecycleEvaluationRequest,
    LifecycleEvaluationResponse,
    LifecycleHistoryResponse,
    LifecycleListResponse,
    LifecycleSettingItem,
    LifecycleSettingsResetRequest,
    LifecycleSettingsResponse,
    LifecycleSettingsUpdateRequest,
    LifecycleSkuSummary,
    LifecycleSnapshotSchema,
    LifecycleSourceFilter,
    LifecycleStage,
    LifecycleTransitionSummary,
    StageDistributionCounts,
)

logger = logging.getLogger(__name__)
ZERO_MONEY = Decimal("0.00")
ZERO_QTY = Decimal("0.0000")


class LifecycleNotFoundError(KeyError):
    """Raised when a target product_id or stock_code does not exist (HTTP 404)."""


class LifecycleValidationError(ValueError):
    """Raised on out-of-bounds threshold updates or invalid inputs (HTTP 422)."""


class LifecycleGovernanceError(RuntimeError):
    """Raised on workflow governance guard violations (HTTP 409)."""


@dataclass(frozen=True)
class ComputedSkuMetrics:
    """Deterministic demand trajectory metrics for a single SKU at an anchor date."""

    anchor_date: date
    sku_age_days: int
    days_since_last_sale: Optional[int]
    rolling_velocity: Decimal
    prior_rolling_velocity: Decimal
    velocity_trend_pct: Optional[Decimal]
    order_frequency: Decimal
    is_dormant_stock: bool
    raw_candidate_stage: LifecycleStage
    explanation: str


class LifecycleService:
    """Stateless business-logic orchestrator for M08 Product Lifecycle Intelligence."""

    def __init__(
        self,
        repository: LifecycleRepositoryProtocol = lifecycle_repository,
        alerts: AlertPublisherProtocol = alert_publisher,
    ) -> None:
        self._repository = repository
        self._alerts = alerts

    @staticmethod
    def _extract_settings_values(settings: Dict[str, BoundedSettingRecord]) -> Dict[str, Any]:
        # Fall back cleanly to approved defaults if operational_settings is only partially seeded
        # (DATABASE_SCHEMA.md v2.9 explicitly seeds lifecycle_hysteresis_windows & lifecycle_inactivity_days).
        defaults = build_default_lifecycle_settings()

        def _val(key: str) -> Any:
            rec = settings.get(key) or defaults[key]
            return rec.setting_value

        return {
            "lifecycle_hysteresis_windows": int(_val("lifecycle_hysteresis_windows")),
            "lifecycle_inactivity_days": int(_val("lifecycle_inactivity_days")),
            "lifecycle_intro_max_age_days": int(_val("lifecycle_intro_max_age_days")),
            "lifecycle_velocity_window_days": int(_val("lifecycle_velocity_window_days")),
            "lifecycle_growth_velocity_pct": Decimal(str(_val("lifecycle_growth_velocity_pct"))),
            "lifecycle_decline_velocity_pct": Decimal(str(_val("lifecycle_decline_velocity_pct"))),
            "lifecycle_min_order_frequency": Decimal(str(_val("lifecycle_min_order_frequency"))),
        }

    @staticmethod
    def _serialize_settings_for_snapshot(cfg: Dict[str, Any]) -> Dict[str, Any]:
        """Serializes strictly the applied operational_settings threshold snapshot (no undocumented state)."""
        return {
            "lifecycle_hysteresis_windows": cfg["lifecycle_hysteresis_windows"],
            "lifecycle_inactivity_days": cfg["lifecycle_inactivity_days"],
            "lifecycle_intro_max_age_days": cfg["lifecycle_intro_max_age_days"],
            "lifecycle_velocity_window_days": cfg["lifecycle_velocity_window_days"],
            "lifecycle_growth_velocity_pct": str(cfg["lifecycle_growth_velocity_pct"]),
            "lifecycle_decline_velocity_pct": str(cfg["lifecycle_decline_velocity_pct"]),
            "lifecycle_min_order_frequency": str(cfg["lifecycle_min_order_frequency"]),
        }

    @staticmethod
    def _resolve_anchor_date(
        product: ProductLifecycleRecord,
        override_date: Optional[date] = None,
    ) -> date:
        if override_date is not None:
            return override_date
        # Blueprint Module 8H: anchor UCI historical evaluation strictly to 2011-12-09
        if product.source_origin == "uci_historical":
            return UCI_ANCHOR_DATE
        return datetime.now(timezone.utc).date()

    def _compute_metrics(
        self,
        product: ProductLifecycleRecord,
        cfg: Dict[str, Any],
        anchor_date: date,
    ) -> ComputedSkuMetrics:
        sku_age_days = max(0, (anchor_date - product.onboarded_date).days)
        window_days: int = cfg["lifecycle_velocity_window_days"]
        inactivity_days: int = cfg["lifecycle_inactivity_days"]
        intro_max_age: int = cfg["lifecycle_intro_max_age_days"]
        growth_pct: Decimal = cfg["lifecycle_growth_velocity_pct"]
        decline_pct: Decimal = cfg["lifecycle_decline_velocity_pct"]
        min_order_freq: Decimal = cfg["lifecycle_min_order_frequency"]

        # Filter sales up to anchor_date (strictly causal — no future leakage)
        eligible_dates = [d for d, (qty, _) in product.daily_sales.items() if d <= anchor_date and qty > Decimal("0")]
        if eligible_dates:
            last_sale_date = max(eligible_dates)
            days_since_last_sale: Optional[int] = max(0, (anchor_date - last_sale_date).days)
        else:
            days_since_last_sale = None

        curr_start = anchor_date - timedelta(days=window_days - 1)
        prior_end = curr_start - timedelta(days=1)
        prior_start = prior_end - timedelta(days=window_days - 1)

        curr_units = Decimal("0")
        curr_orders = 0
        prior_units = Decimal("0")

        for sale_dt, (qty, orders) in product.daily_sales.items():
            if curr_start <= sale_dt <= anchor_date:
                curr_units += qty
                curr_orders += orders
            elif prior_start <= sale_dt <= prior_end:
                prior_units += qty

        window_dec = Decimal(window_days)
        rolling_velocity = quantize_qty(curr_units / window_dec)
        prior_velocity = quantize_qty(prior_units / window_dec)
        order_frequency = quantize_qty(Decimal(curr_orders) / window_dec)

        # Safe division guard: prior_velocity == 0 yields None (never Inf or NaN)
        if prior_velocity > Decimal("0"):
            trend_pct: Optional[Decimal] = quantize_money(
                ((rolling_velocity - prior_velocity) / prior_velocity) * Decimal("100")
            )
        else:
            trend_pct = None

        # Dormant stock check: active SKU holding positive inventory with extended inactivity
        is_inactive_beyond_window = (
            (days_since_last_sale is not None and days_since_last_sale >= inactivity_days)
            or (days_since_last_sale is None and sku_age_days >= inactivity_days)
        )
        is_dormant_stock = bool(
            product.is_active
            and product.lifecycle_stage != "Discontinued"
            and product.current_quantity > Decimal("0")
            and is_inactive_beyond_window
        )

        # Deterministic DDR-08 raw candidate classification (NEVER returns 'Discontinued')
        if product.lifecycle_stage == "Discontinued":
            raw_stage: LifecycleStage = "Discontinued"
            explanation = "SKU was explicitly marked Discontinued via authorized Store Manager action (DDR-08)."
        elif sku_age_days <= intro_max_age:
            # Cold-start safeguard: newly onboarded SKUs stay in Introduction even with 0 sales
            raw_stage = "Introduction"
            explanation = (
                f"SKU age ({sku_age_days}d) is within the configured Introduction window "
                f"(<= {intro_max_age}d); protected from premature Decline/dead-stock classification."
            )
        elif is_inactive_beyond_window:
            raw_stage = "Decline"
            explanation = (
                f"Established SKU exceeded inactivity threshold ({inactivity_days}d; "
                f"days since last sale={days_since_last_sale}). Flagged as Decline without auto-discontinuation."
            )
        elif prior_velocity == Decimal("0") and rolling_velocity > Decimal("0") and order_frequency >= min_order_freq:
            raw_stage = "Growth"
            explanation = (
                f"Established SKU resumed positive rolling velocity ({rolling_velocity}/day) from a zero prior baseline "
                f"with order frequency {order_frequency}/day (>= {min_order_freq})."
            )
        elif (
            trend_pct is not None
            and trend_pct >= growth_pct
            and order_frequency >= min_order_freq
        ):
            raw_stage = "Growth"
            explanation = (
                f"Rolling velocity grew +{trend_pct}% (>= +{growth_pct}%) with order frequency "
                f"{order_frequency}/day (>= {min_order_freq})."
            )
        elif (trend_pct is not None and trend_pct <= -decline_pct) or rolling_velocity == Decimal("0"):
            raw_stage = "Decline"
            explanation = (
                f"Rolling velocity fell to {rolling_velocity}/day (trend={trend_pct}%, "
                f"decline threshold=-{decline_pct}%)."
            )
        else:
            raw_stage = "Maturity"
            explanation = (
                f"Established SKU maintains steady-state rolling velocity ({rolling_velocity}/day, "
                f"trend={trend_pct}%) within configured Maturity bands."
            )

        return ComputedSkuMetrics(
            anchor_date=anchor_date,
            sku_age_days=sku_age_days,
            days_since_last_sale=days_since_last_sale,
            rolling_velocity=rolling_velocity,
            prior_rolling_velocity=prior_velocity,
            velocity_trend_pct=trend_pct,
            order_frequency=order_frequency,
            is_dormant_stock=is_dormant_stock,
            raw_candidate_stage=raw_stage,
            explanation=explanation,
        )

    @staticmethod
    def _to_snapshot_schema(record: LifecycleSnapshotRecord) -> LifecycleSnapshotSchema:
        return LifecycleSnapshotSchema(
            id=record.id,
            product_id=record.product_id,
            stock_code=record.stock_code,
            lifecycle_stage=record.lifecycle_stage,
            previous_stage=record.previous_stage,
            rolling_velocity=record.rolling_velocity,
            order_frequency=record.order_frequency,
            sku_age_days=record.sku_age_days,
            days_since_last_sale=record.days_since_last_sale,
            is_dormant_stock=record.is_dormant_stock,
            trigger_type=record.trigger_type,
            applied_settings_snapshot=record.applied_settings_snapshot,
            selected_workspace=record.selected_workspace,
            action_source=record.action_source,
            operator_ref=record.operator_ref,
            evaluated_at=record.evaluated_at,
        )

    def _build_sku_summary(
        self,
        product: ProductLifecycleRecord,
        cfg: Dict[str, Any],
        override_date: Optional[date] = None,
    ) -> Tuple[LifecycleSkuSummary, ComputedSkuMetrics]:
        anchor = self._resolve_anchor_date(product, override_date=override_date)
        metrics = self._compute_metrics(product, cfg, anchor)
        latest = self._repository.get_latest_snapshot(product.product_id)

        # If SKU has never been evaluated yet and is not manually Discontinued, show deterministic stage preview
        effective_stage: LifecycleStage = (
            product.lifecycle_stage
            if (latest is not None or product.lifecycle_stage == "Discontinued")
            else metrics.raw_candidate_stage
        )
        pending_stage, consecutive_count = self._repository.get_pending_hysteresis(product.product_id)
        stock_value = quantize_money(product.current_quantity * product.current_unit_price)

        summary = LifecycleSkuSummary(
            product_id=product.product_id,
            stock_code=product.stock_code,
            description=product.description,
            category_name=product.category_name,
            source_origin=product.source_origin,
            currency=product.currency_code,
            is_active=product.is_active,
            lifecycle_stage=effective_stage,
            previous_stage=latest.previous_stage if latest else None,
            pending_candidate_stage=pending_stage if pending_stage != effective_stage else None,
            consecutive_candidate_windows=consecutive_count if pending_stage != effective_stage else 0,
            required_hysteresis_windows=cfg["lifecycle_hysteresis_windows"],
            rolling_velocity=metrics.rolling_velocity,
            prior_rolling_velocity=metrics.prior_rolling_velocity,
            velocity_trend_pct=metrics.velocity_trend_pct,
            order_frequency=metrics.order_frequency,
            sku_age_days=metrics.sku_age_days,
            days_since_last_sale=metrics.days_since_last_sale,
            current_quantity=quantize_qty(product.current_quantity),
            current_unit_price=quantize_money(product.current_unit_price),
            stock_value=stock_value,
            is_dormant_stock=metrics.is_dormant_stock,
            anchor_date=anchor.isoformat(),
            last_evaluated_at=latest.evaluated_at if latest else None,
        )
        return summary, metrics

    def list_lifecycle(
        self,
        *,
        provenance: RequestProvenance,
        source_origin: LifecycleSourceFilter = "all",
        stage: Optional[LifecycleStage] = None,
        is_dormant_stock: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 25,
    ) -> LifecycleListResponse:
        settings = self._repository.get_settings()
        cfg = self._extract_settings_values(settings)
        products = self._repository.list_products(source_origin=source_origin)

        all_summaries: List[LifecycleSkuSummary] = []
        dist = {"Introduction": 0, "Growth": 0, "Maturity": 0, "Decline": 0, "Discontinued": 0}
        dormant_count = 0

        for prod in products:
            summary, _ = self._build_sku_summary(prod, cfg)
            dist[summary.lifecycle_stage] += 1
            if summary.is_dormant_stock:
                dormant_count += 1
            all_summaries.append(summary)

        filtered = all_summaries
        if stage is not None:
            filtered = [s for s in filtered if s.lifecycle_stage == stage]
        if is_dormant_stock is not None:
            filtered = [s for s in filtered if s.is_dormant_stock == is_dormant_stock]
        if search and search.strip():
            q = search.strip().lower()
            filtered = [
                s
                for s in filtered
                if q in s.stock_code.lower() or q in s.description.lower()
            ]

        total = len(filtered)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size
        page_items = filtered[offset : offset + page_size]

        return LifecycleListResponse(
            distribution=StageDistributionCounts(**dist),
            dormant_stock_count=dormant_count,
            anchor_notes={
                "uci_historical": f"Anchored to UCI dataset cutoff ({UCI_ANCHOR_DATE.isoformat()}) rather than wall-clock date.",
                "operational": f"Anchored to current UTC date ({datetime.now(timezone.utc).date().isoformat()}).",
            },
            items=page_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_sku_detail(
        self,
        *,
        product_identifier: Union[int, str],
        provenance: RequestProvenance,
    ) -> LifecycleDetailResponse:
        product = self._repository.get_product(product_identifier)
        if product is None:
            raise LifecycleNotFoundError(f"Product '{product_identifier}' was not found in lifecycle catalog.")

        cfg = self._extract_settings_values(self._repository.get_settings())
        summary, metrics = self._build_sku_summary(product, cfg)
        snapshots = [self._to_snapshot_schema(s) for s in self._repository.get_snapshots(product.product_id)]

        return LifecycleDetailResponse(
            sku=summary,
            classification_explanation=metrics.explanation,
            snapshots=snapshots,
            snapshot_count=len(snapshots),
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_sku_history(
        self,
        *,
        product_identifier: Union[int, str],
        provenance: RequestProvenance,
    ) -> LifecycleHistoryResponse:
        product = self._repository.get_product(product_identifier)
        if product is None:
            raise LifecycleNotFoundError(f"Product '{product_identifier}' was not found in lifecycle catalog.")

        snapshots = [self._to_snapshot_schema(s) for s in self._repository.get_snapshots(product.product_id)]
        return LifecycleHistoryResponse(
            product_id=product.product_id,
            stock_code=product.stock_code,
            current_stage=product.lifecycle_stage,
            snapshots=snapshots,
            total=len(snapshots),
            correlation_id=provenance.correlation_id,
        )

    def evaluate_lifecycle(
        self,
        *,
        request: LifecycleEvaluationRequest,
        provenance: RequestProvenance,
    ) -> LifecycleEvaluationResponse:
        """Executes DDR-08 hysteresis evaluation and appends immutable snapshots."""
        override_date: Optional[date] = None
        if request.as_of_date is not None:
            try:
                override_date = date.fromisoformat(request.as_of_date)
            except ValueError as exc:
                raise LifecycleValidationError(
                    f"Invalid as_of_date '{request.as_of_date}'. Expected ISO format YYYY-MM-DD."
                ) from exc

        settings = self._repository.get_settings()
        cfg = self._extract_settings_values(settings)
        hysteresis_required: int = cfg["lifecycle_hysteresis_windows"]

        products = self._repository.list_products(source_origin=request.source_origin)
        if request.product_ids is not None:
            allowed_ids = set(request.product_ids)
            products = [p for p in products if p.product_id in allowed_ids]
        if request.stock_codes is not None:
            allowed_codes = {c.strip().lower() for c in request.stock_codes}
            products = [p for p in products if p.stock_code.lower() in allowed_codes]

        results: List[LifecycleTransitionSummary] = []
        transitions_committed = 0
        hysteresis_buffered = 0
        skipped_discontinued = 0
        alerts_emitted = 0
        alerts_suppressed = 0

        for product in products:
            # DDR-08 hard guard: automated evaluation NEVER alters or writes 'Discontinued'
            if product.lifecycle_stage == "Discontinued":
                skipped_discontinued += 1
                continue

            anchor = self._resolve_anchor_date(product, override_date=override_date)
            metrics = self._compute_metrics(product, cfg, anchor)
            raw_candidate = metrics.raw_candidate_stage
            latest = self._repository.get_latest_snapshot(product.product_id)

            prev_stage = product.lifecycle_stage
            transitioned = False
            hysteresis_pending = False

            if latest is None:
                # Initial baseline evaluation assigns the deterministic starting stage cleanly
                resulting_stage = raw_candidate
                transitioned = resulting_stage != prev_stage
                pending_stage: Optional[LifecycleStage] = None
                consecutive_count = 0
            elif raw_candidate == prev_stage:
                resulting_stage = prev_stage
                pending_stage = None
                consecutive_count = 0
            else:
                # Apply consecutive-period hysteresis buffer (DDR-08)
                prior_pending, prior_count = self._repository.get_pending_hysteresis(product.product_id)
                new_count = (prior_count + 1) if prior_pending == raw_candidate else 1
                if new_count >= hysteresis_required:
                    resulting_stage = raw_candidate
                    transitioned = True
                    pending_stage = None
                    consecutive_count = 0
                else:
                    resulting_stage = prev_stage
                    hysteresis_pending = True
                    hysteresis_buffered += 1
                    pending_stage = raw_candidate
                    consecutive_count = new_count

            settings_snapshot = self._serialize_settings_for_snapshot(cfg)
            self._repository.set_pending_hysteresis(
                product.product_id,
                pending_stage,
                consecutive_count,
            )

            snap = self._repository.append_evaluation_snapshot(
                product_id=product.product_id,
                new_stage=resulting_stage,
                previous_stage=prev_stage,
                rolling_velocity=metrics.rolling_velocity,
                order_frequency=metrics.order_frequency,
                sku_age_days=metrics.sku_age_days,
                days_since_last_sale=metrics.days_since_last_sale,
                is_dormant_stock=metrics.is_dormant_stock,
                applied_settings_snapshot=settings_snapshot,
                provenance=provenance,
                action_source="SYSTEM" if provenance.action_source == "API" else provenance.action_source,
            )

            if transitioned:
                transitions_committed += 1

            # Dispatch deduplicated SYS-03 alerts on confirmed negative transitions or dormant stock.
            # Alert failures are isolated from committed lifecycle snapshots.
            alert_created = False
            alert_suppressed = False
            sku_lifecycle_dedup_key = f"lifecycle:decline_or_dormant:{product.product_id}"
            try:
                if transitioned and resulting_stage == "Decline" and prev_stage in ("Growth", "Maturity"):
                    _, created = self._alerts.publish(
                        product_id=product.product_id,
                        source_module="lifecycle_intelligence",
                        alert_type="lifecycle_decline_transition",
                        severity="ELEVATED" if product.current_quantity > Decimal("0") else "WARNING",
                        dedup_key=sku_lifecycle_dedup_key,
                        title=f"Lifecycle Decline: {product.stock_code} ({prev_stage} -> Decline)",
                        message=(
                            f"SKU '{product.stock_code}' transitioned from {prev_stage} to Decline after "
                            f"{hysteresis_required} consecutive evaluation window(s). "
                            f"Current stock: {product.current_quantity} units."
                        ),
                        created_source="SYSTEM",
                    )
                    if created:
                        alert_created = True
                        alerts_emitted += 1
                    else:
                        alert_suppressed = True
                        alerts_suppressed += 1
                elif metrics.is_dormant_stock:
                    stock_val = quantize_money(product.current_quantity * product.current_unit_price)
                    _, created = self._alerts.publish(
                        product_id=product.product_id,
                        source_module="lifecycle_intelligence",
                        alert_type="dormant_dead_stock",
                        severity="WARNING",
                        dedup_key=sku_lifecycle_dedup_key,
                        title=f"Dormant Stock Review: {product.stock_code}",
                        message=(
                            f"SKU '{product.stock_code}' holds {product.current_quantity} units "
                            f"({product.currency_code} {stock_val}) with zero recent sales exceeding "
                            f"{cfg['lifecycle_inactivity_days']} days. Review manually (no auto-discontinuation)."
                        ),
                        created_source="SYSTEM",
                    )
                    if created:
                        alert_created = True
                        alerts_emitted += 1
                    else:
                        alert_suppressed = True
                        alerts_suppressed += 1
            except Exception as alert_exc:
                logger.warning(
                    "SYS-03 alert dispatch failed for SKU '%s' (snapshot #%s preserved): %s",
                    product.stock_code,
                    snap.id,
                    alert_exc,
                )

            results.append(
                LifecycleTransitionSummary(
                    product_id=product.product_id,
                    stock_code=product.stock_code,
                    previous_stage=prev_stage,
                    resulting_stage=resulting_stage,
                    raw_candidate_stage=raw_candidate,
                    transitioned=transitioned,
                    hysteresis_pending=hysteresis_pending,
                    is_dormant_stock=metrics.is_dormant_stock,
                    snapshot_id=snap.id,
                    alert_emitted=alert_created,
                    alert_suppressed_duplicate=alert_suppressed,
                )
            )

        return LifecycleEvaluationResponse(
            evaluated_count=len(results),
            transitions_committed=transitions_committed,
            hysteresis_buffered_count=hysteresis_buffered,
            skipped_discontinued_count=skipped_discontinued,
            alerts_emitted=alerts_emitted,
            alerts_suppressed_duplicates=alerts_suppressed,
            applied_settings={k: str(v) for k, v in cfg.items()},
            results=results,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_dead_stock(
        self,
        *,
        provenance: RequestProvenance,
        source_origin: LifecycleSourceFilter = "all",
        page: int = 1,
        page_size: int = 25,
    ) -> DeadStockResponse:
        settings = self._repository.get_settings()
        cfg = self._extract_settings_values(settings)
        inactivity_days: int = cfg["lifecycle_inactivity_days"]

        products = self._repository.list_products(source_origin=source_origin)
        dead_items: List[DeadStockItem] = []
        total_inr = ZERO_MONEY
        total_gbp = ZERO_MONEY

        for prod in products:
            if not prod.is_active or prod.lifecycle_stage == "Discontinued":
                continue
            if prod.current_quantity <= Decimal("0"):
                continue
            summary, metrics = self._build_sku_summary(prod, cfg)
            if not metrics.is_dormant_stock:
                continue

            dead_val = quantize_money(prod.current_quantity * prod.current_unit_price)
            if prod.currency_code == "INR":
                total_inr = quantize_money(total_inr + dead_val)
            else:
                total_gbp = quantize_money(total_gbp + dead_val)

            dead_items.append(
                DeadStockItem(
                    product_id=prod.product_id,
                    stock_code=prod.stock_code,
                    description=prod.description,
                    category_name=prod.category_name,
                    source_origin=prod.source_origin,
                    currency=prod.currency_code,
                    lifecycle_stage=summary.lifecycle_stage,
                    current_quantity=quantize_qty(prod.current_quantity),
                    current_unit_price=quantize_money(prod.current_unit_price),
                    dead_stock_value=dead_val,
                    days_since_last_sale=metrics.days_since_last_sale,
                    sku_age_days=metrics.sku_age_days,
                    anchor_date=metrics.anchor_date.isoformat(),
                    inactivity_threshold_days=inactivity_days,
                )
            )

        # Rank highest tied-up capital first
        dead_items.sort(key=lambda i: (-i.dead_stock_value, i.stock_code))
        total = len(dead_items)
        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size

        return DeadStockResponse(
            inactivity_threshold_days=inactivity_days,
            total_dead_stock_skus=total,
            operational_dead_stock_value_inr=total_inr,
            uci_baseline_dead_stock_value_gbp=total_gbp,
            items=dead_items[offset : offset + page_size],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _enforce_store_manager_governance(provenance: RequestProvenance, action_label: str) -> None:
        """Enforces DDR-08 workflow governance context (UI workspace guard, not security RBAC)."""
        if provenance.selected_workspace != "store_manager":
            raise LifecycleGovernanceError(
                f"Workflow governance guard (DDR-08): '{action_label}' requires "
                "Store Manager (Admin) workspace context (header X-NEXORA-Workspace: store_manager)."
            )

    def discontinue_product(
        self,
        *,
        product_identifier: Union[int, str],
        request: DiscontinueProductRequest,
        provenance: RequestProvenance,
    ) -> DiscontinueProductResponse:
        self._enforce_store_manager_governance(provenance, "Manual Product Discontinuation")

        if not request.confirm_discontinue:
            raise LifecycleValidationError(
                "Explicit confirmation required: 'confirm_discontinue' must be true to mark a SKU Discontinued."
            )

        product = self._repository.get_product(product_identifier)
        if product is None:
            raise LifecycleNotFoundError(f"Product '{product_identifier}' was not found in lifecycle catalog.")

        idem_key = (
            request.idempotency_key.strip()
            if request.idempotency_key and request.idempotency_key.strip()
            else None
        )
        if idem_key is not None:
            existing = self._repository.get_discontinue_idempotency(idem_key)
            if existing is not None:
                if (existing.product_id, existing.reason, existing.operator_ref) != (
                    product.product_id,
                    request.reason,
                    request.operator_ref,
                ):
                    raise LifecycleGovernanceError(
                        f"Idempotency key '{idem_key}' was already used for a different discontinuation request."
                    )
                return DiscontinueProductResponse(
                    product_id=product.product_id,
                    stock_code=product.stock_code,
                    previous_stage=existing.previous_stage,
                    snapshot=self._to_snapshot_schema(existing.snapshot),
                    audit_log_id=existing.audit_log_id,
                    workspace_context=provenance.workspace_label,
                    correlation_id=provenance.correlation_id,
                )

        if product.lifecycle_stage == "Discontinued":
            raise LifecycleGovernanceError(
                f"Product '{product.stock_code}' is already in 'Discontinued' lifecycle stage."
            )

        prev_stage = product.lifecycle_stage
        cfg = self._extract_settings_values(self._repository.get_settings())
        anchor = self._resolve_anchor_date(product)
        metrics = self._compute_metrics(product, cfg, anchor)

        settings_snapshot = self._serialize_settings_for_snapshot(cfg)

        snap, audit_id = self._repository.discontinue_product_atomic(
            product_id=product.product_id,
            rolling_velocity=metrics.rolling_velocity,
            order_frequency=metrics.order_frequency,
            sku_age_days=metrics.sku_age_days,
            days_since_last_sale=metrics.days_since_last_sale,
            is_dormant_stock=metrics.is_dormant_stock,
            applied_settings_snapshot=settings_snapshot,
            reason=request.reason,
            provenance=provenance,
            operator_ref=request.operator_ref,
            idempotency_key=idem_key,
        )

        return DiscontinueProductResponse(
            product_id=product.product_id,
            stock_code=product.stock_code,
            previous_stage=prev_stage,
            snapshot=self._to_snapshot_schema(snap),
            audit_log_id=audit_id,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
        )

    @staticmethod
    def _to_settings_items(settings: Dict[str, BoundedSettingRecord]) -> List[LifecycleSettingItem]:
        return [
            LifecycleSettingItem(
                setting_key=rec.setting_key,
                setting_value=rec.setting_value,
                default_value=rec.default_value,
                min_bound=rec.min_bound,
                max_bound=rec.max_bound,
                value_type=rec.value_type,
                description=rec.description,
                selected_workspace=rec.selected_workspace,
                action_source=rec.action_source,
                operator_ref=rec.operator_ref,
                updated_at=rec.updated_at,
            )
            for rec in settings.values()
        ]

    def get_settings(self, *, provenance: RequestProvenance) -> LifecycleSettingsResponse:
        settings = self._repository.get_settings()
        return LifecycleSettingsResponse(
            settings=self._to_settings_items(settings),
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
        )

    def update_settings(
        self,
        *,
        request: LifecycleSettingsUpdateRequest,
        provenance: RequestProvenance,
    ) -> LifecycleSettingsResponse:
        self._enforce_store_manager_governance(provenance, "Update Lifecycle Threshold Settings")

        current = self._repository.get_settings()
        payload_dict = request.model_dump(exclude={"operator_ref"}, exclude_none=True)
        if not payload_dict:
            raise LifecycleValidationError("Provide at least one lifecycle setting key to update.")

        validated_updates: Dict[str, Union[int, Decimal]] = {}
        violations: List[str] = []

        for key, raw_val in payload_dict.items():
            if key not in current:
                violations.append(f"Unsupported lifecycle setting key '{key}'.")
                continue
            spec = current[key]
            numeric_val = Decimal(str(raw_val))
            if numeric_val < spec.min_bound or numeric_val > spec.max_bound:
                violations.append(
                    f"'{key}' value {raw_val} is outside enforced bounds "
                    f"[{spec.min_bound}, {spec.max_bound}]."
                )
                continue
            if spec.value_type == "INTEGER":
                validated_updates[key] = int(raw_val)
            else:
                validated_updates[key] = quantize_qty(numeric_val) if key == "lifecycle_min_order_frequency" else quantize_money(numeric_val)

        if violations:
            raise LifecycleValidationError(" ".join(violations))

        updated_settings, audit_id = self._repository.update_settings_atomic(
            updates=validated_updates,
            provenance=provenance,
            operator_ref=request.operator_ref,
            action="LIFECYCLE_CONFIG_UPDATED",
        )
        return LifecycleSettingsResponse(
            settings=self._to_settings_items(updated_settings),
            audit_log_id=audit_id,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
        )

    def reset_settings(
        self,
        *,
        request: LifecycleSettingsResetRequest,
        provenance: RequestProvenance,
    ) -> LifecycleSettingsResponse:
        self._enforce_store_manager_governance(provenance, "Reset Lifecycle Threshold Settings")

        current = self._repository.get_settings()
        defaults_map: Dict[str, Union[int, Decimal]] = {
            key: rec.default_value for key, rec in current.items()
        }
        reset_settings, audit_id = self._repository.update_settings_atomic(
            updates=defaults_map,
            provenance=provenance,
            operator_ref=request.operator_ref,
            action="LIFECYCLE_CONFIG_RESET",
        )
        return LifecycleSettingsResponse(
            settings=self._to_settings_items(reset_settings),
            audit_log_id=audit_id,
            workspace_context=provenance.workspace_label,
            correlation_id=provenance.correlation_id,
        )


# Singleton service instance
lifecycle_service = LifecycleService()

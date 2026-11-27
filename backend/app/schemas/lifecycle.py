"""Pydantic v2 Request & Response Schemas for M08 — Product Lifecycle Intelligence.

Strictly enforces the five canonical DDR-08 / DATABASE_SCHEMA.md v2.9 lifecycle stages:
  Introduction, Growth, Maturity, Decline, Discontinued
with `is_dormant_stock` tracked as a distinct boolean flag rather than a 6th stage,
append-only `product_lifecycle_snapshots`, bounded `operational_settings`, and
explicit manual discontinuation with Tier 1 fail-closed auditing (DDR-10).
"""

from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

LifecycleStage = Literal[
    "Introduction",
    "Growth",
    "Maturity",
    "Decline",
    "Discontinued",
]
SnapshotTriggerType = Literal["scheduled_evaluation", "manual_discontinued"]
LifecycleSourceFilter = Literal["uci_historical", "operational", "all"]
CurrencyCode = Literal["GBP", "INR"]
SettingValueType = Literal["DECIMAL", "INTEGER", "STRING", "BOOLEAN", "JSON"]


class LifecycleSnapshotSchema(BaseModel):
    """Immutable snapshot row matching DATABASE_SCHEMA.md v2.9 `product_lifecycle_snapshots`."""

    id: int
    product_id: int
    stock_code: str
    lifecycle_stage: LifecycleStage
    previous_stage: Optional[LifecycleStage] = None
    rolling_velocity: Decimal = Field(..., ge=Decimal("0"))
    order_frequency: Decimal = Field(..., ge=Decimal("0"))
    sku_age_days: int = Field(..., ge=0)
    days_since_last_sale: Optional[int] = Field(None, ge=0)
    is_dormant_stock: bool
    trigger_type: SnapshotTriggerType
    applied_settings_snapshot: Optional[Dict[str, Any]] = None
    selected_workspace: Optional[str] = None
    action_source: str
    operator_ref: Optional[str] = None
    evaluated_at: str


class LifecycleSkuSummary(BaseModel):
    """Portfolio row describing a product's current lifecycle stage and key metrics."""

    product_id: int
    stock_code: str
    description: str
    category_name: Optional[str] = None
    source_origin: Literal["uci_historical", "operational"]
    currency: CurrencyCode
    is_active: bool
    lifecycle_stage: LifecycleStage
    previous_stage: Optional[LifecycleStage] = None
    pending_candidate_stage: Optional[LifecycleStage] = Field(
        None,
        description="Candidate stage awaiting consecutive hysteresis windows before transition commits",
    )
    consecutive_candidate_windows: int = Field(default=0, ge=0)
    required_hysteresis_windows: int = Field(..., ge=1)
    rolling_velocity: Decimal = Field(..., description="Recent rolling daily unit velocity (DECIMAL 14,4)")
    prior_rolling_velocity: Decimal = Field(..., description="Prior window rolling daily unit velocity (DECIMAL 14,4)")
    velocity_trend_pct: Optional[Decimal] = Field(
        None,
        description="Velocity % change vs prior period; null when prior velocity is 0",
    )
    order_frequency: Decimal = Field(..., description="Orders per day across rolling window (DECIMAL 10,4)")
    sku_age_days: int = Field(..., ge=0)
    days_since_last_sale: Optional[int] = Field(None, ge=0)
    current_quantity: Decimal = Field(..., description="Warehouse Physical Stock (base_uom, DECIMAL 14,4)")
    current_unit_price: Decimal = Field(..., description="Catalog unit price (DECIMAL 10,2)")
    stock_value: Decimal = Field(..., description="current_quantity * current_unit_price (DECIMAL 12,2)")
    is_dormant_stock: bool
    anchor_date: str = Field(..., description="Reference date used for age & recency (2011-12-09 for UCI)")
    last_evaluated_at: Optional[str] = None


class StageDistributionCounts(BaseModel):
    """Exact counts across the 5 canonical DDR-08 lifecycle stages."""

    Introduction: int = 0
    Growth: int = 0
    Maturity: int = 0
    Decline: int = 0
    Discontinued: int = 0


class LifecycleListResponse(BaseModel):
    """Response for GET /api/v1/intelligence/lifecycle."""

    distribution: StageDistributionCounts
    dormant_stock_count: int = Field(..., ge=0)
    anchor_notes: Dict[str, str]
    non_auto_discontinued_policy: str = Field(
        default=(
            "Automated lifecycle evaluation never assigns 'Discontinued'. "
            "Transitioning any SKU to 'Discontinued' requires explicit Store Manager (Admin) confirmation (DDR-08)."
        )
    )
    items: List[LifecycleSkuSummary]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)
    workspace_context: Optional[str] = None
    correlation_id: str
    generated_at: str


class LifecycleDetailResponse(BaseModel):
    """Response for GET /api/v1/intelligence/lifecycle/{product_id}."""

    sku: LifecycleSkuSummary
    classification_explanation: str
    snapshots: List[LifecycleSnapshotSchema]
    snapshot_count: int = Field(..., ge=0)
    workspace_context: Optional[str] = None
    correlation_id: str
    generated_at: str


class LifecycleHistoryResponse(BaseModel):
    """Response for GET /api/v1/intelligence/lifecycle/{product_id}/history."""

    product_id: int
    stock_code: str
    current_stage: LifecycleStage
    snapshots: List[LifecycleSnapshotSchema]
    total: int = Field(..., ge=0)
    immutability_notice: str = Field(
        default=(
            "Historical product_lifecycle_snapshots are append-only and immutable; "
            "future threshold updates never retroactively rewrite prior snapshots (DDR-08)."
        )
    )
    correlation_id: str


class LifecycleEvaluationRequest(BaseModel):
    """Optional parameters for POST /api/v1/intelligence/lifecycle/evaluate."""

    source_origin: LifecycleSourceFilter = Field(default="all")
    product_ids: Optional[List[int]] = Field(default=None, description="Optional subset of product IDs to evaluate")
    stock_codes: Optional[List[str]] = Field(default=None, description="Optional subset of stock codes to evaluate")
    as_of_date: Optional[str] = Field(
        default=None,
        description="Optional ISO date override (YYYY-MM-DD); UCI defaults to 2011-12-09 anchor",
    )


class LifecycleTransitionSummary(BaseModel):
    """Summary of an individual SKU evaluated during a batch evaluation run."""

    product_id: int
    stock_code: str
    previous_stage: LifecycleStage
    resulting_stage: LifecycleStage
    raw_candidate_stage: LifecycleStage
    transitioned: bool
    hysteresis_pending: bool
    is_dormant_stock: bool
    snapshot_id: int
    alert_emitted: bool
    alert_suppressed_duplicate: bool


class LifecycleEvaluationResponse(BaseModel):
    """Response for POST /api/v1/intelligence/lifecycle/evaluate."""

    evaluated_count: int = Field(..., ge=0)
    transitions_committed: int = Field(..., ge=0)
    hysteresis_buffered_count: int = Field(..., ge=0)
    skipped_discontinued_count: int = Field(..., ge=0)
    alerts_emitted: int = Field(..., ge=0)
    alerts_suppressed_duplicates: int = Field(..., ge=0)
    applied_settings: Dict[str, Any]
    results: List[LifecycleTransitionSummary]
    workspace_context: Optional[str] = None
    correlation_id: str
    evaluated_at: str


class DeadStockItem(BaseModel):
    """Active SKU holding positive warehouse stock beyond inactivity threshold."""

    product_id: int
    stock_code: str
    description: str
    category_name: Optional[str] = None
    source_origin: Literal["uci_historical", "operational"]
    currency: CurrencyCode
    lifecycle_stage: LifecycleStage
    current_quantity: Decimal
    current_unit_price: Decimal
    dead_stock_value: Decimal = Field(..., description="current_quantity * current_unit_price (DECIMAL 12,2)")
    days_since_last_sale: Optional[int] = None
    sku_age_days: int
    anchor_date: str
    inactivity_threshold_days: int


class DeadStockResponse(BaseModel):
    """Response for GET /api/v1/intelligence/dead-stock."""

    inactivity_threshold_days: int
    total_dead_stock_skus: int = Field(..., ge=0)
    operational_dead_stock_value_inr: Decimal
    uci_baseline_dead_stock_value_gbp: Decimal
    currency_blending_prohibited: bool = True
    policy_notice: str = Field(
        default=(
            "Dead-stock items remain active and are never auto-discontinued (DDR-08). "
            "Autonomous price markdowns are explicitly excluded (EXCL-04)."
        )
    )
    items: List[DeadStockItem]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)
    workspace_context: Optional[str] = None
    correlation_id: str
    generated_at: str


class DiscontinueProductRequest(BaseModel):
    """Explicit manual confirmation payload to transition a SKU to `Discontinued`."""

    confirm_discontinue: bool = Field(
        ...,
        description="Must be explicitly true to confirm manual discontinuation (DDR-08)",
    )
    reason: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Mandatory human justification recorded in Tier 1 audit_logs",
    )
    operator_ref: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Optional non-authenticated attribution reference (never implies login)",
    )

    @field_validator("reason")
    @classmethod
    def validate_non_blank_reason(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("A non-blank discontinuation reason (at least 3 characters) is required.")
        return cleaned


class DiscontinueProductResponse(BaseModel):
    """Response for PATCH /api/v1/intelligence/lifecycle/{product_id}/discontinue."""

    product_id: int
    stock_code: str
    previous_stage: LifecycleStage
    lifecycle_stage: Literal["Discontinued"] = "Discontinued"
    snapshot: LifecycleSnapshotSchema
    audit_log_id: int
    excl_04_notice: str = Field(
        default="Discontinuation updates lifecycle status only; zero autonomous price markdowns were triggered (EXCL-04)."
    )
    workspace_context: Optional[str] = None
    correlation_id: str


class LifecycleSettingItem(BaseModel):
    """Single bounded lifecycle setting matching `operational_settings` DDL."""

    setting_key: str
    setting_value: Union[int, Decimal]
    default_value: Union[int, Decimal]
    min_bound: Decimal
    max_bound: Decimal
    value_type: SettingValueType
    domain: Literal["lifecycle"] = "lifecycle"
    description: str
    selected_workspace: Optional[str] = None
    action_source: str
    operator_ref: Optional[str] = None
    updated_at: str


class LifecycleSettingsResponse(BaseModel):
    """Response for GET / PUT / POST reset on /api/v1/settings/lifecycle."""

    domain: Literal["lifecycle"] = "lifecycle"
    forward_only_notice: str = Field(
        default=(
            "Threshold changes apply strictly to future evaluations and never rewrite "
            "existing historical product_lifecycle_snapshots (DDR-08)."
        )
    )
    settings: List[LifecycleSettingItem]
    audit_log_id: Optional[int] = None
    workspace_context: Optional[str] = None
    correlation_id: str


class LifecycleSettingsUpdateRequest(BaseModel):
    """Partial or full bounded update payload for PUT /api/v1/settings/lifecycle."""

    lifecycle_hysteresis_windows: Optional[int] = None
    lifecycle_inactivity_days: Optional[int] = None
    lifecycle_intro_max_age_days: Optional[int] = None
    lifecycle_velocity_window_days: Optional[int] = None
    lifecycle_growth_velocity_pct: Optional[Decimal] = None
    lifecycle_decline_velocity_pct: Optional[Decimal] = None
    lifecycle_min_order_frequency: Optional[Decimal] = None
    operator_ref: Optional[str] = Field(default=None, max_length=64)


class LifecycleSettingsResetRequest(BaseModel):
    """Optional attribution payload for POST /api/v1/settings/lifecycle/reset."""

    operator_ref: Optional[str] = Field(default=None, max_length=64)

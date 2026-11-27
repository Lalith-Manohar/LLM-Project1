"""Pydantic v2 Request & Response Schemas for M06 — Business Intelligence.

Enforces exact DECIMAL precision (no float drift for monetary/quantity totals),
strict separation of UCI historical (GBP, 2009–2011) and operational (INR) data
streams per Technical Blueprint v2.2 (Module 6 & DDR-04) and DATABASE_SCHEMA.md v2.9.
"""

from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

SourceOriginFilter = Literal["uci_historical", "operational", "all"]
SingleSourceOrigin = Literal["uci_historical", "operational"]
CurrencyCode = Literal["GBP", "INR"]
GranularityType = Literal["day", "week", "month"]
SkuRankingOrder = Literal["top", "slowest"]
SkuRankingSortBy = Literal["revenue", "quantity", "order_count"]
ComparisonPeriodType = Literal["mom", "qoq", "yoy"]


class DataSpanMetadata(BaseModel):
    """Explicit temporal coverage and empty-state disclosure for a data source."""

    start_date: Optional[str] = Field(None, description="Earliest transaction date in filtered result (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Latest transaction date in filtered result (YYYY-MM-DD)")
    record_count: int = Field(..., ge=0, description="Total transaction line items across all filtered streams")
    has_data: bool = Field(..., description="Whether at least one matching record exists")
    empty_state_reason: Optional[str] = Field(
        None,
        description="Explicit explanation when no records match the selected source/filters",
    )


class SourceKpiBlock(BaseModel):
    """Executive KPI summary isolated to a single source_origin and currency."""

    model_config = ConfigDict(ser_json_timedelta="iso8601")

    source_origin: SingleSourceOrigin
    currency: CurrencyCode
    label: str = Field(..., description="Human-readable data source label (prevents misrepresenting UCI as live)")
    data_span: DataSpanMetadata
    gross_revenue: Decimal = Field(..., description="Gross revenue from valid positive sales stream only (DECIMAL 12,2)")
    return_amount: Decimal = Field(..., description="Absolute monetary value of return/credit stream (DECIMAL 12,2)")
    cancellation_amount: Decimal = Field(..., description="Absolute monetary value of 'C'-prefix cancellations (DECIMAL 12,2)")
    net_revenue: Decimal = Field(..., description="Gross revenue minus returns and cancellations (DECIMAL 12,2)")
    gross_units_sold: Decimal = Field(..., description="Positive valid units sold (DECIMAL 14,4)")
    return_units: Decimal = Field(..., description="Absolute returned units (DECIMAL 14,4)")
    cancellation_units: Decimal = Field(..., description="Absolute cancelled units (DECIMAL 14,4)")
    net_units_sold: Decimal = Field(..., description="Gross units minus returns and cancellations (DECIMAL 14,4)")
    unique_order_count: int = Field(..., ge=0, description="Distinct positive sales invoices/orders")
    active_sku_count: int = Field(..., ge=0, description="Distinct SKUs with valid positive sales in window")
    average_order_value: Optional[Decimal] = Field(
        None,
        description="Gross revenue / unique_order_count; null when unique_order_count is 0",
    )
    return_rate_pct: Optional[Decimal] = Field(
        None,
        description="Return amount as % of gross revenue; null when gross revenue is 0",
    )
    cancellation_rate_pct: Optional[Decimal] = Field(
        None,
        description="Cancellation amount as % of gross revenue; null when gross revenue is 0",
    )


class AnalyticsSummaryResponse(BaseModel):
    """Response for GET /api/v1/analytics/summary."""

    source_origin_filter: SourceOriginFilter
    currency_blending_prohibited: bool = Field(
        default=True,
        description="Guarantees GBP UCI historical and INR operational totals are never silently summed together",
    )
    currency_notice: str
    filters_applied: Dict[str, Any]
    uci_historical: Optional[SourceKpiBlock] = None
    operational: Optional[SourceKpiBlock] = None
    workspace_context: Optional[str] = None
    correlation_id: str
    generated_at: str


class TimeSeriesPoint(BaseModel):
    """Single aggregated time bucket for Chart.js / SVG visualization."""

    period_key: str = Field(..., description="Bucket key (YYYY-MM-DD, YYYY-Www, or YYYY-MM)")
    period_start: str = Field(..., description="Inclusive bucket start date (YYYY-MM-DD)")
    period_end: str = Field(..., description="Inclusive bucket end date (YYYY-MM-DD)")
    gross_revenue: Decimal
    return_amount: Decimal
    cancellation_amount: Decimal
    net_revenue: Decimal
    gross_units: Decimal
    net_units: Decimal
    order_count: int = Field(..., ge=0)


class SourceTimeSeriesBlock(BaseModel):
    """Time-series trajectory isolated to a single source_origin and currency."""

    source_origin: SingleSourceOrigin
    currency: CurrencyCode
    granularity: GranularityType
    label: str
    data_span: DataSpanMetadata
    points: List[TimeSeriesPoint]


class AnalyticsTimeSeriesResponse(BaseModel):
    """Response for GET /api/v1/analytics/timeseries."""

    source_origin_filter: SourceOriginFilter
    granularity: GranularityType
    currency_blending_prohibited: bool = True
    currency_notice: str
    filters_applied: Dict[str, Any]
    uci_historical: Optional[SourceTimeSeriesBlock] = None
    operational: Optional[SourceTimeSeriesBlock] = None
    workspace_context: Optional[str] = None
    correlation_id: str
    generated_at: str


class CountryBreakdownItem(BaseModel):
    """Geographical revenue and volume slice for a single country."""

    country: str
    gross_revenue: Decimal
    return_amount: Decimal
    cancellation_amount: Decimal
    net_revenue: Decimal
    gross_units: Decimal
    order_count: int = Field(..., ge=0)
    revenue_share_pct: Decimal = Field(..., description="Percentage share of total gross revenue within source")


class SourceCountryBlock(BaseModel):
    """Country breakdown isolated to a single source_origin and currency."""

    source_origin: SingleSourceOrigin
    currency: CurrencyCode
    label: str
    data_span: DataSpanMetadata
    total_countries: int = Field(..., ge=0)
    total_gross_revenue: Decimal
    countries: List[CountryBreakdownItem]


class AnalyticsCountriesResponse(BaseModel):
    """Response for GET /api/v1/analytics/countries."""

    source_origin_filter: SourceOriginFilter
    currency_blending_prohibited: bool = True
    currency_notice: str
    filters_applied: Dict[str, Any]
    uci_historical: Optional[SourceCountryBlock] = None
    operational: Optional[SourceCountryBlock] = None
    workspace_context: Optional[str] = None
    correlation_id: str
    generated_at: str


class SkuRankingItem(BaseModel):
    """Product-level velocity, stream breakdown, and slow-moving indicator."""

    rank: int = Field(..., ge=1)
    product_id: Optional[int] = None
    stock_code: str
    description: str
    category_name: Optional[str] = None
    gross_units: Decimal
    return_units: Decimal
    cancellation_units: Decimal
    net_units: Decimal
    gross_revenue: Decimal
    return_amount: Decimal
    cancellation_amount: Decimal
    net_revenue: Decimal
    order_count: int = Field(..., ge=0)
    avg_daily_velocity: Decimal = Field(..., description="Gross units divided by observed window days")
    current_inventory_qty: Optional[Decimal] = Field(
        None,
        description="Live Physical Stock when available from M09 inventory; null for UCI historical baseline",
    )
    is_slow_moving: bool = Field(
        ...,
        description="True when velocity is below catalog median (distinct from M08 Decline/Discontinued stages)",
    )


class SourceSkuRankingBlock(BaseModel):
    """Paginated SKU ranking block isolated to a single source_origin and currency."""

    source_origin: SingleSourceOrigin
    currency: CurrencyCode
    label: str
    data_span: DataSpanMetadata
    catalog_median_daily_velocity: Decimal
    items: List[SkuRankingItem]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_pages: int = Field(..., ge=0)


class AnalyticsSkuRankingsResponse(BaseModel):
    """Response for GET /api/v1/analytics/sku-rankings."""

    source_origin_filter: SourceOriginFilter
    order: SkuRankingOrder
    sort_by: SkuRankingSortBy
    currency_blending_prohibited: bool = True
    currency_notice: str
    lifecycle_separation_notice: str = Field(
        default=(
            "Slow-moving rankings measure relative sales velocity within the selected filter window "
            "and are distinct from M08 Product Lifecycle stages (Decline/dormant or manual Discontinued)."
        )
    )
    filters_applied: Dict[str, Any]
    uci_historical: Optional[SourceSkuRankingBlock] = None
    operational: Optional[SourceSkuRankingBlock] = None
    workspace_context: Optional[str] = None
    correlation_id: str
    generated_at: str


class PeriodMetricComparison(BaseModel):
    """Variance metrics between current and previous comparison windows."""

    metric_key: str
    label: str
    unit: str
    current_value: Decimal
    previous_value: Decimal
    absolute_delta: Decimal
    delta_pct: Optional[Decimal] = Field(
        None,
        description="Percentage change vs previous period; strictly null when previous_value == 0",
    )


class SourceComparisonBlock(BaseModel):
    """Period-over-period comparison isolated to a single source_origin and currency."""

    source_origin: SingleSourceOrigin
    currency: CurrencyCode
    label: str
    period_type: ComparisonPeriodType
    current_period_label: str
    previous_period_label: str
    current_span: DataSpanMetadata
    previous_span: DataSpanMetadata
    has_comparison_baseline: bool
    coverage_notice: Optional[str] = None
    metrics: List[PeriodMetricComparison]


class AnalyticsComparisonsResponse(BaseModel):
    """Response for GET /api/v1/analytics/comparisons."""

    source_origin_filter: SourceOriginFilter
    period_type: ComparisonPeriodType
    currency_blending_prohibited: bool = True
    currency_notice: str
    filters_applied: Dict[str, Any]
    uci_historical: Optional[SourceComparisonBlock] = None
    operational: Optional[SourceComparisonBlock] = None
    workspace_context: Optional[str] = None
    correlation_id: str
    generated_at: str

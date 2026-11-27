/**
 * TypeScript interfaces for M06 — Business Intelligence.
 * Strictly aligned 1:1 with backend `app.schemas.analytics` (Decimal fields serialized as strings).
 */

export type SourceOriginFilter = 'uci_historical' | 'operational' | 'all'
export type SingleSourceOrigin = 'uci_historical' | 'operational'
export type CurrencyCode = 'GBP' | 'INR'
export type GranularityType = 'day' | 'week' | 'month'
export type SkuRankingOrder = 'top' | 'slowest'
export type SkuRankingSortBy = 'revenue' | 'quantity' | 'order_count'
export type ComparisonPeriodType = 'mom' | 'qoq' | 'yoy'

export interface DataSpanMetadata {
  start_date: string | null
  end_date: string | null
  record_count: number
  has_data: boolean
  empty_state_reason: string | null
}

export interface SourceKpiBlock {
  source_origin: SingleSourceOrigin
  currency: CurrencyCode
  label: string
  data_span: DataSpanMetadata
  gross_revenue: string
  return_amount: string
  cancellation_amount: string
  net_revenue: string
  gross_units_sold: string
  return_units: string
  cancellation_units: string
  net_units_sold: string
  unique_order_count: number
  active_sku_count: number
  average_order_value: string | null
  return_rate_pct: string | null
  cancellation_rate_pct: string | null
}

export interface AnalyticsSummaryResponse {
  source_origin_filter: SourceOriginFilter
  currency_blending_prohibited: boolean
  currency_notice: string
  filters_applied: Record<string, unknown>
  uci_historical: SourceKpiBlock | null
  operational: SourceKpiBlock | null
  workspace_context: string | null
  correlation_id: string
  generated_at: string
}

export interface TimeSeriesPoint {
  period_key: string
  period_start: string
  period_end: string
  gross_revenue: string
  return_amount: string
  cancellation_amount: string
  net_revenue: string
  gross_units: string
  net_units: string
  order_count: number
}

export interface SourceTimeSeriesBlock {
  source_origin: SingleSourceOrigin
  currency: CurrencyCode
  granularity: GranularityType
  label: string
  data_span: DataSpanMetadata
  points: TimeSeriesPoint[]
}

export interface AnalyticsTimeSeriesResponse {
  source_origin_filter: SourceOriginFilter
  granularity: GranularityType
  currency_blending_prohibited: boolean
  currency_notice: string
  filters_applied: Record<string, unknown>
  uci_historical: SourceTimeSeriesBlock | null
  operational: SourceTimeSeriesBlock | null
  workspace_context: string | null
  correlation_id: string
  generated_at: string
}

export interface CountryBreakdownItem {
  country: string
  gross_revenue: string
  return_amount: string
  cancellation_amount: string
  net_revenue: string
  gross_units: string
  order_count: number
  revenue_share_pct: string
}

export interface SourceCountryBlock {
  source_origin: SingleSourceOrigin
  currency: CurrencyCode
  label: string
  data_span: DataSpanMetadata
  total_countries: number
  total_gross_revenue: string
  countries: CountryBreakdownItem[]
}

export interface AnalyticsCountriesResponse {
  source_origin_filter: SourceOriginFilter
  currency_blending_prohibited: boolean
  currency_notice: string
  filters_applied: Record<string, unknown>
  uci_historical: SourceCountryBlock | null
  operational: SourceCountryBlock | null
  workspace_context: string | null
  correlation_id: string
  generated_at: string
}

export interface SkuRankingItem {
  rank: number
  product_id: number | null
  stock_code: string
  description: string
  category_name: string | null
  gross_units: string
  return_units: string
  cancellation_units: string
  net_units: string
  gross_revenue: string
  return_amount: string
  cancellation_amount: string
  net_revenue: string
  order_count: number
  avg_daily_velocity: string
  current_inventory_qty: string | null
  is_slow_moving: boolean
}

export interface SourceSkuRankingBlock {
  source_origin: SingleSourceOrigin
  currency: CurrencyCode
  label: string
  data_span: DataSpanMetadata
  catalog_median_daily_velocity: string
  items: SkuRankingItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface AnalyticsSkuRankingsResponse {
  source_origin_filter: SourceOriginFilter
  order: SkuRankingOrder
  sort_by: SkuRankingSortBy
  currency_blending_prohibited: boolean
  currency_notice: string
  lifecycle_separation_notice: string
  filters_applied: Record<string, unknown>
  uci_historical: SourceSkuRankingBlock | null
  operational: SourceSkuRankingBlock | null
  workspace_context: string | null
  correlation_id: string
  generated_at: string
}

export interface PeriodMetricComparison {
  metric_key: string
  label: string
  unit: string
  current_value: string
  previous_value: string
  absolute_delta: string
  delta_pct: string | null
}

export interface SourceComparisonBlock {
  source_origin: SingleSourceOrigin
  currency: CurrencyCode
  label: string
  period_type: ComparisonPeriodType
  current_period_label: string
  previous_period_label: string
  current_span: DataSpanMetadata
  previous_span: DataSpanMetadata
  has_comparison_baseline: boolean
  coverage_notice: string | null
  metrics: PeriodMetricComparison[]
}

export interface AnalyticsComparisonsResponse {
  source_origin_filter: SourceOriginFilter
  period_type: ComparisonPeriodType
  currency_blending_prohibited: boolean
  currency_notice: string
  filters_applied: Record<string, unknown>
  uci_historical: SourceComparisonBlock | null
  operational: SourceComparisonBlock | null
  workspace_context: string | null
  correlation_id: string
  generated_at: string
}

export interface AnalyticsFilterParams {
  source_origin: SourceOriginFilter
  start_date?: string
  end_date?: string
  country?: string
  category_id?: number
  stock_code?: string
  granularity?: GranularityType
  order?: SkuRankingOrder
  sort_by?: SkuRankingSortBy
  period_type?: ComparisonPeriodType
  page?: number
  page_size?: number
  limit?: number
}

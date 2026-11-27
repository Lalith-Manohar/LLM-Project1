/**
 * TypeScript interfaces for M08 — Product Lifecycle Intelligence.
 * Strictly aligned 1:1 with backend `app.schemas.lifecycle` and DATABASE_SCHEMA.md v2.9.
 */

export type LifecycleStage =
  | 'Introduction'
  | 'Growth'
  | 'Maturity'
  | 'Decline'
  | 'Discontinued'

export type LifecycleSourceFilter = 'uci_historical' | 'operational' | 'all'
export type CurrencyCode = 'GBP' | 'INR'

export interface LifecycleSnapshot {
  id: number
  product_id: number
  stock_code: string
  lifecycle_stage: LifecycleStage
  previous_stage: LifecycleStage | null
  rolling_velocity: string
  order_frequency: string
  sku_age_days: number
  days_since_last_sale: number | null
  is_dormant_stock: boolean
  trigger_type: 'scheduled_evaluation' | 'manual_discontinued'
  applied_settings_snapshot: Record<string, unknown> | null
  selected_workspace: string | null
  action_source: string
  operator_ref: string | null
  evaluated_at: string
}

export interface LifecycleSkuSummary {
  product_id: number
  stock_code: string
  description: string
  category_name: string | null
  source_origin: 'uci_historical' | 'operational'
  currency: CurrencyCode
  is_active: boolean
  lifecycle_stage: LifecycleStage
  previous_stage: LifecycleStage | null
  pending_candidate_stage: LifecycleStage | null
  consecutive_candidate_windows: number
  required_hysteresis_windows: number
  rolling_velocity: string
  prior_rolling_velocity: string
  velocity_trend_pct: string | null
  order_frequency: string
  sku_age_days: number
  days_since_last_sale: number | null
  current_quantity: string
  current_unit_price: string
  stock_value: string
  is_dormant_stock: boolean
  anchor_date: string
  last_evaluated_at: string | null
}

export interface StageDistributionCounts {
  Introduction: number
  Growth: number
  Maturity: number
  Decline: number
  Discontinued: number
}

export interface LifecycleListResponse {
  distribution: StageDistributionCounts
  dormant_stock_count: number
  anchor_notes: Record<string, string>
  non_auto_discontinued_policy: string
  items: LifecycleSkuSummary[]
  total: number
  page: number
  page_size: number
  total_pages: number
  workspace_context: string | null
  correlation_id: string
  generated_at: string
}

export interface LifecycleDetailResponse {
  sku: LifecycleSkuSummary
  classification_explanation: string
  snapshots: LifecycleSnapshot[]
  snapshot_count: number
  workspace_context: string | null
  correlation_id: string
  generated_at: string
}

export interface LifecycleEvaluationResponse {
  evaluated_count: number
  transitions_committed: number
  hysteresis_buffered_count: number
  skipped_discontinued_count: number
  alerts_emitted: number
  alerts_suppressed_duplicates: number
  applied_settings: Record<string, string>
  results: Array<{
    product_id: number
    stock_code: string
    previous_stage: LifecycleStage
    resulting_stage: LifecycleStage
    raw_candidate_stage: LifecycleStage
    transitioned: boolean
    hysteresis_pending: boolean
    is_dormant_stock: boolean
    snapshot_id: number
    alert_emitted: boolean
    alert_suppressed_duplicate: boolean
  }>
  workspace_context: string | null
  correlation_id: string
  evaluated_at: string
}

export interface DeadStockItem {
  product_id: number
  stock_code: string
  description: string
  category_name: string | null
  source_origin: 'uci_historical' | 'operational'
  currency: CurrencyCode
  lifecycle_stage: LifecycleStage
  current_quantity: string
  current_unit_price: string
  dead_stock_value: string
  days_since_last_sale: number | null
  sku_age_days: number
  anchor_date: string
  inactivity_threshold_days: number
}

export interface DeadStockResponse {
  inactivity_threshold_days: number
  total_dead_stock_skus: number
  operational_dead_stock_value_inr: string
  uci_baseline_dead_stock_value_gbp: string
  currency_blending_prohibited: boolean
  policy_notice: string
  items: DeadStockItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
  workspace_context: string | null
  correlation_id: string
  generated_at: string
}

export interface DiscontinueProductRequest {
  confirm_discontinue: boolean
  reason: string
  operator_ref?: string
  idempotency_key?: string
}

export interface DiscontinueProductResponse {
  product_id: number
  stock_code: string
  previous_stage: LifecycleStage
  lifecycle_stage: 'Discontinued'
  snapshot: LifecycleSnapshot
  audit_log_id: number
  excl_04_notice: string
  workspace_context: string | null
  correlation_id: string
}

export interface LifecycleSettingItem {
  setting_key: string
  setting_value: number | string
  default_value: number | string
  min_bound: string
  max_bound: string
  value_type: 'DECIMAL' | 'INTEGER' | 'STRING' | 'BOOLEAN' | 'JSON'
  domain: 'lifecycle'
  description: string
  selected_workspace: string | null
  action_source: string
  operator_ref: string | null
  updated_at: string
}

export interface LifecycleSettingsResponse {
  domain: 'lifecycle'
  forward_only_notice: string
  settings: LifecycleSettingItem[]
  audit_log_id: number | null
  workspace_context: string | null
  correlation_id: string
}

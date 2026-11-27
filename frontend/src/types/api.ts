/**
 * TypeScript interfaces strictly matching verified live FastAPI schemas
 * in backend/app/main.py and backend/app/schemas/forecast.py.
 */

export interface HealthResponse {
  status: string
  service: string
  version: string
}

export interface ComponentReadiness {
  ready: boolean
  models_count?: number | null
  loaded_horizons?: number[] | null
  total_skus?: number | null
  total_records?: number | null
  dataset_file?: string | null
  demand_data_ready?: boolean | null
  price_service_ready?: boolean | null
  models_dir?: string | null
  price_service?: Record<string, unknown> | null
  error?: string | null
}

export interface ReadinessResponse {
  status: string
  service: string
  version: string
  models: ComponentReadiness
  historical_data: ComponentReadiness
  experimental_models?: ComponentReadiness | null
}

/**
 * TypeScript interface definitions matching NEXORA backend Pydantic schemas.
 * (app.schemas.forecast)
 */

export interface HistoricalFeatures {
  day_of_week?: number;
  month?: number;
  day_of_month?: number;
  lag_1: number;
  lag_7: number;
  lag_14: number;
  lag_28: number;
  rolling_mean_7: number;
  rolling_mean_28: number;
}

export interface ForecastRequest {
  stock_code: string;
  horizons?: number[];
  features?: HistoricalFeatures;
  // Flat fallback fields
  day_of_week?: number;
  month?: number;
  day_of_month?: number;
  lag_1?: number;
  lag_7?: number;
  lag_14?: number;
  lag_28?: number;
  rolling_mean_7?: number;
  rolling_mean_28?: number;
}

export interface HorizonPredictionDetail {
  horizon_days: number;
  predicted_demand: number;
  model_name: string;
  wape?: number;
}

export interface ForecastResponse {
  stock_code: string;
  horizons: number[];
  predictions: Record<string, number>;
  horizon_details: HorizonPredictionDetail[];
  units: string;
  model_version: string;
  timestamp: string;
  warnings: string[];
  status: string;
  observation_date?: string;
  history_days?: number;
  is_auto_generated?: boolean;
  total_predicted_demand?: number;
  horizon_days?: number;
}

export interface SupportedHorizonsResponse {
  supported_horizons_days: number[];
  description: string;
  horizon_definitions: Record<string, string>;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

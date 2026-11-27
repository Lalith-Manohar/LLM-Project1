import { apiClient } from '@/services/api/client'
import type { HealthResponse, ReadinessResponse } from '@/types/api'

/** Calls live FastAPI liveness probe GET /health. */
export async function fetchHealthStatus(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>('/health')
  return data
}

/** Calls live FastAPI readiness probe GET /ready (handles 503 payloads if needed). */
export async function fetchReadinessStatus(): Promise<ReadinessResponse> {
  const { data } = await apiClient.get<ReadinessResponse>('/ready')
  return data
}

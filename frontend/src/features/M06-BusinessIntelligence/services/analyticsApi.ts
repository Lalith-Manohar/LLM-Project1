import axios from 'axios'
import { apiClient } from '@/services/api/client'
import type { WorkspaceId } from '@/types/workspace'
import type {
  AnalyticsComparisonsResponse,
  AnalyticsCountriesResponse,
  AnalyticsFilterParams,
  AnalyticsSkuRankingsResponse,
  AnalyticsSummaryResponse,
  AnalyticsTimeSeriesResponse,
} from '../types'

/** Extracts structured FastAPI / Pydantic v2 error messages cleanly without swallowing status codes. */
export function formatAnalyticsApiError(err: unknown): {
  status: number | null
  message: string
} {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status ?? null
    const detail = (err.response?.data as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') {
      return { status, message: detail }
    }
    if (Array.isArray(detail)) {
      const joined = detail
        .map((item) => {
          const d = item as { loc?: unknown[]; msg?: string }
          const field = Array.isArray(d.loc) ? d.loc.join('.') : 'Field'
          return `${field}: ${d.msg ?? 'Validation error'}`
        })
        .join('; ')
      return { status, message: joined }
    }
    return { status, message: err.message || 'Analytics API request failed.' }
  }
  return {
    status: null,
    message: err instanceof Error ? err.message : 'Unexpected analytics error.',
  }
}

function cleanParams(params: Record<string, string | number | undefined>) {
  const cleaned: Record<string, string | number> = {}
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined && val !== '') {
      cleaned[key] = val
    }
  }
  return cleaned
}

function workspaceHeaders(workspace: WorkspaceId) {
  return { 'X-NEXORA-Workspace': workspace }
}

export async function fetchAnalyticsSummary(
  params: AnalyticsFilterParams,
  workspace: WorkspaceId
): Promise<AnalyticsSummaryResponse> {
  const { data } = await apiClient.get<AnalyticsSummaryResponse>('/api/v1/analytics/summary', {
    params: cleanParams({
      source_origin: params.source_origin,
      start_date: params.start_date,
      end_date: params.end_date,
      country: params.country,
      category_id: params.category_id,
      stock_code: params.stock_code,
    }),
    headers: workspaceHeaders(workspace),
  })
  return data
}

export async function fetchAnalyticsTimeSeries(
  params: AnalyticsFilterParams,
  workspace: WorkspaceId
): Promise<AnalyticsTimeSeriesResponse> {
  const { data } = await apiClient.get<AnalyticsTimeSeriesResponse>(
    '/api/v1/analytics/timeseries',
    {
      params: cleanParams({
        source_origin: params.source_origin,
        granularity: params.granularity || 'month',
        start_date: params.start_date,
        end_date: params.end_date,
        country: params.country,
        category_id: params.category_id,
        stock_code: params.stock_code,
      }),
      headers: workspaceHeaders(workspace),
    }
  )
  return data
}

export async function fetchAnalyticsCountries(
  params: AnalyticsFilterParams,
  workspace: WorkspaceId
): Promise<AnalyticsCountriesResponse> {
  const { data } = await apiClient.get<AnalyticsCountriesResponse>(
    '/api/v1/analytics/countries',
    {
      params: cleanParams({
        source_origin: params.source_origin,
        start_date: params.start_date,
        end_date: params.end_date,
        category_id: params.category_id,
        stock_code: params.stock_code,
        limit: params.limit || 10,
      }),
      headers: workspaceHeaders(workspace),
    }
  )
  return data
}

export async function fetchAnalyticsSkuRankings(
  params: AnalyticsFilterParams,
  workspace: WorkspaceId
): Promise<AnalyticsSkuRankingsResponse> {
  const { data } = await apiClient.get<AnalyticsSkuRankingsResponse>(
    '/api/v1/analytics/sku-rankings',
    {
      params: cleanParams({
        source_origin: params.source_origin,
        order: params.order || 'top',
        sort_by: params.sort_by || 'revenue',
        start_date: params.start_date,
        end_date: params.end_date,
        country: params.country,
        category_id: params.category_id,
        stock_code: params.stock_code,
        page: params.page || 1,
        page_size: params.page_size || 12,
      }),
      headers: workspaceHeaders(workspace),
    }
  )
  return data
}

export async function fetchAnalyticsComparisons(
  params: AnalyticsFilterParams,
  workspace: WorkspaceId
): Promise<AnalyticsComparisonsResponse> {
  const { data } = await apiClient.get<AnalyticsComparisonsResponse>(
    '/api/v1/analytics/comparisons',
    {
      params: cleanParams({
        source_origin: params.source_origin,
        period_type: params.period_type || 'mom',
        reference_date: params.end_date,
        country: params.country,
        category_id: params.category_id,
        stock_code: params.stock_code,
      }),
      headers: workspaceHeaders(workspace),
    }
  )
  return data
}

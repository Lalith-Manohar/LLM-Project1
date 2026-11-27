/**
 * Typed HTTP API client for M06 — Business Intelligence (/api/v1/analytics/*).
 */

import { ApiError } from '../../services/api'
import { WorkspaceCode } from '../../types/workspace'
import {
  AnalyticsComparisonsResponse,
  AnalyticsCountriesResponse,
  AnalyticsFilterParams,
  AnalyticsSkuRankingsResponse,
  AnalyticsSummaryResponse,
  AnalyticsTimeSeriesResponse
} from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== '') {
      search.set(key, String(val))
    }
  })
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

async function fetchAnalyticsJson<T>(path: string, workspace: WorkspaceCode): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'X-NEXORA-Workspace': workspace
      }
    })
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Network error'
    throw new ApiError(0, `Cannot connect to NEXORA backend at ${API_BASE_URL}. (${message})`)
  }

  const rawText = await response.text()
  let parsed: any
  try {
    parsed = JSON.parse(rawText)
  } catch {
    parsed = { detail: rawText }
  }

  if (!response.ok) {
    let message = `Analytics request failed with HTTP ${response.status}`
    if (typeof parsed?.detail === 'string') {
      message = parsed.detail
    } else if (Array.isArray(parsed?.detail)) {
      message = parsed.detail
        .map((d: any) => `${Array.isArray(d.loc) ? d.loc.join('.') : 'Field'}: ${d.msg}`)
        .join('; ')
    }
    throw new ApiError(response.status, message, parsed)
  }

  return parsed as T
}

export function fetchAnalyticsSummary(
  params: AnalyticsFilterParams,
  workspace: WorkspaceCode
): Promise<AnalyticsSummaryResponse> {
  const qs = buildQuery({
    source_origin: params.source_origin,
    start_date: params.start_date,
    end_date: params.end_date,
    country: params.country,
    stock_code: params.stock_code
  })
  return fetchAnalyticsJson<AnalyticsSummaryResponse>(`/api/v1/analytics/summary${qs}`, workspace)
}

export function fetchAnalyticsTimeSeries(
  params: AnalyticsFilterParams,
  workspace: WorkspaceCode
): Promise<AnalyticsTimeSeriesResponse> {
  const qs = buildQuery({
    source_origin: params.source_origin,
    granularity: params.granularity || 'month',
    start_date: params.start_date,
    end_date: params.end_date,
    country: params.country,
    stock_code: params.stock_code
  })
  return fetchAnalyticsJson<AnalyticsTimeSeriesResponse>(`/api/v1/analytics/timeseries${qs}`, workspace)
}

export function fetchAnalyticsCountries(
  params: AnalyticsFilterParams,
  workspace: WorkspaceCode
): Promise<AnalyticsCountriesResponse> {
  const qs = buildQuery({
    source_origin: params.source_origin,
    start_date: params.start_date,
    end_date: params.end_date,
    stock_code: params.stock_code,
    limit: params.limit || 12
  })
  return fetchAnalyticsJson<AnalyticsCountriesResponse>(`/api/v1/analytics/countries${qs}`, workspace)
}

export function fetchAnalyticsSkuRankings(
  params: AnalyticsFilterParams,
  workspace: WorkspaceCode
): Promise<AnalyticsSkuRankingsResponse> {
  const qs = buildQuery({
    source_origin: params.source_origin,
    order: params.order || 'top',
    sort_by: params.sort_by || 'revenue',
    start_date: params.start_date,
    end_date: params.end_date,
    country: params.country,
    stock_code: params.stock_code,
    page: params.page || 1,
    page_size: params.page_size || 15
  })
  return fetchAnalyticsJson<AnalyticsSkuRankingsResponse>(`/api/v1/analytics/sku-rankings${qs}`, workspace)
}

export function fetchAnalyticsComparisons(
  params: AnalyticsFilterParams,
  workspace: WorkspaceCode
): Promise<AnalyticsComparisonsResponse> {
  const qs = buildQuery({
    source_origin: params.source_origin,
    period_type: params.period_type || 'mom',
    reference_date: params.end_date,
    country: params.country,
    stock_code: params.stock_code
  })
  return fetchAnalyticsJson<AnalyticsComparisonsResponse>(`/api/v1/analytics/comparisons${qs}`, workspace)
}

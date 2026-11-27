/**
 * Typed HTTP API client for M08 — Product Lifecycle Intelligence.
 */

import { ApiError } from '../../services/api'
import { WorkspaceCode } from '../../types/workspace'
import {
  DeadStockResponse,
  DiscontinueProductRequest,
  DiscontinueProductResponse,
  LifecycleDetailResponse,
  LifecycleEvaluationResponse,
  LifecycleListResponse,
  LifecycleSettingsResponse,
  LifecycleSourceFilter,
  LifecycleStage
} from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '')

async function requestLifecycleJson<T>(
  path: string,
  workspace: WorkspaceCode,
  options?: { method?: string; body?: unknown }
): Promise<T> {
  const method = options?.method || 'GET'
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'X-NEXORA-Workspace': workspace
  }
  if (options?.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: options?.body !== undefined ? JSON.stringify(options.body) : undefined
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
    let message = `Lifecycle API request failed with HTTP ${response.status}`
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

export function fetchLifecyclePortfolio(
  params: {
    source_origin: LifecycleSourceFilter
    stage?: LifecycleStage | ''
    is_dormant_stock?: boolean
    search?: string
    page?: number
    page_size?: number
  },
  workspace: WorkspaceCode
): Promise<LifecycleListResponse> {
  const q = new URLSearchParams()
  q.set('source_origin', params.source_origin)
  if (params.stage) q.set('stage', params.stage)
  if (params.is_dormant_stock !== undefined) q.set('is_dormant_stock', String(params.is_dormant_stock))
  if (params.search && params.search.trim()) q.set('search', params.search.trim())
  q.set('page', String(params.page || 1))
  q.set('page_size', String(params.page_size || 15))
  return requestLifecycleJson<LifecycleListResponse>(`/api/v1/intelligence/lifecycle?${q.toString()}`, workspace)
}

export function fetchLifecycleSkuDetail(
  productIdOrSku: number | string,
  workspace: WorkspaceCode
): Promise<LifecycleDetailResponse> {
  return requestLifecycleJson<LifecycleDetailResponse>(
    `/api/v1/intelligence/lifecycle/${encodeURIComponent(String(productIdOrSku))}`,
    workspace
  )
}

export function evaluateLifecycleBatch(
  payload: { source_origin: LifecycleSourceFilter; stock_codes?: string[] },
  workspace: WorkspaceCode
): Promise<LifecycleEvaluationResponse> {
  return requestLifecycleJson<LifecycleEvaluationResponse>('/api/v1/intelligence/lifecycle/evaluate', workspace, {
    method: 'POST',
    body: payload
  })
}

export function fetchDeadStock(
  params: { source_origin: LifecycleSourceFilter; page?: number; page_size?: number },
  workspace: WorkspaceCode
): Promise<DeadStockResponse> {
  const q = new URLSearchParams()
  q.set('source_origin', params.source_origin)
  q.set('page', String(params.page || 1))
  q.set('page_size', String(params.page_size || 15))
  return requestLifecycleJson<DeadStockResponse>(`/api/v1/intelligence/dead-stock?${q.toString()}`, workspace)
}

export function discontinueProduct(
  productId: number,
  payload: DiscontinueProductRequest,
  workspace: WorkspaceCode
): Promise<DiscontinueProductResponse> {
  return requestLifecycleJson<DiscontinueProductResponse>(
    `/api/v1/intelligence/lifecycle/${productId}/discontinue`,
    workspace,
    {
      method: 'PATCH',
      body: payload
    }
  )
}

export function fetchLifecycleSettings(workspace: WorkspaceCode): Promise<LifecycleSettingsResponse> {
  return requestLifecycleJson<LifecycleSettingsResponse>('/api/v1/settings/lifecycle', workspace)
}

export function updateLifecycleSettings(
  payload: Record<string, string | number | undefined>,
  workspace: WorkspaceCode
): Promise<LifecycleSettingsResponse> {
  return requestLifecycleJson<LifecycleSettingsResponse>('/api/v1/settings/lifecycle', workspace, {
    method: 'PUT',
    body: payload
  })
}

export function resetLifecycleSettings(
  operatorRef: string | undefined,
  workspace: WorkspaceCode
): Promise<LifecycleSettingsResponse> {
  return requestLifecycleJson<LifecycleSettingsResponse>('/api/v1/settings/lifecycle/reset', workspace, {
    method: 'POST',
    body: operatorRef ? { operator_ref: operatorRef } : {}
  })
}

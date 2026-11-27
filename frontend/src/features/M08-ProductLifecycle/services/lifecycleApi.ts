import axios from 'axios'
import { apiClient } from '@/services/api/client'
import type { WorkspaceId } from '@/types/workspace'
import type {
  DeadStockResponse,
  DiscontinueProductRequest,
  DiscontinueProductResponse,
  LifecycleDetailResponse,
  LifecycleEvaluationResponse,
  LifecycleListResponse,
  LifecycleSettingsResponse,
  LifecycleSourceFilter,
  LifecycleStage,
} from '../types'

export function formatLifecycleApiError(err: unknown): {
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
    return { status, message: err.message || 'Lifecycle API request failed.' }
  }
  return {
    status: null,
    message: err instanceof Error ? err.message : 'Unexpected lifecycle error.',
  }
}

function workspaceHeaders(workspace: WorkspaceId) {
  return { 'X-NEXORA-Workspace': workspace }
}

export async function fetchLifecyclePortfolio(
  params: {
    source_origin: LifecycleSourceFilter
    stage?: LifecycleStage | ''
    is_dormant_stock?: boolean
    search?: string
    page?: number
    page_size?: number
  },
  workspace: WorkspaceId
): Promise<LifecycleListResponse> {
  const query: Record<string, string | number | boolean> = {
    source_origin: params.source_origin,
    page: params.page || 1,
    page_size: params.page_size || 15,
  }
  if (params.stage) query.stage = params.stage
  if (params.is_dormant_stock !== undefined) query.is_dormant_stock = params.is_dormant_stock
  if (params.search && params.search.trim()) query.search = params.search.trim()

  const { data } = await apiClient.get<LifecycleListResponse>('/api/v1/intelligence/lifecycle', {
    params: query,
    headers: workspaceHeaders(workspace),
  })
  return data
}

export async function fetchLifecycleSkuDetail(
  productIdOrSku: number | string,
  workspace: WorkspaceId
): Promise<LifecycleDetailResponse> {
  const { data } = await apiClient.get<LifecycleDetailResponse>(
    `/api/v1/intelligence/lifecycle/${encodeURIComponent(String(productIdOrSku))}`,
    {
      headers: workspaceHeaders(workspace),
    }
  )
  return data
}

export async function evaluateLifecycleBatch(
  payload: { source_origin: LifecycleSourceFilter; stock_codes?: string[] },
  workspace: WorkspaceId
): Promise<LifecycleEvaluationResponse> {
  const { data } = await apiClient.post<LifecycleEvaluationResponse>(
    '/api/v1/intelligence/lifecycle/evaluate',
    payload,
    {
      headers: workspaceHeaders(workspace),
    }
  )
  return data
}

export async function fetchDeadStock(
  params: { source_origin: LifecycleSourceFilter; page?: number; page_size?: number },
  workspace: WorkspaceId
): Promise<DeadStockResponse> {
  const { data } = await apiClient.get<DeadStockResponse>('/api/v1/intelligence/dead-stock', {
    params: {
      source_origin: params.source_origin,
      page: params.page || 1,
      page_size: params.page_size || 15,
    },
    headers: workspaceHeaders(workspace),
  })
  return data
}

export async function discontinueProduct(
  productId: number,
  payload: DiscontinueProductRequest,
  workspace: WorkspaceId
): Promise<DiscontinueProductResponse> {
  const { data } = await apiClient.patch<DiscontinueProductResponse>(
    `/api/v1/intelligence/lifecycle/${productId}/discontinue`,
    payload,
    {
      headers: workspaceHeaders(workspace),
    }
  )
  return data
}

export async function fetchLifecycleSettings(
  workspace: WorkspaceId
): Promise<LifecycleSettingsResponse> {
  const { data } = await apiClient.get<LifecycleSettingsResponse>('/api/v1/settings/lifecycle', {
    headers: workspaceHeaders(workspace),
  })
  return data
}

export async function updateLifecycleSettings(
  payload: Record<string, string | number | undefined>,
  workspace: WorkspaceId
): Promise<LifecycleSettingsResponse> {
  const { data } = await apiClient.put<LifecycleSettingsResponse>(
    '/api/v1/settings/lifecycle',
    payload,
    {
      headers: workspaceHeaders(workspace),
    }
  )
  return data
}

export async function resetLifecycleSettings(
  operatorRef: string | undefined,
  workspace: WorkspaceId
): Promise<LifecycleSettingsResponse> {
  const { data } = await apiClient.post<LifecycleSettingsResponse>(
    '/api/v1/settings/lifecycle/reset',
    operatorRef ? { operator_ref: operatorRef } : {},
    {
      headers: workspaceHeaders(workspace),
    }
  )
  return data
}

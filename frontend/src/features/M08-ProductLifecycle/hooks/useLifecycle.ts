import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { WorkspaceId } from '@/types/workspace'
import {
  discontinueProduct,
  evaluateLifecycleBatch,
  fetchDeadStock,
  fetchLifecyclePortfolio,
  fetchLifecycleSettings,
  fetchLifecycleSkuDetail,
  resetLifecycleSettings,
  updateLifecycleSettings,
} from '../services/lifecycleApi'
import type {
  DiscontinueProductRequest,
  LifecycleSourceFilter,
  LifecycleStage,
} from '../types'

export function useLifecyclePortfolio(
  params: {
    source_origin: LifecycleSourceFilter
    stage?: LifecycleStage | ''
    is_dormant_stock?: boolean
    search?: string
    page?: number
    page_size?: number
  },
  workspace: WorkspaceId,
  enabled = true
) {
  return useQuery({
    queryKey: ['m08', 'portfolio', params, workspace],
    queryFn: () => fetchLifecyclePortfolio(params, workspace),
    enabled,
  })
}

export function useDeadStock(
  params: { source_origin: LifecycleSourceFilter; page?: number; page_size?: number },
  workspace: WorkspaceId,
  enabled = true
) {
  return useQuery({
    queryKey: ['m08', 'dead-stock', params, workspace],
    queryFn: () => fetchDeadStock(params, workspace),
    enabled,
  })
}

export function useLifecycleSettings(workspace: WorkspaceId, enabled = true) {
  return useQuery({
    queryKey: ['m08', 'settings', workspace],
    queryFn: () => fetchLifecycleSettings(workspace),
    enabled,
  })
}

export function useLifecycleSkuDetail(
  productId: number | null,
  workspace: WorkspaceId
) {
  return useQuery({
    queryKey: ['m08', 'detail', productId, workspace],
    queryFn: () => fetchLifecycleSkuDetail(productId as number, workspace),
    enabled: productId !== null,
  })
}

export function useLifecycleMutations(workspace: WorkspaceId) {
  const queryClient = useQueryClient()

  const invalidateAll = async () => {
    await queryClient.invalidateQueries({ queryKey: ['m08'] })
  }

  const evaluateMutation = useMutation({
    mutationFn: (payload: { source_origin: LifecycleSourceFilter; stock_codes?: string[] }) =>
      evaluateLifecycleBatch(payload, workspace),
    onSuccess: invalidateAll,
  })

  const discontinueMutation = useMutation({
    mutationFn: (vars: { productId: number; payload: DiscontinueProductRequest }) =>
      discontinueProduct(vars.productId, vars.payload, workspace),
    onSuccess: invalidateAll,
  })

  const updateSettingsMutation = useMutation({
    mutationFn: (payload: Record<string, string | number | undefined>) =>
      updateLifecycleSettings(payload, workspace),
    onSuccess: invalidateAll,
  })

  const resetSettingsMutation = useMutation({
    mutationFn: (operatorRef?: string) => resetLifecycleSettings(operatorRef, workspace),
    onSuccess: invalidateAll,
  })

  return {
    evaluateMutation,
    discontinueMutation,
    updateSettingsMutation,
    resetSettingsMutation,
  }
}

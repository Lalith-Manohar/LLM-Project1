import { useQuery } from '@tanstack/react-query'
import type { WorkspaceId } from '@/types/workspace'
import {
  fetchAnalyticsComparisons,
  fetchAnalyticsCountries,
  fetchAnalyticsSkuRankings,
  fetchAnalyticsSummary,
  fetchAnalyticsTimeSeries,
} from '../services/analyticsApi'
import type { AnalyticsFilterParams } from '../types'

/** TanStack Query hooks for M06 Business Intelligence endpoints. */
export function useAnalyticsBundle(
  params: AnalyticsFilterParams,
  workspace: WorkspaceId,
  enabled: boolean
) {
  const summaryParams: AnalyticsFilterParams = {
    source_origin: params.source_origin,
    start_date: params.start_date,
    end_date: params.end_date,
    country: params.country,
    category_id: params.category_id,
    stock_code: params.stock_code,
  }

  const timeSeriesParams: AnalyticsFilterParams = {
    ...summaryParams,
    granularity: params.granularity || 'month',
  }

  const countriesParams: AnalyticsFilterParams = {
    source_origin: params.source_origin,
    start_date: params.start_date,
    end_date: params.end_date,
    category_id: params.category_id,
    stock_code: params.stock_code,
    limit: params.limit || 10,
  }

  const skuRankingsParams: AnalyticsFilterParams = {
    ...summaryParams,
    order: params.order || 'top',
    sort_by: params.sort_by || 'revenue',
    page: params.page || 1,
    page_size: params.page_size || 12,
  }

  const comparisonsParams: AnalyticsFilterParams = {
    source_origin: params.source_origin,
    period_type: params.period_type || 'mom',
    end_date: params.end_date,
    country: params.country,
    category_id: params.category_id,
    stock_code: params.stock_code,
  }

  const summaryQuery = useQuery({
    queryKey: ['m06', 'summary', summaryParams, workspace],
    queryFn: () => fetchAnalyticsSummary(summaryParams, workspace),
    enabled,
  })

  const timeSeriesQuery = useQuery({
    queryKey: ['m06', 'timeseries', timeSeriesParams, workspace],
    queryFn: () => fetchAnalyticsTimeSeries(timeSeriesParams, workspace),
    enabled,
  })

  const countriesQuery = useQuery({
    queryKey: ['m06', 'countries', countriesParams, workspace],
    queryFn: () => fetchAnalyticsCountries(countriesParams, workspace),
    enabled,
  })

  const skuRankingsQuery = useQuery({
    queryKey: ['m06', 'sku-rankings', skuRankingsParams, workspace],
    queryFn: () => fetchAnalyticsSkuRankings(skuRankingsParams, workspace),
    enabled,
  })

  const comparisonsQuery = useQuery({
    queryKey: ['m06', 'comparisons', comparisonsParams, workspace],
    queryFn: () => fetchAnalyticsComparisons(comparisonsParams, workspace),
    enabled,
  })

  const isLoading =
    summaryQuery.isLoading ||
    timeSeriesQuery.isLoading ||
    countriesQuery.isLoading ||
    skuRankingsQuery.isLoading ||
    comparisonsQuery.isLoading

  const error =
    summaryQuery.error ||
    timeSeriesQuery.error ||
    countriesQuery.error ||
    skuRankingsQuery.error ||
    comparisonsQuery.error ||
    null

  const refetchAll = async () => {
    await Promise.all([
      summaryQuery.refetch(),
      timeSeriesQuery.refetch(),
      countriesQuery.refetch(),
      skuRankingsQuery.refetch(),
      comparisonsQuery.refetch(),
    ])
  }

  return {
    summary: summaryQuery.data,
    timeseries: timeSeriesQuery.data,
    countries: countriesQuery.data,
    rankings: skuRankingsQuery.data,
    comparisons: comparisonsQuery.data,
    isLoading,
    error,
    refetchAll,
  }
}

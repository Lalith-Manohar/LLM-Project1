import { useEffect, useState, type FormEvent } from 'react'
import { AlertCircle, BarChart3, Download, RefreshCw, ShieldCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { getWorkspaceById } from '@/utils/modules'
import { CountryBarChart, SalesTrendChart } from '../components/BiCharts'
import { KpiSummaryGrid } from '../components/KpiSummaryGrid'
import { SkuRankingsTable } from '../components/SkuRankingsTable'
import { useAnalyticsBundle } from '../hooks/useAnalytics'
import { formatAnalyticsApiError } from '../services/analyticsApi'
import type {
  AnalyticsFilterParams,
  ComparisonPeriodType,
  GranularityType,
  SkuRankingOrder,
  SkuRankingSortBy,
  SourceOriginFilter,
} from '../types'
import {
  buildFormulaSafeCsv,
  formatCurrencyAmount,
  formatMetricNumber,
  triggerFileDownload,
} from '../utils/formatters'

const WORKSPACE_M06_SCOPE: Record<string, string> = {
  store_manager:
    'Full UI Access: Executive KPIs, Time-Series Trends, Country Breakdown, Comparisons & SKU Rankings.',
  inventory_staff:
    'Scoped Operational View: Slow-moving SKU velocity & stock turnover indicators across separated sources.',
  purchase_manager:
    'Scoped Operational View: SKU velocity leaderboards & demand trends supporting replenishment planning.',
  finance_staff:
    'Scoped Operational View: Gross vs. Net revenue reconciliation, returns/cancellations & country splits.',
}

export function BusinessIntelligenceView() {
  const activeWorkspace = useWorkspaceStore((state) => state.activeWorkspace)
  const workspaceDef = getWorkspaceById(activeWorkspace)

  // Draft filter inputs & applied filter state
  const [sourceOrigin, setSourceOrigin] = useState<SourceOriginFilter>('all')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [country, setCountry] = useState('')
  const [stockCode, setStockCode] = useState('')

  const [granularity, setGranularity] = useState<GranularityType>('month')
  const [trendMetric, setTrendMetric] = useState<'gross_revenue' | 'net_revenue' | 'gross_units'>(
    'gross_revenue'
  )
  const [rankingOrder, setRankingOrder] = useState<SkuRankingOrder>(
    activeWorkspace === 'inventory_staff' ? 'slowest' : 'top'
  )
  const [rankingSortBy, setRankingSortBy] = useState<SkuRankingSortBy>('revenue')
  const [rankingPage, setRankingPage] = useState(1)
  const [periodType, setPeriodType] = useState<ComparisonPeriodType>('mom')

  const [validationError, setValidationError] = useState<string | null>(null)
  const [exportNotice, setExportNotice] = useState<string | null>(null)

  const [appliedDates, setAppliedDates] = useState<{
    start_date?: string
    end_date?: string
    country?: string
    stock_code?: string
  }>({})

  useEffect(() => {
    if (activeWorkspace === 'inventory_staff') {
      setRankingOrder('slowest')
    } else if (activeWorkspace === 'purchase_manager' || activeWorkspace === 'finance_staff') {
      setRankingOrder('top')
    }
  }, [activeWorkspace])

  const queryParams: AnalyticsFilterParams = {
    source_origin: sourceOrigin,
    start_date: appliedDates.start_date,
    end_date: appliedDates.end_date,
    country: appliedDates.country,
    stock_code: appliedDates.stock_code,
    granularity,
    order: rankingOrder,
    sort_by: rankingSortBy,
    period_type: periodType,
    page: rankingPage,
    page_size: 12,
    limit: 10,
  }

  const {
    summary,
    timeseries,
    countries,
    rankings,
    comparisons,
    isLoading,
    error,
    refetchAll,
  } = useAnalyticsBundle(queryParams, activeWorkspace, validationError === null)

  const handleApplyFilters = (e: FormEvent) => {
    e.preventDefault()
    setExportNotice(null)
    if (startDate && endDate && startDate > endDate) {
      setValidationError(
        'Invalid date range: Start Date cannot be after End Date (HTTP 422 guard).'
      )
      return
    }
    setValidationError(null)
    setRankingPage(1)
    setAppliedDates({
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      country: country.trim() || undefined,
      stock_code: stockCode.trim() || undefined,
    })
  }

  const handleResetFilters = () => {
    setSourceOrigin('all')
    setStartDate('')
    setEndDate('')
    setCountry('')
    setStockCode('')
    setGranularity('month')
    setPeriodType('mom')
    setRankingPage(1)
    setValidationError(null)
    setExportNotice(null)
    setAppliedDates({})
  }

  /**
   * Client-side SYS-04 handoff export (formula-neutralized CSV / JSON).
   * Phase 5 SYS-04 will wire server-persisted REPORT_EXPORTED audit calls to POST /api/v1/reports/export.
   */
  const handleExportSkuRankings = (format: 'csv' | 'json') => {
    const activeBlock = rankings?.operational?.data_span.has_data
      ? rankings.operational
      : rankings?.uci_historical

    if (!activeBlock || activeBlock.items.length === 0) {
      setExportNotice('No SKU ranking rows available to export for the current filters.')
      return
    }

    const stamp = new Date().toISOString().slice(0, 10)
    if (format === 'json') {
      triggerFileDownload(
        JSON.stringify(
          {
            module: 'M06_BUSINESS_INTELLIGENCE',
            export_contract: 'SYS-04_CLIENT_HANDOFF_PREVIEW',
            workspace_context: workspaceDef.label,
            source_origin: activeBlock.source_origin,
            currency: activeBlock.currency,
            data_span: activeBlock.data_span,
            rows: activeBlock.items,
          },
          null,
          2
        ),
        `nexora_m06_sku_rankings_${activeBlock.source_origin}_${stamp}.json`,
        'application/json'
      )
    } else {
      const headers = [
        'rank',
        'stock_code',
        'description',
        'source_origin',
        'currency',
        'gross_units',
        'return_units',
        'cancellation_units',
        'net_units',
        'gross_revenue',
        'return_amount',
        'cancellation_amount',
        'net_revenue',
        'order_count',
        'avg_daily_velocity',
        'is_slow_moving',
      ]
      const rows = activeBlock.items.map((item) => ({
        ...item,
        source_origin: activeBlock.source_origin,
        currency: activeBlock.currency,
      }))
      const csv = buildFormulaSafeCsv(headers, rows)
      triggerFileDownload(
        csv,
        `nexora_m06_sku_rankings_${activeBlock.source_origin}_${stamp}.csv`,
        'text/csv;charset=utf-8'
      )
    }

    setExportNotice(
      `Exported ${activeBlock.items.length} ${activeBlock.source_origin} (${activeBlock.currency}) rows as formula-safe ${format.toUpperCase()} (client preview; Phase 5 SYS-04 endpoint adds server REPORT_EXPORTED audit).`
    )
  }

  const formattedError = error ? formatAnalyticsApiError(error) : null

  const kpiBlocks = [
    ...(summary?.operational ? [summary.operational] : []),
    ...(summary?.uci_historical ? [summary.uci_historical] : []),
  ]
  const tsBlocks = [
    ...(timeseries?.operational ? [timeseries.operational] : []),
    ...(timeseries?.uci_historical ? [timeseries.uci_historical] : []),
  ]
  const countryBlocks = [
    ...(countries?.operational ? [countries.operational] : []),
    ...(countries?.uci_historical ? [countries.uci_historical] : []),
  ]
  const comparisonBlocks = [
    ...(comparisons?.operational ? [comparisons.operational] : []),
    ...(comparisons?.uci_historical ? [comparisons.uci_historical] : []),
  ]
  const rankingBlocks = [
    ...(rankings?.operational ? [rankings.operational] : []),
    ...(rankings?.uci_historical ? [rankings.uci_historical] : []),
  ]

  return (
    <section className="space-y-6" aria-label="M06 Business Intelligence">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-primary" />
                <Badge variant="outline" className="font-mono">
                  M06
                </Badge>
                <CardTitle className="text-xl">Business Intelligence</CardTitle>
              </div>
              <CardDescription>
                Read-only executive KPIs, time-series trends, geographical distributions, period comparisons, and SKU velocity leaderboards.
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleExportSkuRankings('csv')}
                disabled={isLoading}
              >
                <Download className="h-4 w-4" />
                Export CSV
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleExportSkuRankings('json')}
                disabled={isLoading}
              >
                <Download className="h-4 w-4" />
                Export JSON
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="rounded-md border bg-primary/5 px-3 py-2 text-xs text-foreground">
            <strong>{workspaceDef.label} Scope:</strong>{' '}
            {WORKSPACE_M06_SCOPE[activeWorkspace] ?? WORKSPACE_M06_SCOPE.store_manager}
          </div>

          <div className="flex items-start gap-2 rounded-md border border-l-4 border-l-primary bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            <span>
              <strong>DDR-04 Currency Separation Active:</strong> Historical UCI baseline records (2009–2011) are denominated in{' '}
              <code>GBP (£)</code> and live operational store records in <code>INR (₹)</code>. Sources are strictly separated and never blended.
            </span>
          </div>

          <form onSubmit={handleApplyFilters} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
            <div className="space-y-1">
              <label htmlFor="m06-source" className="text-xs font-medium text-muted-foreground">
                Data Source View
              </label>
              <select
                id="m06-source"
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                value={sourceOrigin}
                onChange={(e) => {
                  setSourceOrigin(e.target.value as SourceOriginFilter)
                  setRankingPage(1)
                }}
              >
                <option value="all">Combined View (GBP &amp; INR Separated)</option>
                <option value="uci_historical">Historical UCI Baseline (GBP)</option>
                <option value="operational">Live Operational Store (INR)</option>
              </select>
            </div>

            <div className="space-y-1">
              <label htmlFor="m06-start-date" className="text-xs font-medium text-muted-foreground">
                Start Date
              </label>
              <Input
                id="m06-start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label htmlFor="m06-end-date" className="text-xs font-medium text-muted-foreground">
                End Date
              </label>
              <Input
                id="m06-end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label htmlFor="m06-country" className="text-xs font-medium text-muted-foreground">
                Country
              </label>
              <Input
                id="m06-country"
                type="text"
                placeholder="e.g. United Kingdom"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <label htmlFor="m06-sku" className="text-xs font-medium text-muted-foreground">
                Product SKU
              </label>
              <Input
                id="m06-sku"
                type="text"
                placeholder="e.g. 85123A"
                value={stockCode}
                onChange={(e) => setStockCode(e.target.value)}
              />
            </div>

            <div className="flex items-end gap-2">
              <Button type="submit" size="sm" disabled={isLoading}>
                Apply Filters
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={handleResetFilters} disabled={isLoading}>
                Reset
              </Button>
            </div>
          </form>

          {validationError && (
            <div
              role="alert"
              className="flex items-center gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{validationError}</span>
            </div>
          )}

          {formattedError && (
            <div
              role="alert"
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              <span>
                {formattedError.status ? `[HTTP ${formattedError.status}] ` : ''}
                {formattedError.message}
              </span>
              <Button type="button" variant="outline" size="sm" onClick={() => void refetchAll()}>
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </Button>
            </div>
          )}

          {exportNotice && (
            <div
              role="status"
              className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
            >
              {exportNotice}
            </div>
          )}
        </CardContent>
      </Card>

      {isLoading ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <RefreshCw className="mb-3 h-7 w-7 animate-spin text-primary" />
            <p className="font-semibold text-foreground">Aggregating Business Intelligence Streams...</p>
            <p className="text-xs text-muted-foreground">
              Computing exact DECIMAL KPIs, trends, country shares, comparisons, and SKU velocity rankings
            </p>
          </CardContent>
        </Card>
      ) : (
        <>
          <KpiSummaryGrid blocks={kpiBlocks} />

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Time-Series Trajectory */}
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-lg">Sales Time-Series Trajectory</CardTitle>
                    <CardDescription>Daily, ISO-weekly, or monthly trends.</CardDescription>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {(['day', 'week', 'month'] as GranularityType[]).map((g) => (
                      <Button
                        key={g}
                        type="button"
                        size="sm"
                        variant={granularity === g ? 'default' : 'outline'}
                        onClick={() => setGranularity(g)}
                      >
                        {g.toUpperCase()}
                      </Button>
                    ))}
                    <select
                      aria-label="Time-series metric"
                      className="h-8 rounded-md border border-input bg-background px-2 text-xs font-medium"
                      value={trendMetric}
                      onChange={(e) =>
                        setTrendMetric(
                          e.target.value as 'gross_revenue' | 'net_revenue' | 'gross_units'
                        )
                      }
                    >
                      <option value="gross_revenue">Gross Revenue</option>
                      <option value="net_revenue">Net Revenue</option>
                      <option value="gross_units">Gross Units</option>
                    </select>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                {tsBlocks.map((block) => (
                  <div
                    key={block.source_origin}
                    className="space-y-2 border-t pt-4 first:border-t-0 first:pt-0"
                  >
                    <div className="flex items-center justify-between gap-2 text-sm font-medium">
                      <span>{block.label}</span>
                      <Badge variant="outline" className="font-mono">
                        {block.currency}
                      </Badge>
                    </div>
                    <SalesTrendChart
                      points={block.points}
                      currency={block.currency}
                      metric={trendMetric}
                    />
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Period-over-Period Variance */}
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-lg">Period-over-Period Variance</CardTitle>
                    <CardDescription>
                      Safe zero-baseline % comparisons (returns N/A instead of Infinity).
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {(['mom', 'qoq', 'yoy'] as ComparisonPeriodType[]).map((p) => (
                      <Button
                        key={p}
                        type="button"
                        size="sm"
                        variant={periodType === p ? 'default' : 'outline'}
                        onClick={() => setPeriodType(p)}
                      >
                        {p.toUpperCase()}
                      </Button>
                    ))}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                {comparisonBlocks.map((block) => (
                  <div
                    key={block.source_origin}
                    className="space-y-3 border-t pt-4 first:border-t-0 first:pt-0"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 text-sm font-medium">
                      <span>{block.label}</span>
                      <Badge variant="outline" className="font-mono">
                        {block.current_period_label} vs {block.previous_period_label}
                      </Badge>
                    </div>
                    {block.coverage_notice && (
                      <p className="rounded border border-amber-300 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-900">
                        {block.coverage_notice}
                      </p>
                    )}
                    {block.metrics.length === 0 ? (
                      <div className="rounded-lg border border-dashed bg-muted/40 p-5 text-center text-sm text-muted-foreground">
                        No comparison data available for this source.
                      </div>
                    ) : (
                      <div className="grid gap-3 sm:grid-cols-2">
                        {block.metrics.map((m) => {
                          const deltaNum = m.delta_pct !== null ? Number(m.delta_pct) : null
                          return (
                            <div key={m.metric_key} className="rounded-lg border bg-muted/30 p-3">
                              <p className="text-xs font-semibold uppercase text-muted-foreground">
                                {m.label}
                              </p>
                              <p className="mt-1 font-mono text-base font-bold">
                                {m.unit === 'GBP' || m.unit === 'INR'
                                  ? formatCurrencyAmount(m.current_value, m.unit)
                                  : formatMetricNumber(m.current_value, 0)}
                              </p>
                              <div className="mt-1 flex items-center justify-between gap-2 text-xs">
                                <span className="text-muted-foreground">
                                  Prev:{' '}
                                  {m.unit === 'GBP' || m.unit === 'INR'
                                    ? formatCurrencyAmount(m.previous_value, m.unit)
                                    : formatMetricNumber(m.previous_value, 0)}
                                </span>
                                <Badge variant={deltaNum === null ? 'outline' : deltaNum >= 0 ? 'secondary' : 'destructive'}>
                                  {deltaNum === null
                                    ? 'N/A (0 base)'
                                    : `${deltaNum >= 0 ? '+' : ''}${m.delta_pct}%`}
                                </Badge>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Geographical Country Sales Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Geographical Country Sales Breakdown</CardTitle>
              <CardDescription>
                Top markets by gross revenue and share percentage per source.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-6 lg:grid-cols-2">
              {countryBlocks.map((block) => (
                <div key={block.source_origin} className="space-y-3">
                  <div className="flex items-center justify-between gap-2 text-sm font-medium">
                    <span>
                      {block.label} ({block.total_countries} countries)
                    </span>
                    <Badge variant="outline" className="font-mono">
                      {block.currency}
                    </Badge>
                  </div>
                  <CountryBarChart countries={block.countries} currency={block.currency} />
                </div>
              ))}
            </CardContent>
          </Card>

          <SkuRankingsTable
            blocks={rankingBlocks}
            lifecycleSeparationNotice={rankings?.lifecycle_separation_notice}
            rankingOrder={rankingOrder}
            rankingSortBy={rankingSortBy}
            rankingPage={rankingPage}
            isLoading={isLoading}
            onChangeOrder={(order) => {
              setRankingOrder(order)
              setRankingPage(1)
            }}
            onChangeSortBy={(sortBy) => {
              setRankingSortBy(sortBy)
              setRankingPage(1)
            }}
            onChangePage={setRankingPage}
          />
        </>
      )}
    </section>
  )
}

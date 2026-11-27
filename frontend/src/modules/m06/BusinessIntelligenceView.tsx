import React, { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../../services/api'
import { useWorkspace } from '../../context/WorkspaceContext'
import {
  buildFormulaSafeCsv,
  formatMoney,
  formatNumber,
  triggerFileDownload
} from '../../types/workspace'
import {
  fetchAnalyticsComparisons,
  fetchAnalyticsCountries,
  fetchAnalyticsSkuRankings,
  fetchAnalyticsSummary,
  fetchAnalyticsTimeSeries
} from './api'
import { CountryBarChart, SalesTrendChart } from './components/BiCharts'
import {
  AnalyticsComparisonsResponse,
  AnalyticsCountriesResponse,
  AnalyticsSkuRankingsResponse,
  AnalyticsSummaryResponse,
  AnalyticsTimeSeriesResponse,
  ComparisonPeriodType,
  GranularityType,
  SkuRankingOrder,
  SkuRankingSortBy,
  SourceComparisonBlock,
  SourceCountryBlock,
  SourceKpiBlock,
  SourceOriginFilter,
  SourceSkuRankingBlock,
  SourceTimeSeriesBlock
} from './types'

export const BusinessIntelligenceView: React.FC = () => {
  const { workspace, workspaceDef } = useWorkspace()

  // Filter controls
  const [sourceOrigin, setSourceOrigin] = useState<SourceOriginFilter>('all')
  const [startDate, setStartDate] = useState<string>('')
  const [endDate, setEndDate] = useState<string>('')
  const [country, setCountry] = useState<string>('')
  const [stockCode, setStockCode] = useState<string>('')
  const [granularity, setGranularity] = useState<GranularityType>('month')
  const [trendMetric, setTrendMetric] = useState<'gross_revenue' | 'net_revenue' | 'gross_units'>('gross_revenue')
  const [rankingOrder, setRankingOrder] = useState<SkuRankingOrder>(
    workspace === 'inventory_staff' ? 'slowest' : 'top'
  )
  const [rankingSortBy, setRankingSortBy] = useState<SkuRankingSortBy>('revenue')
  const [rankingPage, setRankingPage] = useState<number>(1)
  const [periodType, setPeriodType] = useState<ComparisonPeriodType>('mom')

  // Data state
  const [loading, setLoading] = useState<boolean>(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const [exportSuccess, setExportSuccess] = useState<string | null>(null)

  const [summary, setSummary] = useState<AnalyticsSummaryResponse | null>(null)
  const [timeseries, setTimeseries] = useState<AnalyticsTimeSeriesResponse | null>(null)
  const [countries, setCountries] = useState<AnalyticsCountriesResponse | null>(null)
  const [rankings, setRankings] = useState<AnalyticsSkuRankingsResponse | null>(null)
  const [comparisons, setComparisons] = useState<AnalyticsComparisonsResponse | null>(null)

  // Adjust default ranking focus when switching to Inventory Staff workspace
  useEffect(() => {
    if (workspace === 'inventory_staff') {
      setRankingOrder('slowest')
    } else if (workspace === 'purchase_manager' || workspace === 'finance_staff') {
      setRankingOrder('top')
    }
  }, [workspace])

  const loadAnalytics = useCallback(async (pageOverride?: number) => {
    setValidationError(null)
    setApiError(null)

    if (startDate && endDate && startDate > endDate) {
      setValidationError('Invalid date range: Start Date cannot be after End Date (HTTP 422 guard).')
      return
    }

    const activePage = pageOverride ?? rankingPage
    setLoading(true)
    const params = {
      source_origin: sourceOrigin,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      country: country.trim() || undefined,
      stock_code: stockCode.trim() || undefined,
      granularity,
      order: rankingOrder,
      sort_by: rankingSortBy,
      period_type: periodType,
      page: activePage,
      page_size: 12,
      limit: 10
    }

    try {
      const [sumRes, tsRes, ctryRes, rankRes, compRes] = await Promise.all([
        fetchAnalyticsSummary(params, workspace),
        fetchAnalyticsTimeSeries(params, workspace),
        fetchAnalyticsCountries(params, workspace),
        fetchAnalyticsSkuRankings(params, workspace),
        fetchAnalyticsComparisons(params, workspace)
      ])
      setSummary(sumRes)
      setTimeseries(tsRes)
      setCountries(ctryRes)
      setRankings(rankRes)
      setComparisons(compRes)
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 422) {
          setValidationError(`[HTTP 422] ${err.message}`)
        } else {
          setApiError(`[HTTP ${err.status}] ${err.message}`)
        }
      } else {
        setApiError(err instanceof Error ? err.message : 'Failed to load M06 Business Intelligence metrics.')
      }
    } finally {
      setLoading(false)
    }
  }, [
    sourceOrigin,
    startDate,
    endDate,
    country,
    stockCode,
    granularity,
    rankingOrder,
    rankingSortBy,
    rankingPage,
    periodType,
    workspace
  ])

  useEffect(() => {
    loadAnalytics()
  }, [loadAnalytics])

  const handleApplyFilters = (e: React.FormEvent) => {
    e.preventDefault()
    setRankingPage(1)
    loadAnalytics(1)
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
  }

  /**
   * SYS-04 Reports & Export Handoff (Formula-neutralized CSV / JSON).
   * Integration developer can swap this to POST /api/v1/reports/export when Phase 5 SYS-04 lands.
   */
  const handleExportSkuRankings = (format: 'csv' | 'json') => {
    const activeBlock =
      rankings?.operational?.data_span.has_data
        ? rankings.operational
        : rankings?.uci_historical
    if (!activeBlock || activeBlock.items.length === 0) {
      setExportSuccess(null)
      setApiError('No SKU ranking rows available to export for the current filters.')
      return
    }

    const stamp = new Date().toISOString().slice(0, 10)
    if (format === 'json') {
      const payload = {
        module: 'M06_BUSINESS_INTELLIGENCE',
        export_contract: 'SYS-04_HANDOFF_READY',
        workspace_context: workspaceDef.label,
        source_origin: activeBlock.source_origin,
        currency: activeBlock.currency,
        data_span: activeBlock.data_span,
        rows: activeBlock.items
      }
      triggerFileDownload(
        JSON.stringify(payload, null, 2),
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
        'is_slow_moving'
      ]
      const rows = activeBlock.items.map((item) => ({
        ...item,
        source_origin: activeBlock.source_origin,
        currency: activeBlock.currency
      }))
      const csv = buildFormulaSafeCsv(headers, rows)
      triggerFileDownload(
        csv,
        `nexora_m06_sku_rankings_${activeBlock.source_origin}_${stamp}.csv`,
        'text/csv;charset=utf-8'
      )
    }
    setExportSuccess(
      `Exported ${activeBlock.items.length} ${activeBlock.source_origin} (${activeBlock.currency}) rows as formula-safe ${format.toUpperCase()} (SYS-04 handoff format).`
    )
  }

  const activeKpiBlocks: SourceKpiBlock[] = [
    ...(summary?.operational ? [summary.operational] : []),
    ...(summary?.uci_historical ? [summary.uci_historical] : [])
  ]
  const activeTsBlocks: SourceTimeSeriesBlock[] = [
    ...(timeseries?.operational ? [timeseries.operational] : []),
    ...(timeseries?.uci_historical ? [timeseries.uci_historical] : [])
  ]
  const activeCountryBlocks: SourceCountryBlock[] = [
    ...(countries?.operational ? [countries.operational] : []),
    ...(countries?.uci_historical ? [countries.uci_historical] : [])
  ]
  const activeCompBlocks: SourceComparisonBlock[] = [
    ...(comparisons?.operational ? [comparisons.operational] : []),
    ...(comparisons?.uci_historical ? [comparisons.uci_historical] : [])
  ]
  const activeRankingBlocks: SourceSkuRankingBlock[] = [
    ...(rankings?.operational ? [rankings.operational] : []),
    ...(rankings?.uci_historical ? [rankings.uci_historical] : [])
  ]

  return (
    <section className="module-stack" aria-label="M06 Business Intelligence">
      {/* Header & Workspace Scope Banner */}
      <div className="card">
        <div className="module-header-row">
          <div>
            <h2>M06 — Business Intelligence</h2>
            <p className="section-desc">
              Executive retail KPIs, time-series trajectories, geographical country breakdowns, period comparisons, and SKU velocity leaderboards.
            </p>
          </div>
          <div className="module-actions-row">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => handleExportSkuRankings('csv')}
              disabled={loading}
            >
              Export CSV (Formula-Safe)
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => handleExportSkuRankings('json')}
              disabled={loading}
            >
              Export JSON
            </button>
          </div>
        </div>

        <div className="workspace-scope-banner">
          <strong>{workspaceDef.label} Scope:</strong> {workspaceDef.m06ScopeNote}
        </div>

        <div className="currency-guard-banner">
          <strong>DDR-04 Currency Separation Active:</strong> Historical UCI baseline records (2009–2011) are denominated in <code>GBP (£)</code> and live operational store records in <code>INR (₹)</code>. Sources are displayed in strictly separated blocks and never blended.
        </div>

        {/* Filter Bar */}
        <form className="filter-grid" onSubmit={handleApplyFilters}>
          <div className="filter-field">
            <label htmlFor="m06-source">Data Source View</label>
            <select
              id="m06-source"
              className="input-text"
              value={sourceOrigin}
              onChange={(e) => {
                setSourceOrigin(e.target.value as SourceOriginFilter)
                setRankingPage(1)
              }}
            >
              <option value="all">Combined View (GBP & INR Separated)</option>
              <option value="uci_historical">Historical UCI Dataset Baseline (GBP)</option>
              <option value="operational">Live Operational Store Records (INR)</option>
            </select>
          </div>

          <div className="filter-field">
            <label htmlFor="m06-start-date">Start Date</label>
            <input
              id="m06-start-date"
              type="date"
              className="input-text"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div className="filter-field">
            <label htmlFor="m06-end-date">End Date</label>
            <input
              id="m06-end-date"
              type="date"
              className="input-text"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>

          <div className="filter-field">
            <label htmlFor="m06-country">Country</label>
            <input
              id="m06-country"
              type="text"
              className="input-text"
              placeholder="e.g. United Kingdom"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
            />
          </div>

          <div className="filter-field">
            <label htmlFor="m06-sku">Product SKU</label>
            <input
              id="m06-sku"
              type="text"
              className="input-text"
              placeholder="e.g. 85123A"
              value={stockCode}
              onChange={(e) => setStockCode(e.target.value)}
            />
          </div>

          <div className="filter-actions">
            <button type="submit" className="btn-primary-sm" disabled={loading}>
              {loading ? 'Loading...' : 'Apply Filters'}
            </button>
            <button type="button" className="btn-ghost-sm" onClick={handleResetFilters} disabled={loading}>
              Reset
            </button>
          </div>
        </form>

        {validationError && (
          <div className="alert alert-warning" role="alert">
            <span className="alert-icon">⚠️</span>
            <div><strong>Validation Error:</strong> {validationError}</div>
          </div>
        )}
        {apiError && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon">⛔</span>
            <div><strong>API Error:</strong> {apiError}</div>
          </div>
        )}
        {exportSuccess && (
          <div className="alert alert-success" role="status">
            <span className="alert-icon">✅</span>
            <div>{exportSuccess}</div>
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="card loading-state">
          <div className="large-spinner" />
          <p className="loading-title">Aggregating Business Intelligence Streams...</p>
          <p className="loading-subtitle">Computing exact DECIMAL KPIs, trends, countries, comparisons, and SKU velocity rankings</p>
        </div>
      )}

      {/* Executive KPI Summary Blocks (Separated by Source & Currency) */}
      {!loading && activeKpiBlocks.map((block) => (
        <div key={block.source_origin} className="card">
          <div className="source-block-header">
            <div>
              <h3>{block.label}</h3>
              <p className="section-desc">
                {block.data_span.has_data
                  ? `Data Span: ${block.data_span.start_date} to ${block.data_span.end_date} (${block.data_span.record_count.toLocaleString()} stream line items)`
                  : block.data_span.empty_state_reason}
              </p>
            </div>
            <span className={`currency-badge currency-${block.currency.toLowerCase()}`}>
              {block.currency} • {block.source_origin}
            </span>
          </div>

          {!block.data_span.has_data ? (
            <div className="module-empty-inline">
              {block.data_span.empty_state_reason}
            </div>
          ) : (
            <div className="kpi-cards-grid">
              <div className="kpi-card">
                <span className="kpi-label">Gross Revenue</span>
                <strong className="kpi-value">{formatMoney(block.gross_revenue, block.currency)}</strong>
                <span className="kpi-sub">Positive valid sales stream only</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">Net Revenue</span>
                <strong className="kpi-value">{formatMoney(block.net_revenue, block.currency)}</strong>
                <span className="kpi-sub">Gross minus returns &amp; cancellations</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">Gross / Net Units</span>
                <strong className="kpi-value">{formatNumber(block.gross_units_sold, 0)}</strong>
                <span className="kpi-sub">Net: {formatNumber(block.net_units_sold, 0)} units</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">Unique Orders</span>
                <strong className="kpi-value">{block.unique_order_count.toLocaleString()}</strong>
                <span className="kpi-sub">AOV: {block.average_order_value ? formatMoney(block.average_order_value, block.currency) : 'N/A'}</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">Active SKUs Sold</span>
                <strong className="kpi-value">{block.active_sku_count.toLocaleString()}</strong>
                <span className="kpi-sub">Distinct commercial SKUs</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">Returns &amp; Cancellations</span>
                <strong className="kpi-value danger-text">
                  {formatMoney(Number(block.return_amount) + Number(block.cancellation_amount), block.currency)}
                </strong>
                <span className="kpi-sub">
                  Ret: {block.return_rate_pct ?? '0'}% • Canc: {block.cancellation_rate_pct ?? '0'}%
                </span>
              </div>
            </div>
          )}
        </div>
      ))}

      {/* Time-Series & Period Comparisons Grid */}
      {!loading && (
        <div className="bi-two-col">
          {/* Time-Series Trajectory */}
          <div className="card">
            <div className="module-header-row">
              <div>
                <h3>Sales Time-Series Trajectory</h3>
                <p className="section-desc">Interactive daily, ISO-weekly, or monthly trends.</p>
              </div>
              <div className="pill-toggle-row">
                {(['day', 'week', 'month'] as GranularityType[]).map((g) => (
                  <button
                    key={g}
                    type="button"
                    className={`mini-pill ${granularity === g ? 'active' : ''}`}
                    onClick={() => setGranularity(g)}
                  >
                    {g.toUpperCase()}
                  </button>
                ))}
                <select
                  aria-label="Time-series metric"
                  className="mini-select"
                  value={trendMetric}
                  onChange={(e) => setTrendMetric(e.target.value as 'gross_revenue' | 'net_revenue' | 'gross_units')}
                >
                  <option value="gross_revenue">Gross Revenue</option>
                  <option value="net_revenue">Net Revenue</option>
                  <option value="gross_units">Gross Units</option>
                </select>
              </div>
            </div>

            {activeTsBlocks.map((block) => (
              <div key={block.source_origin} className="sub-source-section">
                <div className="sub-source-title">
                  <span>{block.label}</span>
                  <span className={`currency-badge currency-${block.currency.toLowerCase()}`}>{block.currency}</span>
                </div>
                <SalesTrendChart points={block.points} currency={block.currency} metric={trendMetric} />
              </div>
            ))}
          </div>

          {/* Period-over-Period Comparisons */}
          <div className="card">
            <div className="module-header-row">
              <div>
                <h3>Period-over-Period Variance</h3>
                <p className="section-desc">Safe zero-baseline % comparisons (returns N/A instead of Infinity).</p>
              </div>
              <div className="pill-toggle-row">
                {(['mom', 'qoq', 'yoy'] as ComparisonPeriodType[]).map((p) => (
                  <button
                    key={p}
                    type="button"
                    className={`mini-pill ${periodType === p ? 'active' : ''}`}
                    onClick={() => setPeriodType(p)}
                  >
                    {p.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {activeCompBlocks.map((block) => (
              <div key={block.source_origin} className="sub-source-section">
                <div className="sub-source-title">
                  <span>{block.label}</span>
                  <span className="meta-chip">
                    {block.current_period_label} vs {block.previous_period_label}
                  </span>
                </div>
                {block.coverage_notice && (
                  <p className="coverage-note">{block.coverage_notice}</p>
                )}
                {block.metrics.length === 0 ? (
                  <div className="module-empty-inline">No comparison data for this source.</div>
                ) : (
                  <div className="comp-metrics-grid">
                    {block.metrics.map((m) => {
                      const deltaNum = m.delta_pct !== null ? Number(m.delta_pct) : null
                      const deltaClass =
                        deltaNum === null ? 'neutral' : deltaNum >= 0 ? 'positive' : 'negative'
                      return (
                        <div key={m.metric_key} className="comp-metric-card">
                          <span className="kpi-label">{m.label}</span>
                          <strong className="comp-current">
                            {m.unit === 'GBP' || m.unit === 'INR'
                              ? formatMoney(m.current_value, m.unit)
                              : formatNumber(m.current_value, 0)}
                          </strong>
                          <div className="comp-footer">
                            <span className="kpi-sub">
                              Prev:{' '}
                              {m.unit === 'GBP' || m.unit === 'INR'
                                ? formatMoney(m.previous_value, m.unit)
                                : formatNumber(m.previous_value, 0)}
                            </span>
                            <span className={`delta-badge ${deltaClass}`}>
                              {deltaNum === null ? 'N/A (0 base)' : `${deltaNum >= 0 ? '+' : ''}${m.delta_pct}%`}
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Geographical Country Sales Breakdown */}
      {!loading && (
        <div className="card">
          <div className="module-header-row">
            <div>
              <h3>Geographical Country Sales Breakdown</h3>
              <p className="section-desc">Top markets by gross revenue and share percentage per source.</p>
            </div>
          </div>

          <div className="bi-two-col">
            {activeCountryBlocks.map((block) => (
              <div key={block.source_origin} className="sub-source-section">
                <div className="sub-source-title">
                  <span>{block.label} ({block.total_countries} countries)</span>
                  <span className={`currency-badge currency-${block.currency.toLowerCase()}`}>{block.currency}</span>
                </div>
                <CountryBarChart countries={block.countries} currency={block.currency} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top-Performing & Slow-Moving SKU Rankings */}
      {!loading && (
        <div className="card">
          <div className="module-header-row">
            <div>
              <h3>SKU Velocity Leaderboard ({rankingOrder === 'top' ? 'Top Performing' : 'Slow-Moving Analysis'})</h3>
              <p className="section-desc">
                {rankings?.lifecycle_separation_notice ||
                  'Gross, Returns, Cancellations, and Net performance ranked per source.'}
              </p>
            </div>
            <div className="pill-toggle-row">
              <button
                type="button"
                className={`mini-pill ${rankingOrder === 'top' ? 'active' : ''}`}
                onClick={() => {
                  setRankingOrder('top')
                  setRankingPage(1)
                }}
              >
                Top SKUs
              </button>
              <button
                type="button"
                className={`mini-pill ${rankingOrder === 'slowest' ? 'active' : ''}`}
                onClick={() => {
                  setRankingOrder('slowest')
                  setRankingPage(1)
                }}
              >
                Slow-Moving
              </button>
              <select
                aria-label="Sort SKU rankings by"
                className="mini-select"
                value={rankingSortBy}
                onChange={(e) => {
                  setRankingSortBy(e.target.value as SkuRankingSortBy)
                  setRankingPage(1)
                }}
              >
                <option value="revenue">Sort: Revenue</option>
                <option value="quantity">Sort: Units Sold</option>
                <option value="order_count">Sort: Order Count</option>
              </select>
            </div>
          </div>

          {activeRankingBlocks.map((block) => (
            <div key={block.source_origin} className="sub-source-section">
              <div className="sub-source-title">
                <span>
                  {block.label} — Median Velocity: <strong>{block.catalog_median_daily_velocity} units/day</strong>
                </span>
                <span className="meta-chip">
                  {block.total.toLocaleString()} SKUs • Page {block.page} / {Math.max(1, block.total_pages)}
                </span>
              </div>

              {block.items.length === 0 ? (
                <div className="module-empty-inline">
                  {block.data_span.empty_state_reason || 'No SKU rankings match the current filters.'}
                </div>
              ) : (
                <>
                  <div className="table-scroll">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>SKU</th>
                          <th>Description</th>
                          <th className="num">Gross Units</th>
                          <th className="num">Net Units</th>
                          <th className="num">Gross Revenue</th>
                          <th className="num">Net Revenue</th>
                          <th className="num">Orders</th>
                          <th className="num">Velocity/Day</th>
                          <th>Velocity Flag</th>
                        </tr>
                      </thead>
                      <tbody>
                        {block.items.map((item) => (
                          <tr key={`${block.source_origin}-${item.stock_code}`}>
                            <td>{item.rank}</td>
                            <td className="mono">{item.stock_code}</td>
                            <td>{item.description}</td>
                            <td className="num">{formatNumber(item.gross_units, 0)}</td>
                            <td className="num">{formatNumber(item.net_units, 0)}</td>
                            <td className="num">{formatMoney(item.gross_revenue, block.currency)}</td>
                            <td className="num">{formatMoney(item.net_revenue, block.currency)}</td>
                            <td className="num">{item.order_count.toLocaleString()}</td>
                            <td className="num mono">{item.avg_daily_velocity}</td>
                            <td>
                              <span className={`stage-pill ${item.is_slow_moving ? 'pill-slow' : 'pill-fast'}`}>
                                {item.is_slow_moving ? 'Slow-Moving' : 'Above Median'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {block.total_pages > 1 && (
                    <div className="pagination-bar">
                      <button
                        type="button"
                        className="btn-ghost-sm"
                        disabled={rankingPage <= 1 || loading}
                        onClick={() => setRankingPage((p) => Math.max(1, p - 1))}
                      >
                        ← Previous
                      </button>
                      <span className="pagination-info">
                        Page {block.page} of {block.total_pages}
                      </span>
                      <button
                        type="button"
                        className="btn-ghost-sm"
                        disabled={rankingPage >= block.total_pages || loading}
                        onClick={() => setRankingPage((p) => Math.min(block.total_pages, p + 1))}
                      >
                        Next →
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

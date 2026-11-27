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
  discontinueProduct,
  evaluateLifecycleBatch,
  fetchDeadStock,
  fetchLifecyclePortfolio,
  fetchLifecycleSettings,
  fetchLifecycleSkuDetail,
  resetLifecycleSettings,
  updateLifecycleSettings
} from './api'
import { DiscontinueConfirmModal } from './components/DiscontinueConfirmModal'
import { LifecycleSettingsPanel } from './components/LifecycleSettingsPanel'
import {
  DeadStockResponse,
  LifecycleDetailResponse,
  LifecycleListResponse,
  LifecycleSettingsResponse,
  LifecycleSkuSummary,
  LifecycleSourceFilter,
  LifecycleStage
} from './types'

const CANONICAL_STAGES: readonly LifecycleStage[] = [
  'Introduction',
  'Growth',
  'Maturity',
  'Decline',
  'Discontinued'
] as const

export const ProductLifecycleView: React.FC = () => {
  const { workspace, workspaceDef } = useWorkspace()
  const isStoreManager = workspace === 'store_manager'

  const [activeTab, setActiveTab] = useState<'portfolio' | 'dead_stock' | 'settings'>('portfolio')
  const [sourceOrigin, setSourceOrigin] = useState<LifecycleSourceFilter>('all')
  const [stageFilter, setStageFilter] = useState<LifecycleStage | ''>('')
  const [dormantOnly, setDormantOnly] = useState<boolean>(false)
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [page, setPage] = useState<number>(1)

  const [loading, setLoading] = useState<boolean>(false)
  const [apiError, setApiError] = useState<string | null>(null)
  const [statusBanner, setStatusBanner] = useState<string | null>(null)

  const [portfolio, setPortfolio] = useState<LifecycleListResponse | null>(null)
  const [deadStock, setDeadStock] = useState<DeadStockResponse | null>(null)
  const [settingsRes, setSettingsRes] = useState<LifecycleSettingsResponse | null>(null)

  // Detail & Snapshot Drawer state
  const [selectedDetail, setSelectedDetail] = useState<LifecycleDetailResponse | null>(null)
  const [detailLoading, setDetailLoading] = useState<boolean>(false)

  // Evaluation & Discontinuation modal state
  const [evaluating, setEvaluating] = useState<boolean>(false)
  const [discontinueTarget, setDiscontinueTarget] = useState<LifecycleSkuSummary | null>(null)
  const [discontinueSubmitting, setDiscontinueSubmitting] = useState<boolean>(false)
  const [discontinueError, setDiscontinueError] = useState<string | null>(null)

  // Settings save state
  const [settingsSaving, setSettingsSaving] = useState<boolean>(false)
  const [settingsError, setSettingsError] = useState<string | null>(null)
  const [settingsSuccess, setSettingsSuccess] = useState<string | null>(null)

  const loadPortfolio = useCallback(async () => {
    setLoading(true)
    setApiError(null)
    try {
      const [portRes, deadRes, setRes] = await Promise.all([
        fetchLifecyclePortfolio(
          {
            source_origin: sourceOrigin,
            stage: stageFilter,
            is_dormant_stock: dormantOnly ? true : undefined,
            search: searchQuery,
            page,
            page_size: 15
          },
          workspace
        ),
        fetchDeadStock({ source_origin: sourceOrigin, page: 1, page_size: 25 }, workspace),
        fetchLifecycleSettings(workspace)
      ])
      setPortfolio(portRes)
      setDeadStock(deadRes)
      setSettingsRes(setRes)
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setApiError(`[HTTP ${err.status}] ${err.message}`)
      } else {
        setApiError(err instanceof Error ? err.message : 'Failed to load M08 Product Lifecycle Intelligence.')
      }
    } finally {
      setLoading(false)
    }
  }, [sourceOrigin, stageFilter, dormantOnly, searchQuery, page, workspace])

  useEffect(() => {
    loadPortfolio()
  }, [loadPortfolio])

  const handleInspectSku = async (productId: number) => {
    setDetailLoading(true)
    setApiError(null)
    try {
      const detail = await fetchLifecycleSkuDetail(productId, workspace)
      setSelectedDetail(detail)
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setApiError(`[HTTP ${err.status}] ${err.message}`)
      } else {
        setApiError('Failed to load SKU lifecycle snapshot history.')
      }
    } finally {
      setDetailLoading(false)
    }
  }

  const handleRunEvaluation = async () => {
    setEvaluating(true)
    setApiError(null)
    setStatusBanner(null)
    try {
      // Evaluate the visible page's SKUs for responsive interactive demonstration (or all operational SKUs)
      const visibleCodes = portfolio?.items.map((i) => i.stock_code)
      const res = await evaluateLifecycleBatch(
        {
          source_origin: sourceOrigin,
          stock_codes: visibleCodes && visibleCodes.length > 0 ? visibleCodes : undefined
        },
        workspace
      )
      setStatusBanner(
        `Evaluation complete: ${res.evaluated_count} SKUs evaluated, ${res.transitions_committed} transition(s) committed, ` +
          `${res.hysteresis_buffered_count} buffered by DDR-08 hysteresis, ${res.alerts_emitted} alert(s) emitted ` +
          `(${res.alerts_suppressed_duplicates} duplicate(s) suppressed).`
      )
      await loadPortfolio()
      if (selectedDetail) {
        await handleInspectSku(selectedDetail.sku.product_id)
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setApiError(`[HTTP ${err.status}] ${err.message}`)
      } else {
        setApiError('Failed to execute lifecycle evaluation.')
      }
    } finally {
      setEvaluating(false)
    }
  }

  const handleConfirmDiscontinue = async (payload: { reason: string; operatorRef?: string }) => {
    if (!discontinueTarget) return
    setDiscontinueSubmitting(true)
    setDiscontinueError(null)
    try {
      const res = await discontinueProduct(
        discontinueTarget.product_id,
        {
          confirm_discontinue: true,
          reason: payload.reason,
          operator_ref: payload.operatorRef
        },
        workspace
      )
      setStatusBanner(
        `SKU '${res.stock_code}' transitioned ${res.previous_stage} → Discontinued ` +
          `(Snapshot #${res.snapshot.id}, Tier 1 Audit #${res.audit_log_id}). ${res.excl_04_notice}`
      )
      setDiscontinueTarget(null)
      await loadPortfolio()
      if (selectedDetail && selectedDetail.sku.product_id === res.product_id) {
        await handleInspectSku(res.product_id)
      }
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setDiscontinueError(`[HTTP ${err.status}] ${err.message}`)
      } else {
        setDiscontinueError('Manual discontinuation failed.')
      }
    } finally {
      setDiscontinueSubmitting(false)
    }
  }

  const handleSaveSettings = async (updates: Record<string, string | number | undefined>) => {
    setSettingsSaving(true)
    setSettingsError(null)
    setSettingsSuccess(null)
    try {
      const res = await updateLifecycleSettings(updates, workspace)
      setSettingsRes(res)
      setSettingsSuccess(
        `Bounded lifecycle thresholds saved forward-only (Tier 1 Audit #${res.audit_log_id}). Prior snapshots remain unchanged.`
      )
      await loadPortfolio()
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setSettingsError(`[HTTP ${err.status}] ${err.message}`)
      } else {
        setSettingsError('Failed to save lifecycle settings.')
      }
    } finally {
      setSettingsSaving(false)
    }
  }

  const handleResetSettings = async (operatorRef?: string) => {
    setSettingsSaving(true)
    setSettingsError(null)
    setSettingsSuccess(null)
    try {
      const res = await resetLifecycleSettings(operatorRef, workspace)
      setSettingsRes(res)
      setSettingsSuccess(
        `Lifecycle thresholds reset to system defaults forward-only (Tier 1 Audit #${res.audit_log_id}).`
      )
      await loadPortfolio()
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setSettingsError(`[HTTP ${err.status}] ${err.message}`)
      } else {
        setSettingsError('Failed to reset lifecycle settings.')
      }
    } finally {
      setSettingsSaving(false)
    }
  }

  const handleExportLifecycleCsv = () => {
    if (!portfolio || portfolio.items.length === 0) return
    const headers = [
      'product_id',
      'stock_code',
      'description',
      'source_origin',
      'currency',
      'lifecycle_stage',
      'rolling_velocity',
      'order_frequency',
      'sku_age_days',
      'days_since_last_sale',
      'current_quantity',
      'stock_value',
      'is_dormant_stock',
      'anchor_date'
    ]
    const csv = buildFormulaSafeCsv(
      headers,
      portfolio.items.map((i) => ({ ...i }))
    )
    triggerFileDownload(
      csv,
      `nexora_m08_lifecycle_${new Date().toISOString().slice(0, 10)}.csv`,
      'text/csv;charset=utf-8'
    )
    setStatusBanner(`Exported ${portfolio.items.length} lifecycle rows as formula-safe CSV (SYS-04 handoff).`)
  }

  const totalCatalogCount = portfolio
    ? CANONICAL_STAGES.reduce((acc, st) => acc + portfolio.distribution[st], 0)
    : 0

  return (
    <section className="module-stack" aria-label="M08 Product Lifecycle Intelligence">
      {/* Header & Governance Summary */}
      <div className="card">
        <div className="module-header-row">
          <div>
            <h2>M08 — Product Lifecycle Intelligence</h2>
            <p className="section-desc">
              DDR-08 five-stage classification (Introduction, Growth, Maturity, Decline, Discontinued) with anti-flicker hysteresis, append-only snapshots, and dead-stock review.
            </p>
          </div>
          <div className="module-actions-row">
            <button
              type="button"
              className="btn-primary-sm"
              onClick={handleRunEvaluation}
              disabled={evaluating || loading}
            >
              {evaluating ? 'Evaluating Hysteresis...' : 'Run Evaluation (Visible SKUs)'}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={handleExportLifecycleCsv}
              disabled={loading || !portfolio?.items.length}
            >
              Export CSV
            </button>
          </div>
        </div>

        <div className="workspace-scope-banner">
          <strong>{workspaceDef.label} Scope:</strong> {workspaceDef.m08ScopeNote}
        </div>

        {/* Portfolio Stage Distribution Cards */}
        {portfolio && (
          <>
            <div className="stage-cards-grid">
              {CANONICAL_STAGES.map((stage) => {
                const count = portfolio.distribution[stage]
                const pct = totalCatalogCount > 0 ? ((count / totalCatalogCount) * 100).toFixed(1) : '0.0'
                const active = stageFilter === stage
                return (
                  <button
                    key={stage}
                    type="button"
                    className={`stage-summary-card stage-${stage.toLowerCase()} ${active ? 'selected' : ''}`}
                    onClick={() => {
                      setStageFilter(active ? '' : stage)
                      setPage(1)
                      setActiveTab('portfolio')
                    }}
                  >
                    <span className="stage-card-name">{stage}</span>
                    <strong className="stage-card-count">{count.toLocaleString()}</strong>
                    <span className="stage-card-pct">{pct}% of portfolio</span>
                  </button>
                )
              })}
            </div>

            <div className="policy-strip">
              <span><strong>UCI Anchor:</strong> {portfolio.anchor_notes.uci_historical}</span>
              <span><strong>Dormant Active SKUs:</strong> {portfolio.dormant_stock_count}</span>
            </div>
          </>
        )}

        {/* Sub-Navigation Tabs */}
        <div className="subtab-bar" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'portfolio'}
            className={`subtab-btn ${activeTab === 'portfolio' ? 'active' : ''}`}
            onClick={() => setActiveTab('portfolio')}
          >
            Lifecycle Portfolio
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'dead_stock'}
            className={`subtab-btn ${activeTab === 'dead_stock' ? 'active' : ''}`}
            onClick={() => setActiveTab('dead_stock')}
          >
            Dead-Stock Review ({deadStock?.total_dead_stock_skus ?? 0})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'settings'}
            className={`subtab-btn ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            Bounded Thresholds (DDR-08)
          </button>
        </div>

        {apiError && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon">⛔</span>
            <div>{apiError}</div>
          </div>
        )}
        {statusBanner && (
          <div className="alert alert-success" role="status">
            <span className="alert-icon">✅</span>
            <div>{statusBanner}</div>
          </div>
        )}
      </div>

      {/* TAB 1: Lifecycle Portfolio */}
      {activeTab === 'portfolio' && (
        <div className="card">
          <div className="filter-grid">
            <div className="filter-field">
              <label htmlFor="m08-source">Data Source</label>
              <select
                id="m08-source"
                className="input-text"
                value={sourceOrigin}
                onChange={(e) => {
                  setSourceOrigin(e.target.value as LifecycleSourceFilter)
                  setPage(1)
                }}
              >
                <option value="all">All Catalog Sources</option>
                <option value="operational">Operational Catalog (INR)</option>
                <option value="uci_historical">UCI Historical Baseline (GBP)</option>
              </select>
            </div>

            <div className="filter-field">
              <label htmlFor="m08-stage">Lifecycle Stage</label>
              <select
                id="m08-stage"
                className="input-text"
                value={stageFilter}
                onChange={(e) => {
                  setStageFilter(e.target.value as LifecycleStage | '')
                  setPage(1)
                }}
              >
                <option value="">All 5 Stages</option>
                {CANONICAL_STAGES.map((st) => (
                  <option key={st} value={st}>{st}</option>
                ))}
              </select>
            </div>

            <div className="filter-field">
              <label htmlFor="m08-search">Search SKU / Description</label>
              <input
                id="m08-search"
                type="text"
                className="input-text"
                placeholder="e.g. 85123A"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  setPage(1)
                }}
              />
            </div>

            <div className="filter-field checkbox-filter-wrap">
              <label className="checkbox-row">
                <input
                  type="checkbox"
                  checked={dormantOnly}
                  onChange={(e) => {
                    setDormantOnly(e.target.checked)
                    setPage(1)
                  }}
                />
                <span>Dormant Stock Only</span>
              </label>
            </div>
          </div>

          {loading ? (
            <div className="loading-state">
              <div className="large-spinner" />
              <p className="loading-title">Loading SKU Lifecycle Classifications...</p>
            </div>
          ) : !portfolio || portfolio.items.length === 0 ? (
            <div className="module-empty-inline">
              No catalog SKUs match the selected lifecycle filters.
            </div>
          ) : (
            <>
              <div className="table-scroll">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>SKU</th>
                      <th>Source</th>
                      <th>Stage</th>
                      <th>Hysteresis</th>
                      <th className="num">Velocity/Day</th>
                      <th className="num">Trend %</th>
                      <th className="num">Order Freq</th>
                      <th className="num">Age (d)</th>
                      <th className="num">Last Sale (d)</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolio.items.map((item) => (
                      <tr key={item.product_id}>
                        <td>
                          <strong className="mono">{item.stock_code}</strong>
                          <div className="cell-sub">{item.description}</div>
                        </td>
                        <td>
                          <span className={`currency-badge currency-${item.currency.toLowerCase()}`}>
                            {item.currency}
                          </span>
                        </td>
                        <td>
                          <span className={`stage-pill stage-badge-${item.lifecycle_stage.toLowerCase()}`}>
                            {item.lifecycle_stage}
                          </span>
                          {item.is_dormant_stock && (
                            <span className="dormant-tag" title="Active SKU holding stock beyond inactivity window">
                              Dormant Stock
                            </span>
                          )}
                        </td>
                        <td>
                          {item.pending_candidate_stage ? (
                            <span className="hysteresis-tag">
                              → {item.pending_candidate_stage} ({item.consecutive_candidate_windows}/{item.required_hysteresis_windows})
                            </span>
                          ) : (
                            <span className="cell-sub">Stable</span>
                          )}
                        </td>
                        <td className="num mono">{item.rolling_velocity}</td>
                        <td className="num mono">
                          {item.velocity_trend_pct === null ? 'N/A' : `${item.velocity_trend_pct}%`}
                        </td>
                        <td className="num mono">{item.order_frequency}</td>
                        <td className="num">{item.sku_age_days}</td>
                        <td className="num">{item.days_since_last_sale ?? 'Never'}</td>
                        <td>
                          <div className="row-actions">
                            <button
                              type="button"
                              className="btn-ghost-xs"
                              onClick={() => handleInspectSku(item.product_id)}
                            >
                              History
                            </button>
                            {isStoreManager && item.lifecycle_stage !== 'Discontinued' && (
                              <button
                                type="button"
                                className="btn-danger-xs"
                                onClick={() => {
                                  setDiscontinueError(null)
                                  setDiscontinueTarget(item)
                                }}
                              >
                                Discontinue
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {portfolio.total_pages > 1 && (
                <div className="pagination-bar">
                  <button
                    type="button"
                    className="btn-ghost-sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    ← Previous
                  </button>
                  <span className="pagination-info">
                    Page {portfolio.page} of {portfolio.total_pages} ({portfolio.total.toLocaleString()} SKUs)
                  </span>
                  <button
                    type="button"
                    className="btn-ghost-sm"
                    disabled={page >= portfolio.total_pages}
                    onClick={() => setPage((p) => Math.min(portfolio.total_pages, p + 1))}
                  >
                    Next →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* SKU Trajectory & Immutable Snapshot History Drawer */}
      {(detailLoading || selectedDetail) && (
        <div className="card detail-drawer-card">
          <div className="module-header-row">
            <div>
              <h3>
                SKU Lifecycle Trajectory &amp; Immutable Snapshots
                {selectedDetail && ` — ${selectedDetail.sku.stock_code}`}
              </h3>
              <p className="section-desc">
                {selectedDetail?.classification_explanation || 'Loading trajectory details...'}
              </p>
            </div>
            <button
              type="button"
              className="btn-ghost-sm"
              onClick={() => setSelectedDetail(null)}
            >
              Close Drawer
            </button>
          </div>

          {detailLoading ? (
            <div className="loading-state"><div className="large-spinner" /></div>
          ) : selectedDetail && (
            <>
              <div className="kpi-cards-grid">
                <div className="kpi-card">
                  <span className="kpi-label">Current Stage</span>
                  <strong className="kpi-value">{selectedDetail.sku.lifecycle_stage}</strong>
                  <span className="kpi-sub">Anchor: {selectedDetail.sku.anchor_date}</span>
                </div>
                <div className="kpi-card">
                  <span className="kpi-label">Rolling Velocity</span>
                  <strong className="kpi-value">{selectedDetail.sku.rolling_velocity}/d</strong>
                  <span className="kpi-sub">Prior: {selectedDetail.sku.prior_rolling_velocity}/d</span>
                </div>
                <div className="kpi-card">
                  <span className="kpi-label">Held Stock Value</span>
                  <strong className="kpi-value">
                    {formatMoney(selectedDetail.sku.stock_value, selectedDetail.sku.currency)}
                  </strong>
                  <span className="kpi-sub">
                    Qty: {formatNumber(selectedDetail.sku.current_quantity, 2)} units
                  </span>
                </div>
                <div className="kpi-card">
                  <span className="kpi-label">Recorded Snapshots</span>
                  <strong className="kpi-value">{selectedDetail.snapshot_count}</strong>
                  <span className="kpi-sub">Append-only immutable history</span>
                </div>
              </div>

              {selectedDetail.snapshots.length === 0 ? (
                <div className="module-empty-inline">
                  No persisted lifecycle snapshots yet for this SKU. Click <strong>Run Evaluation</strong> to record an immutable snapshot.
                </div>
              ) : (
                <div className="table-scroll" style={{ marginTop: '1rem' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Snapshot #</th>
                        <th>Evaluated At (UTC)</th>
                        <th>Stage</th>
                        <th>Previous</th>
                        <th>Trigger</th>
                        <th className="num">Velocity</th>
                        <th className="num">Order Freq</th>
                        <th>Dormant</th>
                        <th>Workspace / Ref</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedDetail.snapshots.map((snap) => (
                        <tr key={snap.id}>
                          <td className="mono">#{snap.id}</td>
                          <td className="mono">{snap.evaluated_at.slice(0, 19).replace('T', ' ')}</td>
                          <td>
                            <span className={`stage-pill stage-badge-${snap.lifecycle_stage.toLowerCase()}`}>
                              {snap.lifecycle_stage}
                            </span>
                          </td>
                          <td>{snap.previous_stage ?? '—'}</td>
                          <td className="mono">{snap.trigger_type}</td>
                          <td className="num mono">{snap.rolling_velocity}</td>
                          <td className="num mono">{snap.order_frequency}</td>
                          <td>{snap.is_dormant_stock ? 'Yes' : 'No'}</td>
                          <td>{snap.selected_workspace ?? snap.action_source}{snap.operator_ref ? ` (${snap.operator_ref})` : ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* TAB 2: Dead-Stock Review */}
      {activeTab === 'dead_stock' && (
        <div className="card">
          <div className="module-header-row">
            <div>
              <h3>Dormant / Dead-Stock Active Inventory Review</h3>
              <p className="section-desc">
                {deadStock?.policy_notice ||
                  'Active SKUs holding positive inventory with zero recent sales beyond the inactivity window.'}
              </p>
            </div>
          </div>

          {deadStock && (
            <div className="kpi-cards-grid" style={{ marginBottom: '1.25rem' }}>
              <div className="kpi-card">
                <span className="kpi-label">Dead-Stock SKUs</span>
                <strong className="kpi-value">{deadStock.total_dead_stock_skus}</strong>
                <span className="kpi-sub">Inactivity threshold: ≥ {deadStock.inactivity_threshold_days} days</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">Operational Dead-Stock Capital (INR)</span>
                <strong className="kpi-value">
                  {formatMoney(deadStock.operational_dead_stock_value_inr, 'INR')}
                </strong>
                <span className="kpi-sub">Live warehouse inventory (current_quantity × price)</span>
              </div>
              <div className="kpi-card">
                <span className="kpi-label">UCI Baseline Capital (GBP)</span>
                <strong className="kpi-value">
                  {formatMoney(deadStock.uci_baseline_dead_stock_value_gbp, 'GBP')}
                </strong>
                <span className="kpi-sub">UCI CSV holds no live warehouse stock</span>
              </div>
            </div>
          )}

          {!deadStock || deadStock.items.length === 0 ? (
            <div className="module-empty-inline">
              No dormant dead-stock SKUs with positive warehouse inventory exceed the {deadStock?.inactivity_threshold_days ?? 90}-day inactivity threshold.
            </div>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Description</th>
                    <th>Stage</th>
                    <th className="num">Physical Qty</th>
                    <th className="num">Unit Price</th>
                    <th className="num">Dead-Stock Value</th>
                    <th className="num">Days Inactive</th>
                    <th>Anchor Date</th>
                  </tr>
                </thead>
                <tbody>
                  {deadStock.items.map((item) => (
                    <tr key={item.product_id}>
                      <td className="mono">{item.stock_code}</td>
                      <td>{item.description}</td>
                      <td>
                        <span className={`stage-pill stage-badge-${item.lifecycle_stage.toLowerCase()}`}>
                          {item.lifecycle_stage}
                        </span>
                      </td>
                      <td className="num mono">{formatNumber(item.current_quantity, 2)}</td>
                      <td className="num">{formatMoney(item.current_unit_price, item.currency)}</td>
                      <td className="num"><strong>{formatMoney(item.dead_stock_value, item.currency)}</strong></td>
                      <td className="num">{item.days_since_last_sale ?? `${item.sku_age_days} (no sales)`}</td>
                      <td className="mono">{item.anchor_date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Bounded Threshold Settings */}
      {activeTab === 'settings' && settingsRes && (
        <LifecycleSettingsPanel
          settings={settingsRes.settings}
          isStoreManager={isStoreManager}
          saving={settingsSaving}
          error={settingsError}
          successMessage={settingsSuccess}
          onSave={handleSaveSettings}
          onReset={handleResetSettings}
        />
      )}

      {/* Explicit Confirmation Modal for Manual Discontinued Transition */}
      {discontinueTarget && (
        <DiscontinueConfirmModal
          sku={discontinueTarget}
          submitting={discontinueSubmitting}
          error={discontinueError}
          onCancel={() => setDiscontinueTarget(null)}
          onConfirm={handleConfirmDiscontinue}
        />
      )}
    </section>
  )
}

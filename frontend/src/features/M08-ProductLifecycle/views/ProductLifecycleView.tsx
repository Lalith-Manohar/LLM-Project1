import { useState } from 'react'
import { Activity, Download, History, Play, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { getWorkspaceById } from '@/utils/modules'
import { DiscontinueConfirmModal } from '../components/DiscontinueConfirmModal'
import { LifecycleSettingsPanel } from '../components/LifecycleSettingsPanel'
import {
  useDeadStock,
  useLifecycleMutations,
  useLifecyclePortfolio,
  useLifecycleSettings,
  useLifecycleSkuDetail,
} from '../hooks/useLifecycle'
import { formatLifecycleApiError } from '../services/lifecycleApi'
import type { LifecycleSkuSummary, LifecycleSourceFilter, LifecycleStage } from '../types'

const CANONICAL_STAGES: readonly LifecycleStage[] = [
  'Introduction',
  'Growth',
  'Maturity',
  'Decline',
  'Discontinued',
] as const

const STAGE_BADGE_CLASSES: Record<LifecycleStage, string> = {
  Introduction: 'border-sky-200 bg-sky-50 text-sky-800',
  Growth: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  Maturity: 'border-indigo-200 bg-indigo-50 text-indigo-800',
  Decline: 'border-amber-200 bg-amber-50 text-amber-900',
  Discontinued: 'border-red-200 bg-red-50 text-red-800',
}

const WORKSPACE_M08_SCOPE: Record<string, string> = {
  store_manager:
    'Full UI Access: 5 Stages, Hysteresis Evaluation, Bounded Threshold Config/Reset & Explicit Manual Discontinuation.',
  inventory_staff:
    'View / Review: Dormant dead-stock & Decline-stage inventory review (config & discontinuation reserved for Store Manager).',
  purchase_manager:
    'View / Review: Inspect SKU lifecycle stages and trajectories before approving replenishment orders.',
}

function formatMoney(value: string, currency: 'GBP' | 'INR'): string {
  const num = Number(value)
  if (!Number.isFinite(num)) return value
  const symbol = currency === 'INR' ? '₹' : '£'
  return `${symbol}${num.toLocaleString(currency === 'INR' ? 'en-IN' : 'en-GB', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

const FORMULA_PREFIXES = ['=', '+', '-', '@', '\t', '\r']
function safeCsvCell(value: unknown): string {
  if (value === null || value === undefined) return ''
  const str = String(value)
  const safe = str.length > 0 && FORMULA_PREFIXES.includes(str[0]) ? `'${str}` : str
  return safe.includes(',') || safe.includes('"') || safe.includes('\n')
    ? `"${safe.replace(/"/g, '""')}"`
    : safe
}

export function ProductLifecycleView() {
  const activeWorkspace = useWorkspaceStore((state) => state.activeWorkspace)
  const workspaceDef = getWorkspaceById(activeWorkspace)
  const isStoreManager = activeWorkspace === 'store_manager'

  const [activeTab, setActiveTab] = useState<'portfolio' | 'dead_stock' | 'settings'>('portfolio')
  const [sourceOrigin, setSourceOrigin] = useState<LifecycleSourceFilter>('all')
  const [stageFilter, setStageFilter] = useState<LifecycleStage | ''>('')
  const [dormantOnly, setDormantOnly] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null)
  const [discontinueTarget, setDiscontinueTarget] = useState<LifecycleSkuSummary | null>(null)

  const [statusBanner, setStatusBanner] = useState<string | null>(null)
  const [settingsSuccess, setSettingsSuccess] = useState<string | null>(null)

  const portfolioQuery = useLifecyclePortfolio(
    {
      source_origin: sourceOrigin,
      stage: stageFilter,
      is_dormant_stock: dormantOnly ? true : undefined,
      search: searchQuery,
      page,
      page_size: 15,
    },
    activeWorkspace
  )

  const deadStockQuery = useDeadStock(
    { source_origin: sourceOrigin, page: 1, page_size: 25 },
    activeWorkspace
  )

  const settingsQuery = useLifecycleSettings(activeWorkspace)
  const detailQuery = useLifecycleSkuDetail(selectedProductId, activeWorkspace)

  const {
    evaluateMutation,
    discontinueMutation,
    updateSettingsMutation,
    resetSettingsMutation,
  } = useLifecycleMutations(activeWorkspace)

  const portfolio = portfolioQuery.data
  const deadStock = deadStockQuery.data
  const settingsRes = settingsQuery.data
  const selectedDetail = detailQuery.data

  const totalCatalogCount = portfolio
    ? CANONICAL_STAGES.reduce((sum, st) => sum + portfolio.distribution[st], 0)
    : 0

  const handleRunEvaluation = async () => {
    setStatusBanner(null)
    const visibleCodes = portfolio?.items.map((item) => item.stock_code)
    try {
      const res = await evaluateMutation.mutateAsync({
        source_origin: sourceOrigin,
        stock_codes: visibleCodes && visibleCodes.length > 0 ? visibleCodes : undefined,
      })
      setStatusBanner(
        `Evaluation complete: ${res.evaluated_count} SKUs evaluated, ${res.transitions_committed} transition(s) committed, ` +
          `${res.hysteresis_buffered_count} buffered by DDR-08 hysteresis, ${res.alerts_emitted} alert(s) emitted ` +
          `(${res.alerts_suppressed_duplicates} duplicate(s) suppressed).`
      )
    } catch {
      // Error state is preserved in evaluateMutation.error and rendered via formattedPrimaryError
    }
  }

  const handleConfirmDiscontinue = async (payload: { reason: string; operatorRef?: string }) => {
    if (!discontinueTarget) return
    try {
      const res = await discontinueMutation.mutateAsync({
        productId: discontinueTarget.product_id,
        payload: {
          confirm_discontinue: true,
          reason: payload.reason,
          operator_ref: payload.operatorRef,
        },
      })
      setStatusBanner(
        `SKU '${res.stock_code}' transitioned ${res.previous_stage} → Discontinued ` +
          `(Snapshot #${res.snapshot.id}, Tier 1 Audit #${res.audit_log_id}). ${res.excl_04_notice}`
      )
      setDiscontinueTarget(null)
    } catch {
      // Error state is preserved in discontinueMutation.error and rendered inside DiscontinueConfirmModal
    }
  }

  const handleSaveSettings = async (updates: Record<string, string | number | undefined>) => {
    setSettingsSuccess(null)
    try {
      const res = await updateSettingsMutation.mutateAsync(updates)
      setSettingsSuccess(
        `Bounded lifecycle thresholds saved forward-only (Tier 1 Audit #${res.audit_log_id}). Prior snapshots remain unchanged.`
      )
    } catch {
      // Error state is preserved in updateSettingsMutation.error and rendered in LifecycleSettingsPanel
    }
  }

  const handleResetSettings = async (operatorRef?: string) => {
    setSettingsSuccess(null)
    try {
      const res = await resetSettingsMutation.mutateAsync(operatorRef)
      setSettingsSuccess(
        `Lifecycle thresholds reset to system defaults forward-only (Tier 1 Audit #${res.audit_log_id}).`
      )
    } catch {
      // Error state is preserved in resetSettingsMutation.error and rendered in LifecycleSettingsPanel
    }
  }

  const handleExportCsv = () => {
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
      'anchor_date',
    ]
    const csv = [
      headers.map(safeCsvCell).join(','),
      ...portfolio.items.map((item) =>
        headers.map((h) => safeCsvCell((item as unknown as Record<string, unknown>)[h])).join(',')
      ),
    ].join('\r\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `nexora_m08_lifecycle_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    URL.revokeObjectURL(url)
    setStatusBanner(`Exported ${portfolio.items.length} lifecycle rows as formula-safe CSV (client preview).`)
  }

  const primaryError =
    portfolioQuery.error || deadStockQuery.error || settingsQuery.error || evaluateMutation.error
  const formattedPrimaryError = primaryError ? formatLifecycleApiError(primaryError) : null
  const formattedDiscontinueError = discontinueMutation.error
    ? formatLifecycleApiError(discontinueMutation.error).message
    : null
  const formattedSettingsError =
    updateSettingsMutation.error || resetSettingsMutation.error
      ? formatLifecycleApiError(updateSettingsMutation.error || resetSettingsMutation.error).message
      : null

  return (
    <section className="space-y-6" aria-label="M08 Product Lifecycle Intelligence">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                <Badge variant="outline" className="font-mono">
                  M08
                </Badge>
                <CardTitle className="text-xl">Product Lifecycle Intelligence</CardTitle>
              </div>
              <CardDescription>
                DDR-08 five-stage classification (Introduction, Growth, Maturity, Decline, Discontinued) with anti-flicker hysteresis, immutable snapshots, and dead-stock review.
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                size="sm"
                onClick={() => void handleRunEvaluation()}
                disabled={evaluateMutation.isPending || portfolioQuery.isLoading}
              >
                <Play className="h-4 w-4" />
                {evaluateMutation.isPending ? 'Evaluating Hysteresis...' : 'Run Evaluation'}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleExportCsv}
                disabled={portfolioQuery.isLoading || !portfolio?.items.length}
              >
                <Download className="h-4 w-4" />
                Export CSV
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="rounded-md border bg-primary/5 px-3 py-2 text-xs text-foreground">
            <strong>{workspaceDef.label} Scope:</strong>{' '}
            {WORKSPACE_M08_SCOPE[activeWorkspace] ?? WORKSPACE_M08_SCOPE.store_manager}
          </div>

          {portfolio && (
            <>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {CANONICAL_STAGES.map((stage) => {
                  const count = portfolio.distribution[stage]
                  const pct =
                    totalCatalogCount > 0 ? ((count / totalCatalogCount) * 100).toFixed(1) : '0.0'
                  const selected = stageFilter === stage
                  return (
                    <button
                      key={stage}
                      type="button"
                      onClick={() => {
                        setStageFilter(selected ? '' : stage)
                        setPage(1)
                        setActiveTab('portfolio')
                      }}
                      className={`rounded-lg border p-3 text-left transition-all hover:shadow-sm ${
                        selected ? 'border-primary ring-1 ring-primary bg-primary/5' : 'bg-card'
                      }`}
                    >
                      <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        {stage}
                      </span>
                      <p className="mt-1 font-mono text-2xl font-bold text-foreground">
                        {count.toLocaleString()}
                      </p>
                      <span className="text-xs text-muted-foreground">{pct}% of portfolio</span>
                    </button>
                  )
                })}
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                <span>
                  <strong>UCI Anchor:</strong> {portfolio.anchor_notes.uci_historical}
                </span>
                <span>
                  <strong>Dormant Active SKUs:</strong> {portfolio.dormant_stock_count}
                </span>
              </div>
            </>
          )}

          <div className="flex flex-wrap gap-2 border-t pt-3" role="tablist">
            <Button
              type="button"
              role="tab"
              aria-selected={activeTab === 'portfolio'}
              size="sm"
              variant={activeTab === 'portfolio' ? 'default' : 'outline'}
              onClick={() => setActiveTab('portfolio')}
            >
              Lifecycle Portfolio
            </Button>
            <Button
              type="button"
              role="tab"
              aria-selected={activeTab === 'dead_stock'}
              size="sm"
              variant={activeTab === 'dead_stock' ? 'default' : 'outline'}
              onClick={() => setActiveTab('dead_stock')}
            >
              Dead-Stock Review ({deadStock?.total_dead_stock_skus ?? 0})
            </Button>
            <Button
              type="button"
              role="tab"
              aria-selected={activeTab === 'settings'}
              size="sm"
              variant={activeTab === 'settings' ? 'default' : 'outline'}
              onClick={() => setActiveTab('settings')}
            >
              Bounded Thresholds (DDR-08)
            </Button>
          </div>

          {formattedPrimaryError && (
            <div
              role="alert"
              className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              <span>
                {formattedPrimaryError.status ? `[HTTP ${formattedPrimaryError.status}] ` : ''}
                {formattedPrimaryError.message}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => void portfolioQuery.refetch()}
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </Button>
            </div>
          )}

          {statusBanner && (
            <div
              role="status"
              className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-900"
            >
              {statusBanner}
            </div>
          )}
        </CardContent>
      </Card>

      {activeTab === 'portfolio' && (
        <Card>
          <CardHeader>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-1">
                <label htmlFor="m08-source" className="text-xs font-medium text-muted-foreground">
                  Data Source
                </label>
                <select
                  id="m08-source"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
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

              <div className="space-y-1">
                <label htmlFor="m08-stage" className="text-xs font-medium text-muted-foreground">
                  Lifecycle Stage
                </label>
                <select
                  id="m08-stage"
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                  value={stageFilter}
                  onChange={(e) => {
                    setStageFilter(e.target.value as LifecycleStage | '')
                    setPage(1)
                  }}
                >
                  <option value="">All 5 Stages</option>
                  {CANONICAL_STAGES.map((st) => (
                    <option key={st} value={st}>
                      {st}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1">
                <label htmlFor="m08-search" className="text-xs font-medium text-muted-foreground">
                  Search SKU / Description
                </label>
                <Input
                  id="m08-search"
                  type="text"
                  placeholder="e.g. 85123A"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    setPage(1)
                  }}
                />
              </div>

              <div className="flex items-end pb-2">
                <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-foreground">
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
          </CardHeader>

          <CardContent>
            {portfolioQuery.isLoading ? (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <RefreshCw className="mb-2 h-6 w-6 animate-spin text-primary" />
                <p className="text-sm font-medium text-muted-foreground">
                  Loading SKU Lifecycle Classifications...
                </p>
              </div>
            ) : !portfolio || portfolio.items.length === 0 ? (
              <div className="rounded-lg border border-dashed bg-muted/40 p-6 text-center text-sm text-muted-foreground">
                No catalog SKUs match the selected lifecycle filters.
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>SKU</TableHead>
                      <TableHead>Source</TableHead>
                      <TableHead>Stage</TableHead>
                      <TableHead>Hysteresis</TableHead>
                      <TableHead className="text-right">Velocity/Day</TableHead>
                      <TableHead className="text-right">Trend %</TableHead>
                      <TableHead className="text-right">Order Freq</TableHead>
                      <TableHead className="text-right">Age (d)</TableHead>
                      <TableHead className="text-right">Last Sale (d)</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {portfolio.items.map((item) => (
                      <TableRow key={item.product_id}>
                        <TableCell>
                          <div className="font-mono font-semibold">{item.stock_code}</div>
                          <div className="max-w-xs truncate text-xs text-muted-foreground">
                            {item.description}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="font-mono">
                            {item.currency}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap items-center gap-1">
                            <span
                              className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                                STAGE_BADGE_CLASSES[item.lifecycle_stage]
                              }`}
                            >
                              {item.lifecycle_stage}
                            </span>
                            {item.is_dormant_stock && (
                              <Badge variant="outline" className="border-amber-300 text-amber-800">
                                Dormant
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {item.pending_candidate_stage ? (
                            <Badge variant="secondary" className="font-mono text-xs">
                              → {item.pending_candidate_stage} ({item.consecutive_candidate_windows}/
                              {item.required_hysteresis_windows})
                            </Badge>
                          ) : (
                            <span className="text-xs text-muted-foreground">Stable</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right font-mono">{item.rolling_velocity}</TableCell>
                        <TableCell className="text-right font-mono">
                          {item.velocity_trend_pct === null ? 'N/A' : `${item.velocity_trend_pct}%`}
                        </TableCell>
                        <TableCell className="text-right font-mono">{item.order_frequency}</TableCell>
                        <TableCell className="text-right">{item.sku_age_days}</TableCell>
                        <TableCell className="text-right">
                          {item.days_since_last_sale ?? 'Never'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1.5">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => setSelectedProductId(item.product_id)}
                            >
                              <History className="h-3.5 w-3.5" />
                              History
                            </Button>
                            {isStoreManager && item.lifecycle_stage !== 'Discontinued' && (
                              <Button
                                type="button"
                                variant="destructive"
                                size="sm"
                                onClick={() => {
                                  discontinueMutation.reset()
                                  setDiscontinueTarget(item)
                                }}
                              >
                                Discontinue
                              </Button>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {portfolio.total_pages > 1 && (
                  <div className="mt-4 flex items-center justify-between border-t pt-3">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                    >
                      Previous
                    </Button>
                    <span className="text-xs text-muted-foreground">
                      Page {portfolio.page} of {portfolio.total_pages} ({portfolio.total.toLocaleString()} SKUs)
                    </span>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={page >= portfolio.total_pages}
                      onClick={() => setPage((p) => Math.min(portfolio.total_pages, p + 1))}
                    >
                      Next
                    </Button>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      {selectedProductId !== null && (
        <Card className="border-l-4 border-l-primary">
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <CardTitle className="text-lg">
                  SKU Lifecycle Trajectory &amp; Immutable Snapshots
                  {selectedDetail && ` — ${selectedDetail.sku.stock_code}`}
                </CardTitle>
                <CardDescription>
                  {selectedDetail?.classification_explanation || 'Loading trajectory details...'}
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setSelectedProductId(null)}
              >
                Close Drawer
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {detailQuery.isLoading ? (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Loading snapshot history...
              </div>
            ) : (
              selectedDetail && (
                <>
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="rounded-lg border bg-muted/30 p-3">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">
                        Current Stage
                      </p>
                      <p className="mt-1 font-mono text-lg font-bold">
                        {selectedDetail.sku.lifecycle_stage}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Anchor: {selectedDetail.sku.anchor_date}
                      </p>
                    </div>
                    <div className="rounded-lg border bg-muted/30 p-3">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">
                        Rolling Velocity
                      </p>
                      <p className="mt-1 font-mono text-lg font-bold">
                        {selectedDetail.sku.rolling_velocity}/d
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Prior: {selectedDetail.sku.prior_rolling_velocity}/d
                      </p>
                    </div>
                    <div className="rounded-lg border bg-muted/30 p-3">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">
                        Held Stock Value
                      </p>
                      <p className="mt-1 font-mono text-lg font-bold">
                        {formatMoney(selectedDetail.sku.stock_value, selectedDetail.sku.currency)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Qty: {Number(selectedDetail.sku.current_quantity).toLocaleString()} units
                      </p>
                    </div>
                    <div className="rounded-lg border bg-muted/30 p-3">
                      <p className="text-xs font-semibold uppercase text-muted-foreground">
                        Recorded Snapshots
                      </p>
                      <p className="mt-1 font-mono text-lg font-bold">
                        {selectedDetail.snapshot_count}
                      </p>
                      <p className="text-xs text-muted-foreground">Append-only immutable history</p>
                    </div>
                  </div>

                  {selectedDetail.snapshots.length === 0 ? (
                    <div className="rounded-lg border border-dashed bg-muted/40 p-5 text-center text-sm text-muted-foreground">
                      No persisted lifecycle snapshots yet for this SKU. Click <strong>Run Evaluation</strong> to record an immutable snapshot.
                    </div>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Snapshot #</TableHead>
                          <TableHead>Evaluated At (UTC)</TableHead>
                          <TableHead>Stage</TableHead>
                          <TableHead>Previous</TableHead>
                          <TableHead>Trigger</TableHead>
                          <TableHead className="text-right">Velocity</TableHead>
                          <TableHead className="text-right">Order Freq</TableHead>
                          <TableHead>Dormant</TableHead>
                          <TableHead>Workspace / Ref</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {selectedDetail.snapshots.map((snap) => (
                          <TableRow key={snap.id}>
                            <TableCell className="font-mono">#{snap.id}</TableCell>
                            <TableCell className="font-mono text-xs">
                              {snap.evaluated_at.slice(0, 19).replace('T', ' ')}
                            </TableCell>
                            <TableCell>
                              <span
                                className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${
                                  STAGE_BADGE_CLASSES[snap.lifecycle_stage]
                                }`}
                              >
                                {snap.lifecycle_stage}
                              </span>
                            </TableCell>
                            <TableCell>{snap.previous_stage ?? '—'}</TableCell>
                            <TableCell className="font-mono text-xs">{snap.trigger_type}</TableCell>
                            <TableCell className="text-right font-mono">{snap.rolling_velocity}</TableCell>
                            <TableCell className="text-right font-mono">{snap.order_frequency}</TableCell>
                            <TableCell>{snap.is_dormant_stock ? 'Yes' : 'No'}</TableCell>
                            <TableCell className="text-xs">
                              {snap.selected_workspace ?? snap.action_source}
                              {snap.operator_ref ? ` (${snap.operator_ref})` : ''}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </>
              )
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'dead_stock' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Dormant / Dead-Stock Active Inventory Review</CardTitle>
            <CardDescription>
              {deadStock?.policy_notice ||
                'Active SKUs holding positive inventory with zero recent sales beyond the inactivity window.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {deadStock && (
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-lg border bg-muted/30 p-3">
                  <p className="text-xs font-semibold uppercase text-muted-foreground">
                    Dead-Stock SKUs
                  </p>
                  <p className="mt-1 font-mono text-xl font-bold">{deadStock.total_dead_stock_skus}</p>
                  <p className="text-xs text-muted-foreground">
                    Inactivity threshold: ≥ {deadStock.inactivity_threshold_days} days
                  </p>
                </div>
                <div className="rounded-lg border bg-muted/30 p-3">
                  <p className="text-xs font-semibold uppercase text-muted-foreground">
                    Operational Capital (INR)
                  </p>
                  <p className="mt-1 font-mono text-xl font-bold">
                    {formatMoney(deadStock.operational_dead_stock_value_inr, 'INR')}
                  </p>
                  <p className="text-xs text-muted-foreground">Live warehouse inventory value</p>
                </div>
                <div className="rounded-lg border bg-muted/30 p-3">
                  <p className="text-xs font-semibold uppercase text-muted-foreground">
                    UCI Baseline Capital (GBP)
                  </p>
                  <p className="mt-1 font-mono text-xl font-bold">
                    {formatMoney(deadStock.uci_baseline_dead_stock_value_gbp, 'GBP')}
                  </p>
                  <p className="text-xs text-muted-foreground">UCI CSV holds no live stock</p>
                </div>
              </div>
            )}

            {!deadStock || deadStock.items.length === 0 ? (
              <div className="rounded-lg border border-dashed bg-muted/40 p-6 text-center text-sm text-muted-foreground">
                No dormant dead-stock SKUs with positive warehouse inventory exceed the{' '}
                {deadStock?.inactivity_threshold_days ?? 90}-day inactivity threshold.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>SKU</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Stage</TableHead>
                    <TableHead className="text-right">Physical Qty</TableHead>
                    <TableHead className="text-right">Unit Price</TableHead>
                    <TableHead className="text-right">Dead-Stock Value</TableHead>
                    <TableHead className="text-right">Days Inactive</TableHead>
                    <TableHead>Anchor Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {deadStock.items.map((item) => (
                    <TableRow key={item.product_id}>
                      <TableCell className="font-mono font-semibold">{item.stock_code}</TableCell>
                      <TableCell>{item.description}</TableCell>
                      <TableCell>
                        <span
                          className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${
                            STAGE_BADGE_CLASSES[item.lifecycle_stage]
                          }`}
                        >
                          {item.lifecycle_stage}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {Number(item.current_quantity).toLocaleString()}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatMoney(item.current_unit_price, item.currency)}
                      </TableCell>
                      <TableCell className="text-right font-mono font-bold">
                        {formatMoney(item.dead_stock_value, item.currency)}
                      </TableCell>
                      <TableCell className="text-right">
                        {item.days_since_last_sale ?? `${item.sku_age_days} (no sales)`}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{item.anchor_date}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'settings' && settingsRes && (
        <LifecycleSettingsPanel
          settings={settingsRes.settings}
          isStoreManager={isStoreManager}
          saving={updateSettingsMutation.isPending || resetSettingsMutation.isPending}
          error={formattedSettingsError}
          successMessage={settingsSuccess}
          onSave={(updates) => void handleSaveSettings(updates)}
          onReset={(opRef) => void handleResetSettings(opRef)}
        />
      )}

      <DiscontinueConfirmModal
        sku={discontinueTarget}
        submitting={discontinueMutation.isPending}
        error={formattedDiscontinueError}
        onCancel={() => setDiscontinueTarget(null)}
        onConfirm={(payload) => void handleConfirmDiscontinue(payload)}
      />
    </section>
  )
}

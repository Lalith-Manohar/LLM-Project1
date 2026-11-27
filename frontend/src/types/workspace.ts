/**
 * Canonical NEXORA Stakeholder Workspace types & SYS-04 formula-safe export utilities.
 *
 * Workspace selection is strictly UI operational context and provenance metadata
 * (`X-NEXORA-Workspace`) — NEVER authentication, user accounts, or RBAC.
 */

export type WorkspaceCode =
  | 'store_manager'
  | 'inventory_staff'
  | 'purchase_manager'
  | 'finance_staff'

export interface WorkspaceDefinition {
  code: WorkspaceCode
  label: string
  shortLabel: string
  description: string
  m06ScopeNote: string
  m08ScopeNote: string
}

export const NEXORA_WORKSPACES: readonly WorkspaceDefinition[] = [
  {
    code: 'store_manager',
    label: 'Store Manager (Admin)',
    shortLabel: 'Store Manager',
    description: 'Full executive oversight across all BI analytics, lifecycle configuration, and manual discontinuation governance.',
    m06ScopeNote: 'Full UI Access: All Executive KPIs, Time-Series Trends, Country Breakdown, Comparisons & SKU Rankings.',
    m08ScopeNote: 'Full UI Access: 5 Lifecycle Stages, Bounded Threshold Config/Reset & Explicit Manual Discontinuation.'
  },
  {
    code: 'inventory_staff',
    label: 'Inventory Staff',
    shortLabel: 'Inventory Staff',
    description: 'Warehouse stock turnover, slow-moving SKU monitoring, and dormant/dead-stock capital review.',
    m06ScopeNote: 'Scoped Operational View: Slow-moving SKU velocity & turnover indicators alongside separated source totals.',
    m08ScopeNote: 'View / Review: Dormant dead-stock & Decline-stage inventory review (config & discontinuation reserved for Store Manager).'
  },
  {
    code: 'purchase_manager',
    label: 'Purchase Manager',
    shortLabel: 'Purchase Manager',
    description: 'SKU velocity leaderboards and lifecycle-stage verification prior to replenishment purchase orders.',
    m06ScopeNote: 'Scoped Operational View: SKU velocity rankings & demand trends to inform replenishment planning.',
    m08ScopeNote: 'View / Review: Inspect SKU lifecycle stages and trajectories before approving replenishment orders.'
  },
  {
    code: 'finance_staff',
    label: 'Finance Staff',
    shortLabel: 'Finance Staff',
    description: 'Gross vs. net revenue reconciliation, returns/cancellations impact, country revenue splits, and period comparisons.',
    m06ScopeNote: 'Scoped Operational View: Gross/Net revenue KPIs, returns/cancellations reconciliation, country splits & MoM/QoQ/YoY deltas.',
    m08ScopeNote: 'Read-Only Reference: Dead-stock capital valuation (INR/GBP separated) and lifecycle context.'
  }
] as const

export function getWorkspaceDefinition(code: WorkspaceCode): WorkspaceDefinition {
  return NEXORA_WORKSPACES.find((w) => w.code === code) ?? NEXORA_WORKSPACES[0]
}

/**
 * Formats a Decimal-serialized monetary string cleanly with explicit currency symbol.
 */
export function formatMoney(value: string | number | null | undefined, currency: 'GBP' | 'INR'): string {
  if (value === null || value === undefined || value === '') return '—'
  const num = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(num)) return String(value)
  const symbol = currency === 'INR' ? '₹' : '£'
  const formatted = num.toLocaleString(currency === 'INR' ? 'en-IN' : 'en-GB', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
  return `${symbol}${formatted}`
}

export function formatNumber(value: string | number | null | undefined, maxDecimals = 2): string {
  if (value === null || value === undefined || value === '') return '—'
  const num = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(num)) return String(value)
  return num.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxDecimals
  })
}

/**
 * SYS-04 Formula-Injection Neutralization:
 * Prefixes cells starting with '=', '+', '-', '@', '\t', or '\r' with a single quote.
 */
const FORMULA_PREFIXES = ['=', '+', '-', '@', '\t', '\r']

export function neutralizeCsvCell(value: unknown): string {
  if (value === null || value === undefined) return ''
  const str = String(value)
  const safe = str.length > 0 && FORMULA_PREFIXES.includes(str[0]) ? `'${str}` : str
  if (safe.includes(',') || safe.includes('"') || safe.includes('\n')) {
    return `"${safe.replace(/"/g, '""')}"`
  }
  return safe
}

export function buildFormulaSafeCsv(headers: string[], rows: Record<string, unknown>[]): string {
  const headerLine = headers.map(neutralizeCsvCell).join(',')
  const bodyLines = rows.map((row) => headers.map((h) => neutralizeCsvCell(row[h])).join(','))
  return [headerLine, ...bodyLines].join('\r\n')
}

export function triggerFileDownload(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

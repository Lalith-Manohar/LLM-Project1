/**
 * Formatting and SYS-04 formula-safe export utilities for M06 Business Intelligence.
 */

import type { CurrencyCode } from '../types'

const FORMULA_PREFIXES = ['=', '+', '-', '@', '\t', '\r']

/** Formats DECIMAL monetary string with explicit currency symbol (GBP £ vs INR ₹). */
export function formatCurrencyAmount(
  value: string | number | null | undefined,
  currency: CurrencyCode
): string {
  if (value === null || value === undefined || value === '') return '—'
  const num = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(num)) return String(value)
  const symbol = currency === 'INR' ? '₹' : '£'
  const formatted = num.toLocaleString(currency === 'INR' ? 'en-IN' : 'en-GB', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  return `${symbol}${formatted}`
}

export function formatMetricNumber(
  value: string | number | null | undefined,
  maxDecimals = 2
): string {
  if (value === null || value === undefined || value === '') return '—'
  const num = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(num)) return String(value)
  return num.toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: maxDecimals,
  })
}

/**
 * SYS-04 CSV Formula-Injection Neutralization:
 * Prefixes cells beginning with '=', '+', '-', '@', '\t', or '\r' with a single quote.
 */
export function neutralizeCsvCell(value: unknown): string {
  if (value === null || value === undefined) return ''
  const str = String(value)
  const safe = str.length > 0 && FORMULA_PREFIXES.includes(str[0]) ? `'${str}` : str
  if (safe.includes(',') || safe.includes('"') || safe.includes('\n')) {
    return `"${safe.replace(/"/g, '""')}"`
  }
  return safe
}

export function buildFormulaSafeCsv(
  headers: string[],
  rows: Record<string, unknown>[]
): string {
  const headerLine = headers.map(neutralizeCsvCell).join(',')
  const bodyLines = rows.map((row) =>
    headers.map((h) => neutralizeCsvCell(row[h])).join(',')
  )
  return [headerLine, ...bodyLines].join('\r\n')
}

export function triggerFileDownload(
  content: string,
  filename: string,
  mimeType: string
): void {
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

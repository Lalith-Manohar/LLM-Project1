import { useState } from 'react'
import type { CountryBreakdownItem, CurrencyCode, TimeSeriesPoint } from '../types'
import { formatCurrencyAmount, formatMetricNumber } from '../utils/formatters'

interface SalesTrendChartProps {
  points: TimeSeriesPoint[]
  currency: CurrencyCode
  metric: 'gross_revenue' | 'net_revenue' | 'gross_units'
}

/**
 * Accessible responsive SVG time-series trend chart (zero extra npm dependencies).
 */
export function SalesTrendChart({ points, currency, metric }: SalesTrendChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-dashed bg-muted/40 p-6 text-center text-sm text-muted-foreground">
        No time-series points available for the selected filters.
      </div>
    )
  }

  const width = 760
  const height = 250
  const pad = { top: 20, right: 20, bottom: 42, left: 74 }
  const innerW = width - pad.left - pad.right
  const innerH = height - pad.top - pad.bottom

  const values = points.map((p) => Number(p[metric]))
  const maxVal = Math.max(...values, 1)
  const minVal = Math.min(...values, 0)
  const range = Math.max(maxVal - minVal, 1)

  const coords = points.map((p, idx) => {
    const x =
      points.length === 1
        ? pad.left + innerW / 2
        : pad.left + (idx / (points.length - 1)) * innerW
    const y = pad.top + innerH - ((Number(p[metric]) - minVal) / range) * innerH
    return { x, y, point: p }
  })

  const linePath = coords
    .map((c, idx) => `${idx === 0 ? 'M' : 'L'} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
    .join(' ')
  const areaPath =
    coords.length > 1
      ? `${linePath} L ${coords[coords.length - 1].x.toFixed(1)} ${(pad.top + innerH).toFixed(1)} L ${coords[0].x.toFixed(1)} ${(pad.top + innerH).toFixed(1)} Z`
      : ''

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => minVal + t * range)
  const xStep = Math.max(1, Math.ceil(points.length / 8))

  const formatMetricVal = (val: string | number) =>
    metric === 'gross_units'
      ? `${formatMetricNumber(val, 0)} units`
      : formatCurrencyAmount(val, currency)

  const activePoint = hoveredIdx !== null ? coords[hoveredIdx] : null

  return (
    <div className="w-full space-y-2">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="h-auto w-full"
        role="img"
        aria-label={`Sales ${metric.replace('_', ' ')} trend chart (${currency})`}
      >
        {yTicks.map((tickVal, idx) => {
          const y = pad.top + innerH - ((tickVal - minVal) / range) * innerH
          return (
            <g key={idx}>
              <line
                x1={pad.left}
                x2={width - pad.right}
                y1={y}
                y2={y}
                stroke="hsl(var(--border))"
                strokeDasharray="3 3"
              />
              <text
                x={pad.left - 8}
                y={y + 4}
                textAnchor="end"
                fontSize="11"
                fill="hsl(var(--muted-foreground))"
              >
                {metric === 'gross_units'
                  ? formatMetricNumber(tickVal, 0)
                  : `${currency === 'INR' ? '₹' : '£'}${Math.round(tickVal).toLocaleString()}`}
              </text>
            </g>
          )
        })}

        {areaPath && <path d={areaPath} fill="hsl(var(--primary) / 0.12)" />}
        <path
          d={linePath}
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="2.5"
          strokeLinejoin="round"
        />

        {coords.map((c, idx) => (
          <g key={c.point.period_key}>
            <circle
              cx={c.x}
              cy={c.y}
              r={hoveredIdx === idx ? 5.5 : 3.5}
              fill="hsl(var(--primary))"
              stroke="#ffffff"
              strokeWidth="1.5"
              className="cursor-pointer"
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
            />
            {(idx % xStep === 0 || idx === coords.length - 1) && (
              <text
                x={c.x}
                y={height - 14}
                textAnchor="middle"
                fontSize="10.5"
                fill="hsl(var(--muted-foreground))"
              >
                {c.point.period_key}
              </text>
            )}
          </g>
        ))}
      </svg>

      {activePoint && (
        <div className="flex flex-wrap gap-3 rounded-md border bg-muted/40 px-3 py-2 text-xs">
          <strong>{activePoint.point.period_key}</strong>
          <span className="text-muted-foreground">
            ({activePoint.point.period_start} to {activePoint.point.period_end})
          </span>
          <span>
            Gross: <strong>{formatCurrencyAmount(activePoint.point.gross_revenue, currency)}</strong>
          </span>
          <span>
            Net: <strong>{formatCurrencyAmount(activePoint.point.net_revenue, currency)}</strong>
          </span>
          <span>
            Units: <strong>{formatMetricNumber(activePoint.point.gross_units, 0)}</strong>
          </span>
          <span>
            Orders: <strong>{activePoint.point.order_count.toLocaleString()}</strong>
          </span>
          <span>
            Selected: <strong>{formatMetricVal(activePoint.point[metric])}</strong>
          </span>
        </div>
      )}
    </div>
  )
}

interface CountryBarChartProps {
  countries: CountryBreakdownItem[]
  currency: CurrencyCode
}

export function CountryBarChart({ countries, currency }: CountryBarChartProps) {
  if (countries.length === 0) {
    return (
      <div className="rounded-lg border border-dashed bg-muted/40 p-6 text-center text-sm text-muted-foreground">
        No country-level sales breakdown available for the selected filters.
      </div>
    )
  }

  const maxRev = Math.max(...countries.map((c) => Number(c.gross_revenue)), 1)

  return (
    <div className="space-y-2.5" role="list" aria-label={`Country sales breakdown (${currency})`}>
      {countries.map((item) => {
        const pctWidth = Math.max(2, (Number(item.gross_revenue) / maxRev) * 100)
        return (
          <div key={item.country} className="space-y-1" role="listitem">
            <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs">
              <span className="font-medium text-foreground">{item.country}</span>
              <span className="flex items-center gap-2 font-mono">
                <strong>{formatCurrencyAmount(item.gross_revenue, currency)}</strong>
                <span className="font-semibold text-primary">{item.revenue_share_pct}%</span>
                <span className="text-muted-foreground">
                  ({item.order_count.toLocaleString()} orders)
                </span>
              </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${pctWidth}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

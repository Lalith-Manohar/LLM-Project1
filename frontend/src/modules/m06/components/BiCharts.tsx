import React, { useState } from 'react'
import { formatMoney, formatNumber } from '../../../types/workspace'
import { CountryBreakdownItem, CurrencyCode, TimeSeriesPoint } from '../types'

interface SalesTrendChartProps {
  points: TimeSeriesPoint[]
  currency: CurrencyCode
  metric: 'gross_revenue' | 'net_revenue' | 'gross_units'
}

/**
 * Accessible, zero-dependency responsive SVG area/line chart for M06 time-series trends.
 * Swap-ready for Chart.js / react-chartjs-2 once Phase 3 adds charting packages.
 */
export const SalesTrendChart: React.FC<SalesTrendChartProps> = ({ points, currency, metric }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  if (points.length === 0) {
    return (
      <div className="module-empty-inline">
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

  const linePath = coords.map((c, idx) => `${idx === 0 ? 'M' : 'L'} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`).join(' ')
  const areaPath =
    coords.length > 1
      ? `${linePath} L ${coords[coords.length - 1].x.toFixed(1)} ${(pad.top + innerH).toFixed(1)} L ${coords[0].x.toFixed(1)} ${(pad.top + innerH).toFixed(1)} Z`
      : ''

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => minVal + t * range)
  const xStep = Math.max(1, Math.ceil(points.length / 8))

  const formatMetricVal = (val: string | number) =>
    metric === 'gross_units' ? `${formatNumber(val, 0)} units` : formatMoney(val, currency)

  const activePoint = hoveredIdx !== null ? coords[hoveredIdx] : null

  return (
    <div className="chart-shell">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="bi-svg-chart"
        role="img"
        aria-label={`Sales ${metric.replace('_', ' ')} trend chart (${currency})`}
      >
        {/* Horizontal gridlines + Y-axis labels */}
        {yTicks.map((tickVal, idx) => {
          const y = pad.top + innerH - ((tickVal - minVal) / range) * innerH
          return (
            <g key={idx}>
              <line
                x1={pad.left}
                x2={width - pad.right}
                y1={y}
                y2={y}
                stroke="#e2e8f0"
                strokeDasharray="3 3"
              />
              <text
                x={pad.left - 8}
                y={y + 4}
                textAnchor="end"
                fontSize="11"
                fill="#64748b"
              >
                {metric === 'gross_units'
                  ? formatNumber(tickVal, 0)
                  : `${currency === 'INR' ? '₹' : '£'}${Math.round(tickVal).toLocaleString()}`}
              </text>
            </g>
          )
        })}

        {/* Area & Line */}
        {areaPath && <path d={areaPath} fill="rgba(79, 70, 229, 0.10)" />}
        <path d={linePath} fill="none" stroke="#4f46e5" strokeWidth="2.5" strokeLinejoin="round" />

        {/* Data points */}
        {coords.map((c, idx) => (
          <g key={c.point.period_key}>
            <circle
              cx={c.x}
              cy={c.y}
              r={hoveredIdx === idx ? 5.5 : 3.5}
              fill={hoveredIdx === idx ? '#4338ca' : '#4f46e5'}
              stroke="#ffffff"
              strokeWidth="1.5"
              style={{ cursor: 'pointer' }}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
            />
            {(idx % xStep === 0 || idx === coords.length - 1) && (
              <text
                x={c.x}
                y={height - 14}
                textAnchor="middle"
                fontSize="10.5"
                fill="#64748b"
              >
                {c.point.period_key}
              </text>
            )}
          </g>
        ))}
      </svg>

      {activePoint && (
        <div className="chart-hover-bar">
          <strong>{activePoint.point.period_key}</strong>
          <span>({activePoint.point.period_start} to {activePoint.point.period_end})</span>
          <span>Gross: <strong>{formatMoney(activePoint.point.gross_revenue, currency)}</strong></span>
          <span>Net: <strong>{formatMoney(activePoint.point.net_revenue, currency)}</strong></span>
          <span>Units: <strong>{formatNumber(activePoint.point.gross_units, 0)}</strong></span>
          <span>Orders: <strong>{activePoint.point.order_count.toLocaleString()}</strong></span>
          <span>Selected: <strong>{formatMetricVal(activePoint.point[metric])}</strong></span>
        </div>
      )}
    </div>
  )
}

interface CountryBarChartProps {
  countries: CountryBreakdownItem[]
  currency: CurrencyCode
}

export const CountryBarChart: React.FC<CountryBarChartProps> = ({ countries, currency }) => {
  if (countries.length === 0) {
    return (
      <div className="module-empty-inline">
        No country-level sales breakdown available for the selected filters.
      </div>
    )
  }

  const maxRev = Math.max(...countries.map((c) => Number(c.gross_revenue)), 1)

  return (
    <div className="country-bars-list" role="list" aria-label={`Country sales breakdown (${currency})`}>
      {countries.map((item) => {
        const pctWidth = Math.max(2, (Number(item.gross_revenue) / maxRev) * 100)
        return (
          <div key={item.country} className="country-bar-row" role="listitem">
            <div className="country-bar-meta">
              <span className="country-name">{item.country}</span>
              <span className="country-metrics">
                <strong>{formatMoney(item.gross_revenue, currency)}</strong>
                <span className="country-share">{item.revenue_share_pct}%</span>
                <span className="country-orders">({item.order_count.toLocaleString()} orders)</span>
              </span>
            </div>
            <div className="country-bar-track">
              <div className="country-bar-fill" style={{ width: `${pctWidth}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

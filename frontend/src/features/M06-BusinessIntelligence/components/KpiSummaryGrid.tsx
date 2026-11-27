import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { SourceKpiBlock } from '../types'
import { formatCurrencyAmount, formatMetricNumber } from '../utils/formatters'

interface KpiSummaryGridProps {
  blocks: SourceKpiBlock[]
}

export function KpiSummaryGrid({ blocks }: KpiSummaryGridProps) {
  return (
    <div className="space-y-4">
      {blocks.map((block) => (
        <Card key={block.source_origin}>
          <CardHeader className="pb-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <CardTitle className="text-lg">{block.label}</CardTitle>
                <CardDescription>
                  {block.data_span.has_data
                    ? `Data Span: ${block.data_span.start_date} to ${block.data_span.end_date} (${block.data_span.record_count.toLocaleString()} stream line items)`
                    : block.data_span.empty_state_reason}
                </CardDescription>
              </div>
              <Badge
                variant={block.currency === 'INR' ? 'default' : 'secondary'}
                className="font-mono"
              >
                {block.currency} • {block.source_origin}
              </Badge>
            </div>
          </CardHeader>

          <CardContent>
            {!block.data_span.has_data ? (
              <div className="rounded-lg border border-dashed bg-muted/40 p-6 text-center text-sm text-muted-foreground">
                {block.data_span.empty_state_reason}
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
                <div className="rounded-lg border bg-muted/30 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Gross Revenue
                  </p>
                  <p className="mt-1 font-mono text-lg font-bold text-foreground">
                    {formatCurrencyAmount(block.gross_revenue, block.currency)}
                  </p>
                  <p className="text-xs text-muted-foreground">Positive sales stream only</p>
                </div>

                <div className="rounded-lg border bg-muted/30 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Net Revenue
                  </p>
                  <p className="mt-1 font-mono text-lg font-bold text-foreground">
                    {formatCurrencyAmount(block.net_revenue, block.currency)}
                  </p>
                  <p className="text-xs text-muted-foreground">Net of returns &amp; cancellations</p>
                </div>

                <div className="rounded-lg border bg-muted/30 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Gross / Net Units
                  </p>
                  <p className="mt-1 font-mono text-lg font-bold text-foreground">
                    {formatMetricNumber(block.gross_units_sold, 0)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Net: {formatMetricNumber(block.net_units_sold, 0)} units
                  </p>
                </div>

                <div className="rounded-lg border bg-muted/30 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Unique Orders
                  </p>
                  <p className="mt-1 font-mono text-lg font-bold text-foreground">
                    {block.unique_order_count.toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    AOV:{' '}
                    {block.average_order_value
                      ? formatCurrencyAmount(block.average_order_value, block.currency)
                      : 'N/A'}
                  </p>
                </div>

                <div className="rounded-lg border bg-muted/30 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Active SKUs Sold
                  </p>
                  <p className="mt-1 font-mono text-lg font-bold text-foreground">
                    {block.active_sku_count.toLocaleString()}
                  </p>
                  <p className="text-xs text-muted-foreground">Distinct commercial SKUs</p>
                </div>

                <div className="rounded-lg border bg-muted/30 p-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Returns &amp; Cancels
                  </p>
                  <p className="mt-1 font-mono text-lg font-bold text-destructive">
                    {formatCurrencyAmount(
                      Number(block.return_amount) + Number(block.cancellation_amount),
                      block.currency
                    )}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Ret: {block.return_rate_pct ?? '0'}% • Canc: {block.cancellation_rate_pct ?? '0'}%
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

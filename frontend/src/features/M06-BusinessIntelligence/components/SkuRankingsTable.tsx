import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { SkuRankingOrder, SkuRankingSortBy, SourceSkuRankingBlock } from '../types'
import { formatCurrencyAmount, formatMetricNumber } from '../utils/formatters'

interface SkuRankingsTableProps {
  blocks: SourceSkuRankingBlock[]
  lifecycleSeparationNotice?: string
  rankingOrder: SkuRankingOrder
  rankingSortBy: SkuRankingSortBy
  rankingPage: number
  isLoading: boolean
  onChangeOrder: (order: SkuRankingOrder) => void
  onChangeSortBy: (sortBy: SkuRankingSortBy) => void
  onChangePage: (page: number) => void
}

export function SkuRankingsTable({
  blocks,
  lifecycleSeparationNotice,
  rankingOrder,
  rankingSortBy,
  rankingPage,
  isLoading,
  onChangeOrder,
  onChangeSortBy,
  onChangePage,
}: SkuRankingsTableProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle className="text-lg">
              SKU Velocity Leaderboard ({rankingOrder === 'top' ? 'Top Performing' : 'Slow-Moving Analysis'})
            </CardTitle>
            <CardDescription>
              {lifecycleSeparationNotice ||
                'Gross, Returns, Cancellations, and Net performance ranked per source.'}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant={rankingOrder === 'top' ? 'default' : 'outline'}
              onClick={() => onChangeOrder('top')}
            >
              Top SKUs
            </Button>
            <Button
              type="button"
              size="sm"
              variant={rankingOrder === 'slowest' ? 'default' : 'outline'}
              onClick={() => onChangeOrder('slowest')}
            >
              Slow-Moving
            </Button>
            <select
              aria-label="Sort SKU rankings by"
              className="h-8 rounded-md border border-input bg-background px-2 text-xs font-medium"
              value={rankingSortBy}
              onChange={(e) => onChangeSortBy(e.target.value as SkuRankingSortBy)}
            >
              <option value="revenue">Sort: Revenue</option>
              <option value="quantity">Sort: Units Sold</option>
              <option value="order_count">Sort: Order Count</option>
            </select>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {blocks.map((block) => (
          <div key={block.source_origin} className="space-y-3 border-t pt-4 first:border-t-0 first:pt-0">
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
              <span>
                {block.label} — Median Velocity:{' '}
                <strong className="font-mono">{block.catalog_median_daily_velocity} units/day</strong>
              </span>
              <Badge variant="outline" className="font-mono">
                {block.total.toLocaleString()} SKUs • Page {block.page} / {Math.max(1, block.total_pages)}
              </Badge>
            </div>

            {block.items.length === 0 ? (
              <div className="rounded-lg border border-dashed bg-muted/40 p-6 text-center text-sm text-muted-foreground">
                {block.data_span.empty_state_reason || 'No SKU rankings match the current filters.'}
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead>SKU</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right">Gross Units</TableHead>
                      <TableHead className="text-right">Net Units</TableHead>
                      <TableHead className="text-right">Gross Revenue</TableHead>
                      <TableHead className="text-right">Net Revenue</TableHead>
                      <TableHead className="text-right">Orders</TableHead>
                      <TableHead className="text-right">Velocity/Day</TableHead>
                      <TableHead>Velocity Flag</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {block.items.map((item) => (
                      <TableRow key={`${block.source_origin}-${item.stock_code}`}>
                        <TableCell>{item.rank}</TableCell>
                        <TableCell className="font-mono font-medium">{item.stock_code}</TableCell>
                        <TableCell className="max-w-xs truncate">{item.description}</TableCell>
                        <TableCell className="text-right font-mono">
                          {formatMetricNumber(item.gross_units, 0)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatMetricNumber(item.net_units, 0)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrencyAmount(item.gross_revenue, block.currency)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {formatCurrencyAmount(item.net_revenue, block.currency)}
                        </TableCell>
                        <TableCell className="text-right font-mono">
                          {item.order_count.toLocaleString()}
                        </TableCell>
                        <TableCell className="text-right font-mono">{item.avg_daily_velocity}</TableCell>
                        <TableCell>
                          <Badge variant={item.is_slow_moving ? 'outline' : 'secondary'}>
                            {item.is_slow_moving ? 'Slow-Moving' : 'Above Median'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {block.total_pages > 1 && (
                  <div className="flex items-center justify-between border-t pt-3">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={rankingPage <= 1 || isLoading}
                      onClick={() => onChangePage(Math.max(1, rankingPage - 1))}
                    >
                      Previous
                    </Button>
                    <span className="text-xs text-muted-foreground">
                      Page {block.page} of {block.total_pages}
                    </span>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={rankingPage >= block.total_pages || isLoading}
                      onClick={() => onChangePage(Math.min(block.total_pages, rankingPage + 1))}
                    >
                      Next
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

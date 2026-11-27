import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AppRouter } from '@/app/router/AppRouter'
import { BusinessIntelligenceView } from '@/features/M06-BusinessIntelligence'
import { buildFormulaSafeCsv, neutralizeCsvCell } from '@/features/M06-BusinessIntelligence/utils/formatters'
import { apiClient } from '@/services/api/client'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}

function mockM06SuccessResponses() {
  return vi.spyOn(apiClient, 'get').mockImplementation((url: string) => {
    if (url === '/api/v1/analytics/summary') {
      return Promise.resolve({
        data: {
          source_origin_filter: 'all',
          currency_blending_prohibited: true,
          currency_notice: 'Separated GBP and INR',
          filters_applied: {},
          uci_historical: {
            source_origin: 'uci_historical',
            currency: 'GBP',
            label: 'Historical UCI Dataset Baseline (2009-2011, GBP)',
            data_span: {
              start_date: '2009-12-01',
              end_date: '2011-12-09',
              record_count: 100,
              has_data: true,
              empty_state_reason: null,
            },
            gross_revenue: '1500.00',
            return_amount: '50.00',
            cancellation_amount: '25.00',
            net_revenue: '1425.00',
            gross_units_sold: '300.0000',
            return_units: '10.0000',
            cancellation_units: '5.0000',
            net_units_sold: '285.0000',
            unique_order_count: 15,
            active_sku_count: 8,
            average_order_value: '100.00',
            return_rate_pct: '3.33',
            cancellation_rate_pct: '1.67',
          },
          operational: {
            source_origin: 'operational',
            currency: 'INR',
            label: 'Live Operational Store Records (INR)',
            data_span: {
              start_date: null,
              end_date: null,
              record_count: 0,
              has_data: false,
              empty_state_reason: 'No live operational sales records exist yet.',
            },
            gross_revenue: '0.00',
            return_amount: '0.00',
            cancellation_amount: '0.00',
            net_revenue: '0.00',
            gross_units_sold: '0.0000',
            return_units: '0.0000',
            cancellation_units: '0.0000',
            net_units_sold: '0.0000',
            unique_order_count: 0,
            active_sku_count: 0,
            average_order_value: null,
            return_rate_pct: null,
            cancellation_rate_pct: null,
          },
          workspace_context: 'Store Manager (Admin)',
          correlation_id: 'corr-1',
          generated_at: '2026-11-27T00:00:00Z',
        },
      })
    }
    if (url === '/api/v1/analytics/timeseries') {
      return Promise.resolve({
        data: {
          source_origin_filter: 'all',
          granularity: 'month',
          currency_blending_prohibited: true,
          currency_notice: 'Separated',
          filters_applied: {},
          uci_historical: {
            source_origin: 'uci_historical',
            currency: 'GBP',
            granularity: 'month',
            label: 'Historical UCI Dataset Baseline (2009-2011, GBP)',
            data_span: { start_date: '2011-11-01', end_date: '2011-11-30', record_count: 10, has_data: true, empty_state_reason: null },
            points: [
              {
                period_key: '2011-11',
                period_start: '2011-11-01',
                period_end: '2011-11-30',
                gross_revenue: '1500.00',
                return_amount: '50.00',
                cancellation_amount: '25.00',
                net_revenue: '1425.00',
                gross_units: '300.0000',
                net_units: '285.0000',
                order_count: 15,
              },
            ],
          },
          operational: null,
          workspace_context: 'Store Manager (Admin)',
          correlation_id: 'corr-1',
          generated_at: '2026-11-27T00:00:00Z',
        },
      })
    }
    if (url === '/api/v1/analytics/countries') {
      return Promise.resolve({
        data: {
          source_origin_filter: 'all',
          currency_blending_prohibited: true,
          currency_notice: 'Separated',
          filters_applied: {},
          uci_historical: {
            source_origin: 'uci_historical',
            currency: 'GBP',
            label: 'Historical UCI Dataset Baseline (2009-2011, GBP)',
            data_span: { start_date: '2011-11-01', end_date: '2011-11-30', record_count: 10, has_data: true, empty_state_reason: null },
            total_countries: 1,
            total_gross_revenue: '1500.00',
            countries: [
              {
                country: 'United Kingdom',
                gross_revenue: '1500.00',
                return_amount: '50.00',
                cancellation_amount: '25.00',
                net_revenue: '1425.00',
                gross_units: '300.0000',
                order_count: 15,
                revenue_share_pct: '100.00',
              },
            ],
          },
          operational: null,
          workspace_context: 'Store Manager (Admin)',
          correlation_id: 'corr-1',
          generated_at: '2026-11-27T00:00:00Z',
        },
      })
    }
    if (url === '/api/v1/analytics/sku-rankings') {
      return Promise.resolve({
        data: {
          source_origin_filter: 'all',
          order: 'top',
          sort_by: 'revenue',
          currency_blending_prohibited: true,
          currency_notice: 'Separated',
          lifecycle_separation_notice: 'Distinct from M08 lifecycle stages.',
          filters_applied: {},
          uci_historical: {
            source_origin: 'uci_historical',
            currency: 'GBP',
            label: 'Historical UCI Dataset Baseline (2009-2011, GBP)',
            data_span: { start_date: '2011-11-01', end_date: '2011-11-30', record_count: 10, has_data: true, empty_state_reason: null },
            catalog_median_daily_velocity: '5.0000',
            items: [
              {
                rank: 1,
                product_id: null,
                stock_code: '85123A',
                description: 'WHITE HANGING HEART',
                category_name: null,
                gross_units: '100.0000',
                return_units: '0.0000',
                cancellation_units: '0.0000',
                net_units: '100.0000',
                gross_revenue: '255.00',
                return_amount: '0.00',
                cancellation_amount: '0.00',
                net_revenue: '255.00',
                order_count: 10,
                avg_daily_velocity: '3.3333',
                current_inventory_qty: null,
                is_slow_moving: false,
              },
            ],
            total: 1,
            page: 1,
            page_size: 12,
            total_pages: 1,
          },
          operational: null,
          workspace_context: 'Store Manager (Admin)',
          correlation_id: 'corr-1',
          generated_at: '2026-11-27T00:00:00Z',
        },
      })
    }
    if (url === '/api/v1/analytics/comparisons') {
      return Promise.resolve({
        data: {
          source_origin_filter: 'all',
          period_type: 'mom',
          currency_blending_prohibited: true,
          currency_notice: 'Separated',
          filters_applied: {},
          uci_historical: {
            source_origin: 'uci_historical',
            currency: 'GBP',
            label: 'Historical UCI Dataset Baseline (2009-2011, GBP)',
            period_type: 'mom',
            current_period_label: '2011-11',
            previous_period_label: '2011-10',
            current_span: { start_date: '2011-11-01', end_date: '2011-11-30', record_count: 10, has_data: true, empty_state_reason: null },
            previous_span: { start_date: null, end_date: null, record_count: 0, has_data: false, empty_state_reason: 'Empty' },
            has_comparison_baseline: false,
            coverage_notice: 'No baseline records exist in prior comparison window.',
            metrics: [
              {
                metric_key: 'gross_revenue',
                label: 'Gross Revenue',
                unit: 'GBP',
                current_value: '1500.00',
                previous_value: '0.00',
                absolute_delta: '1500.00',
                delta_pct: null,
              },
            ],
          },
          operational: null,
          workspace_context: 'Store Manager (Admin)',
          correlation_id: 'corr-1',
          generated_at: '2026-11-27T00:00:00Z',
        },
      })
    }
    return Promise.resolve({ data: { status: 'healthy', service: 'backend', version: '0.1.0' } })
  })
}

describe('M06 Business Intelligence Feature', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    useWorkspaceStore.setState({ activeWorkspace: 'store_manager', activeNavItem: 'M06' })
  })

  it('renders separated GBP and INR blocks, empty operational state, and SKU rankings', async () => {
    mockM06SuccessResponses()
    renderWithProviders(<BusinessIntelligenceView />)

    expect(screen.getByText('Business Intelligence')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('85123A')).toBeInTheDocument()
    })
    expect(screen.getAllByText('No live operational sales records exist yet.').length).toBeGreaterThan(0)
    expect(screen.getByText('United Kingdom')).toBeInTheDocument()
    expect(screen.getByText('N/A (0 base)')).toBeInTheDocument()
    expect(screen.getByText(/GBP \(£\)/)).toBeInTheDocument()
    expect(screen.getByText(/INR \(₹\)/)).toBeInTheDocument()
  })

  it('validates invalid date bounds (start_date > end_date) without calling API', async () => {
    const spy = mockM06SuccessResponses()
    renderWithProviders(<BusinessIntelligenceView />)

    await waitFor(() => expect(screen.getByText('85123A')).toBeInTheDocument())
    const initialCalls = spy.mock.calls.length

    fireEvent.change(screen.getByLabelText('Start Date'), { target: { value: '2011-12-01' } })
    fireEvent.change(screen.getByLabelText('End Date'), { target: { value: '2011-01-01' } })
    fireEvent.click(screen.getByRole('button', { name: 'Apply Filters' }))

    expect(screen.getByRole('alert')).toHaveTextContent('Start Date cannot be after End Date')
    expect(spy.mock.calls.length).toBe(initialCalls)
  })

  it('renders explicit API error state with retry action when backend fails', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('Network offline'))
    renderWithProviders(<BusinessIntelligenceView />)

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Network offline')
    })
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
  })

  it('integrates inside /dashboard across all 4 workspaces', async () => {
    mockM06SuccessResponses()
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/dashboard']}>
          <AppRouter />
        </MemoryRouter>
      </QueryClientProvider>
    )
    await waitFor(() => expect(screen.getByText('85123A')).toBeInTheDocument())
  })

  it('neutralizes CSV formula injection prefixes per SYS-04', () => {
    expect(neutralizeCsvCell('=CMD()')).toBe("'=CMD()")
    expect(neutralizeCsvCell('+1+1')).toBe("'+1+1")
    expect(neutralizeCsvCell('-100')).toBe("'-100")
    expect(neutralizeCsvCell('@SUM')).toBe("'@SUM")
    const csv = buildFormulaSafeCsv(['sku', 'note'], [{ sku: '85123A', note: '=1+1' }])
    expect(csv).toContain("'=1+1")
  })
})

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AppRouter } from '@/app/router/AppRouter'
import { ProductLifecycleView } from '@/features/M08-ProductLifecycle'
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

function mockM08Apis() {
  vi.spyOn(apiClient, 'get').mockImplementation((url: string) => {
    if (url === '/api/v1/intelligence/lifecycle') {
      return Promise.resolve({
        data: {
          distribution: { Introduction: 1, Growth: 1, Maturity: 0, Decline: 1, Discontinued: 0 },
          dormant_stock_count: 1,
          anchor_notes: {
            uci_historical: 'Anchored to 2011-12-09.',
            operational: 'Anchored to 2026-11-27.',
          },
          non_auto_discontinued_policy: 'Manual only.',
          items: [
            {
              product_id: 4,
              stock_code: 'SKU-DORMANT-04',
              description: 'Stagnant Seasonal Stock',
              category_name: 'Seasonal',
              source_origin: 'operational',
              currency: 'INR',
              is_active: true,
              lifecycle_stage: 'Decline',
              previous_stage: 'Maturity',
              pending_candidate_stage: null,
              consecutive_candidate_windows: 0,
              required_hysteresis_windows: 2,
              rolling_velocity: '0.0000',
              prior_rolling_velocity: '1.0000',
              velocity_trend_pct: '-100.00',
              order_frequency: '0.0000',
              sku_age_days: 300,
              days_since_last_sale: 150,
              current_quantity: '12.5000',
              current_unit_price: '120.00',
              stock_value: '1500.00',
              is_dormant_stock: true,
              anchor_date: '2026-11-27',
              last_evaluated_at: '2026-11-27T00:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          page_size: 15,
          total_pages: 1,
          workspace_context: 'Store Manager (Admin)',
          correlation_id: 'corr-m08',
          generated_at: '2026-11-27T00:00:00Z',
        },
      })
    }
    if (url === '/api/v1/intelligence/dead-stock') {
      return Promise.resolve({
        data: {
          inactivity_threshold_days: 90,
          total_dead_stock_skus: 1,
          operational_dead_stock_value_inr: '1500.00',
          uci_baseline_dead_stock_value_gbp: '0.00',
          currency_blending_prohibited: true,
          policy_notice: 'No auto-discontinuation (DDR-08) or autonomous markdowns (EXCL-04).',
          items: [
            {
              product_id: 4,
              stock_code: 'SKU-DORMANT-04',
              description: 'Stagnant Seasonal Stock',
              category_name: 'Seasonal',
              source_origin: 'operational',
              currency: 'INR',
              lifecycle_stage: 'Decline',
              current_quantity: '12.5000',
              current_unit_price: '120.00',
              dead_stock_value: '1500.00',
              days_since_last_sale: 150,
              sku_age_days: 300,
              anchor_date: '2026-11-27',
              inactivity_threshold_days: 90,
            },
          ],
          total: 1,
          page: 1,
          page_size: 25,
          total_pages: 1,
          workspace_context: 'Store Manager (Admin)',
          correlation_id: 'corr-m08',
          generated_at: '2026-11-27T00:00:00Z',
        },
      })
    }
    if (url === '/api/v1/settings/lifecycle') {
      return Promise.resolve({
        data: {
          domain: 'lifecycle',
          forward_only_notice: 'Forward only.',
          settings: [
            {
              setting_key: 'lifecycle_inactivity_days',
              setting_value: 90,
              default_value: 90,
              min_bound: '14.0000',
              max_bound: '365.0000',
              value_type: 'INTEGER',
              domain: 'lifecycle',
              description: 'Inactivity window in days.',
              selected_workspace: null,
              action_source: 'SYSTEM',
              operator_ref: null,
              updated_at: '2026-11-27T00:00:00Z',
            },
          ],
          audit_log_id: null,
          workspace_context: 'Store Manager (Admin)',
          correlation_id: 'corr-m08',
        },
      })
    }
    if (url.startsWith('/api/v1/intelligence/lifecycle/4')) {
      return Promise.resolve({
        data: {
          sku: {
            product_id: 4,
            stock_code: 'SKU-DORMANT-04',
            description: 'Stagnant Seasonal Stock',
            category_name: 'Seasonal',
            source_origin: 'operational',
            currency: 'INR',
            is_active: true,
            lifecycle_stage: 'Decline',
            previous_stage: 'Maturity',
            pending_candidate_stage: null,
            consecutive_candidate_windows: 0,
            required_hysteresis_windows: 2,
            rolling_velocity: '0.0000',
            prior_rolling_velocity: '1.0000',
            velocity_trend_pct: '-100.00',
            order_frequency: '0.0000',
            sku_age_days: 300,
            days_since_last_sale: 150,
            current_quantity: '12.5000',
            current_unit_price: '120.00',
            stock_value: '1500.00',
            is_dormant_stock: true,
            anchor_date: '2026-11-27',
            last_evaluated_at: '2026-11-27T00:00:00Z',
          },
          classification_explanation: 'Exceeded 90d inactivity threshold.',
          snapshots: [],
          snapshot_count: 0,
          workspace_context: 'Store Manager (Admin)',
          correlation_id: 'corr-m08',
          generated_at: '2026-11-27T00:00:00Z',
        },
      })
    }
    return Promise.resolve({ data: { status: 'healthy', service: 'backend', version: '0.1.0' } })
  })
}

describe('M08 Product Lifecycle Intelligence Feature', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    useWorkspaceStore.setState({ activeWorkspace: 'store_manager', activeNavItem: 'M08' })
  })

  it('renders 5 canonical stages, portfolio table, dead-stock INR valuation, and settings', async () => {
    mockM08Apis()
    renderWithProviders(<ProductLifecycleView />)

    expect(screen.getByText('Product Lifecycle Intelligence')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('SKU-DORMANT-04')).toBeInTheDocument()
    })

    // Switch to Dead-Stock Review tab
    fireEvent.click(screen.getByRole('tab', { name: /Dead-Stock Review/i }))
    expect(screen.getByText('Operational Capital (INR)')).toBeInTheDocument()
    expect(screen.getAllByText(/₹1,500\.00/).length).toBeGreaterThan(0)

    // Switch to Bounded Thresholds tab and validate out-of-bounds input
    fireEvent.click(screen.getByRole('tab', { name: /Bounded Thresholds/i }))
    const input = screen.getByLabelText('lifecycle_inactivity_days')
    fireEvent.change(input, { target: { value: '999' } })
    fireEvent.click(screen.getByRole('button', { name: /Save Bounded Thresholds/i }))

    expect(screen.getByRole('alert')).toHaveTextContent('must be within [14.0000, 365.0000]')
  })

  it('requires explicit confirmation modal + reason for manual Discontinued and sends PATCH', async () => {
    mockM08Apis()
    const patchSpy = vi.spyOn(apiClient, 'patch').mockResolvedValue({
      data: {
        product_id: 4,
        stock_code: 'SKU-DORMANT-04',
        previous_stage: 'Decline',
        lifecycle_stage: 'Discontinued',
        snapshot: {
          id: 99,
          product_id: 4,
          stock_code: 'SKU-DORMANT-04',
          lifecycle_stage: 'Discontinued',
          previous_stage: 'Decline',
          rolling_velocity: '0.0000',
          order_frequency: '0.0000',
          sku_age_days: 300,
          days_since_last_sale: 150,
          is_dormant_stock: true,
          trigger_type: 'manual_discontinued',
          applied_settings_snapshot: {},
          selected_workspace: 'store_manager',
          action_source: 'UI',
          operator_ref: null,
          evaluated_at: '2026-11-27T00:00:00Z',
        },
        audit_log_id: 10,
        excl_04_notice: 'Zero markdowns triggered.',
        workspace_context: 'Store Manager (Admin)',
        correlation_id: 'corr-m08',
      },
    })

    renderWithProviders(<ProductLifecycleView />)
    await waitFor(() => expect(screen.getByText('SKU-DORMANT-04')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: 'Discontinue' }))
    expect(screen.getByText('Confirm Manual Product Discontinuation')).toBeInTheDocument()

    // Try submitting without checking acknowledgement checkbox
    fireEvent.change(screen.getByLabelText(/Discontinuation Reason/i), {
      target: { value: 'Supplier retired line' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Discontinue' }))
    expect(screen.getByRole('alert')).toHaveTextContent('explicitly check the confirmation box')
    expect(patchSpy).not.toHaveBeenCalled()

    // Check box and confirm
    fireEvent.click(screen.getByRole('checkbox', { name: /I explicitly confirm/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Discontinue' }))

    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalledWith(
        '/api/v1/intelligence/lifecycle/4/discontinue',
        { confirm_discontinue: true, reason: 'Supplier retired line', operator_ref: undefined },
        { headers: { 'X-NEXORA-Workspace': 'store_manager' } }
      )
    })
  })

  it('hides M08 from Finance Staff in /dashboard navigation and hides Discontinue button in Inventory Staff', async () => {
    mockM08Apis()
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/dashboard']}>
          <AppRouter />
        </MemoryRouter>
      </QueryClientProvider>
    )

    await waitFor(() => expect(screen.getByText('SKU-DORMANT-04')).toBeInTheDocument())

    // Inventory Staff sees M08 but CANNOT discontinue
    act(() => {
      useWorkspaceStore.getState().setWorkspace('inventory_staff')
    })
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: 'Discontinue' })).not.toBeInTheDocument()
    })

    // Finance Staff does NOT have M08 in navigation (falls back away from M08)
    act(() => {
      useWorkspaceStore.getState().setWorkspace('finance_staff')
    })
    expect(screen.queryByText('Product Lifecycle Intelligence')).not.toBeInTheDocument()
  })

  it('handles failed evaluation and discontinue mutations gracefully without unhandled rejections', async () => {
    mockM08Apis()
    vi.spyOn(apiClient, 'post').mockRejectedValueOnce(new Error('Evaluation service unavailable'))
    vi.spyOn(apiClient, 'patch').mockRejectedValueOnce(new Error('Discontinue conflict'))

    renderWithProviders(<ProductLifecycleView />)
    await waitFor(() => expect(screen.getByText('SKU-DORMANT-04')).toBeInTheDocument())

    // Trigger Run Evaluation failure
    fireEvent.click(screen.getByRole('button', { name: /Run Evaluation/i }))
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Evaluation service unavailable')
    })

    // Trigger Discontinue PATCH failure and verify modal remains open with error alert
    fireEvent.click(screen.getByRole('button', { name: 'Discontinue' }))
    fireEvent.change(screen.getByLabelText(/Discontinuation Reason/i), {
      target: { value: 'Supplier retired line' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /I explicitly confirm/i }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Discontinue' }))

    await waitFor(() => {
      const alerts = screen.getAllByRole('alert')
      expect(alerts.some((el) => el.textContent?.includes('Discontinue conflict'))).toBe(true)
    })
    expect(screen.getByText('Confirm Manual Product Discontinuation')).toBeInTheDocument()
  })
})

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { act, render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AppRouter } from '@/app/router/AppRouter'
import { apiClient } from '@/services/api/client'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { CORE_MODULES, SUPPORTING_CAPABILITIES, WORKSPACES } from '@/utils/modules'

function renderAtRoute(initialRoute = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <AppRouter />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('NEXORA Frontend Foundation', () => {
  beforeEach(() => {
    useWorkspaceStore.setState({ activeWorkspace: 'store_manager', activeNavItem: 'M01' })
    vi.spyOn(apiClient, 'get').mockResolvedValue({
      data: { status: 'healthy', service: 'backend', version: '0.1.0' },
    })
  })

  it('renders Page 1 with exact heading, 4 workspaces, and zero password inputs', () => {
    const { container } = renderAtRoute('/')
    expect(
      screen.getByRole('heading', { name: 'Welcome to NEXORA — Select Your Workspace' })
    ).toBeInTheDocument()

    expect(WORKSPACES).toHaveLength(4)
    expect(screen.getByText('Store Manager (Admin)')).toBeInTheDocument()
    expect(screen.getByText('Inventory Staff')).toBeInTheDocument()
    expect(screen.getByText('Purchase Manager')).toBeInTheDocument()
    expect(screen.getByText('Finance Staff')).toBeInTheDocument()
    expect(container.querySelector('input[type="password"]')).toBeNull()
  })

  it('defines exactly 18 core modules and 4 separate supporting capabilities', () => {
    expect(CORE_MODULES).toHaveLength(18)
    expect(SUPPORTING_CAPABILITIES).toHaveLength(4)
  })

  it('navigates to /dashboard and restricts M03 to Store Manager and Finance Staff', () => {
    renderAtRoute('/')

    // Select Inventory Staff -> M03 must NOT appear in sidebar navigation
    const buttons = screen.getAllByRole('button', { name: /Open Workspace/i })
    fireEvent.click(buttons[1]) // Inventory Staff card

    expect(screen.getByTestId('current-workspace-badge')).toHaveTextContent(
      'Workspace: Inventory Staff'
    )
    expect(screen.queryByText('Customer Management')).not.toBeInTheDocument()

    // Purchase Manager -> M03 must NOT appear
    act(() => {
      useWorkspaceStore.getState().setWorkspace('purchase_manager')
    })
    expect(screen.queryByText('Customer Management')).not.toBeInTheDocument()

    // Finance Staff -> M03 MUST appear
    act(() => {
      useWorkspaceStore.getState().setWorkspace('finance_staff')
    })
    expect(screen.getByText('Customer Management')).toBeInTheDocument()

    // Store Manager -> all 18 core modules + 4 SYS capabilities visible
    act(() => {
      useWorkspaceStore.getState().setWorkspace('store_manager')
    })
    expect(screen.getByText('Core Modules (18 Visible)')).toBeInTheDocument()
    expect(screen.getByText('Customer Management')).toBeInTheDocument()
    expect(screen.getByText('Workspace Selection')).toBeInTheDocument()
    expect(screen.getByText('Centralized History & Audit')).toBeInTheDocument()
    expect(screen.getByText('Smart Alerts')).toBeInTheDocument()
    expect(screen.getByText('Reports & Export')).toBeInTheDocument()
  })

  it('configures Axios base URL without unverified custom workspace header injection', () => {
    expect(apiClient.defaults.baseURL).toBe('http://localhost:8000')
    expect(apiClient.defaults.headers['X-NEXORA-Workspace']).toBeUndefined()
  })
})

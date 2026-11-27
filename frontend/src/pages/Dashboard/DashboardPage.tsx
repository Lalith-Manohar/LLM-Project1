import { DashboardLayout } from '@/app/layouts/DashboardLayout'
import { ModulePlaceholderView } from '@/components/dashboard/ModulePlaceholderView'
import { BusinessIntelligenceView } from '@/features/M06-BusinessIntelligence'
import { ProductLifecycleView } from '@/features/M08-ProductLifecycle'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'

/** Page 2 (/dashboard): Unified Retail Management Dashboard across all 4 workspaces. */
export function DashboardPage() {
  const activeNavItem = useWorkspaceStore((state) => state.activeNavItem)

  const renderActiveModule = () => {
    if (activeNavItem === 'M06') {
      return <BusinessIntelligenceView />
    }
    if (activeNavItem === 'M08') {
      return <ProductLifecycleView />
    }
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <ModulePlaceholderView />
      </div>
    )
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-7xl space-y-4">{renderActiveModule()}</div>
    </DashboardLayout>
  )
}

import { DashboardLayout } from '@/app/layouts/DashboardLayout'
import { ModulePlaceholderView } from '@/components/dashboard/ModulePlaceholderView'

/** Page 2 (/dashboard): Unified Retail Management Dashboard across all 4 workspaces. */
export function DashboardPage() {
  return (
    <DashboardLayout>
      <div className="mx-auto max-w-4xl space-y-4">
        <ModulePlaceholderView />
      </div>
    </DashboardLayout>
  )
}

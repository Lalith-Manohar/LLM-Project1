import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { SidebarNav } from '@/components/navigation/SidebarNav'
import { WorkspaceSwitcher } from '@/components/navigation/WorkspaceSwitcher'
import { BackendStatusBadge } from '@/components/shared/BackendStatusBadge'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { getWorkspaceById } from '@/utils/modules'

interface DashboardLayoutProps {
  children: ReactNode
}

/** Shared Page 2 shell: header, current workspace badge, switcher, sidebar, and main area. */
export function DashboardLayout({ children }: DashboardLayoutProps) {
  const activeWorkspace = useWorkspaceStore((state) => state.activeWorkspace)
  const currentWorkspace = getWorkspaceById(activeWorkspace)

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="sticky top-0 z-30 border-b bg-card">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 lg:px-6">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" asChild>
              <Link to="/" className="gap-1.5">
                <ArrowLeft className="h-4 w-4" />
                Workspaces
              </Link>
            </Button>
            <div className="h-5 w-px bg-border" />
            <div>
              <span className="font-bold tracking-tight">NEXORA</span>
              <span className="ml-2 text-xs text-muted-foreground hidden sm:inline">
                Unified Retail Management Dashboard
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" data-testid="current-workspace-badge">
              Workspace: {currentWorkspace.label}
            </Badge>
            <BackendStatusBadge />
            <WorkspaceSwitcher />
          </div>
        </div>
      </header>

      <div className="flex flex-1 flex-col lg:flex-row">
        <SidebarNav />
        <main className="flex-1 p-4 lg:p-6">{children}</main>
      </div>
    </div>
  )
}

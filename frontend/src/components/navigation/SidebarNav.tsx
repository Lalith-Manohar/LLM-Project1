import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { cn } from '@/utils/cn'
import {
  getVisibleCoreModules,
  getVisibleSupportingCapabilities,
} from '@/utils/modules'

/**
 * Unified sidebar scoping visible Core Modules (M01-M18) and
 * separate Supporting Capabilities (SYS-01..SYS-04) for the active workspace.
 */
export function SidebarNav() {
  const activeWorkspace = useWorkspaceStore((state) => state.activeWorkspace)
  const activeNavItem = useWorkspaceStore((state) => state.activeNavItem)
  const setActiveNavItem = useWorkspaceStore((state) => state.setActiveNavItem)

  const coreModules = getVisibleCoreModules(activeWorkspace)
  const supportingCapabilities = getVisibleSupportingCapabilities(activeWorkspace)

  return (
    <aside className="w-full shrink-0 border-b bg-card lg:w-72 lg:border-b-0 lg:border-r">
      <div className="p-4 space-y-6">
        <div>
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Core Modules ({coreModules.length} Visible)
          </p>
          <nav aria-label="Core modules" className="space-y-1">
            {coreModules.map((mod) => (
              <button
                key={mod.id}
                type="button"
                onClick={() => setActiveNavItem(mod.id)}
                className={cn(
                  'flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors',
                  activeNavItem === mod.id
                    ? 'bg-primary text-primary-foreground font-medium'
                    : 'text-foreground hover:bg-muted'
                )}
              >
                <span className="font-mono text-xs opacity-80">{mod.id}</span>
                <span className="truncate">{mod.name}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="border-t pt-4">
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Supporting Capabilities (SYS)
          </p>
          <nav aria-label="Supporting capabilities" className="space-y-1">
            {supportingCapabilities.map((cap) => (
              <button
                key={cap.id}
                type="button"
                onClick={() => setActiveNavItem(cap.id)}
                className={cn(
                  'flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-sm transition-colors',
                  activeNavItem === cap.id
                    ? 'bg-primary text-primary-foreground font-medium'
                    : 'text-foreground hover:bg-muted'
                )}
              >
                <span className="font-mono text-xs opacity-80">{cap.id}</span>
                <span className="truncate">{cap.name}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>
    </aside>
  )
}

import { create } from 'zustand'
import type { NavItemId, WorkspaceId } from '@/types/workspace'
import { getVisibleCoreModules, getVisibleSupportingCapabilities } from '@/utils/modules'

interface WorkspaceState {
  /** UI-only operational context. Never treated as login, user identity, or RBAC. */
  activeWorkspace: WorkspaceId
  activeNavItem: NavItemId
  setWorkspace: (workspace: WorkspaceId) => void
  setActiveNavItem: (itemId: NavItemId) => void
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  activeWorkspace: 'store_manager',
  activeNavItem: 'M01',

  setWorkspace: (workspace) => {
    const visibleCore = getVisibleCoreModules(workspace)
    const visibleSys = getVisibleSupportingCapabilities(workspace)
    const currentItem = get().activeNavItem

    const isStillVisible =
      visibleCore.some((m) => m.id === currentItem) ||
      visibleSys.some((s) => s.id === currentItem)

    set({
      activeWorkspace: workspace,
      // Fall back cleanly to the first visible module if the current tab is hidden in the new workspace.
      activeNavItem: isStillVisible ? currentItem : (visibleCore[0]?.id ?? 'SYS-01'),
    })
  },

  setActiveNavItem: (itemId) => set({ activeNavItem: itemId }),
}))

import { ChevronDown, Check, Layers } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { WORKSPACES, getWorkspaceById } from '@/utils/modules'

/**
 * In-header workspace context switcher (SYS-01).
 * Updates UI navigation focus only; does not perform login or security authorization.
 */
export function WorkspaceSwitcher() {
  const activeWorkspace = useWorkspaceStore((state) => state.activeWorkspace)
  const setWorkspace = useWorkspaceStore((state) => state.setWorkspace)
  const current = getWorkspaceById(activeWorkspace)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Layers className="h-4 w-4 text-primary" />
          <span>{current.label}</span>
          <ChevronDown className="h-3.5 w-3.5 opacity-70" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel>Switch Workspace (UI Context)</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {WORKSPACES.map((ws) => (
          <DropdownMenuItem
            key={ws.id}
            onClick={() => setWorkspace(ws.id)}
            className="flex items-center justify-between"
          >
            <span>{ws.label}</span>
            {ws.id === activeWorkspace && <Check className="h-4 w-4 text-primary" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

import { useNavigate } from 'react-router-dom'
import { ArrowRight, Building2, Package, ShoppingCart, Wallet } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BackendStatusBadge } from '@/components/shared/BackendStatusBadge'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import type { WorkspaceId } from '@/types/workspace'
import { WORKSPACES } from '@/utils/modules'

const WORKSPACE_ICONS: Record<WorkspaceId, typeof Building2> = {
  store_manager: Building2,
  inventory_staff: Package,
  purchase_manager: ShoppingCart,
  finance_staff: Wallet,
}

/** Page 1 (/): Stakeholder Workspace Selection without login or password prompts. */
export function WorkspaceSelectionPage() {
  const navigate = useNavigate()
  const setWorkspace = useWorkspaceStore((state) => state.setWorkspace)

  const handleSelectWorkspace = (workspaceId: WorkspaceId) => {
    setWorkspace(workspaceId)
    navigate('/dashboard')
  }

  return (
    <div className="min-h-screen bg-background px-4 py-10">
      <div className="mx-auto max-w-4xl space-y-8">
        <div className="flex flex-col items-center space-y-3 text-center">
          <BackendStatusBadge />
          <h1 className="text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
            Welcome to NEXORA — Select Your Workspace
          </h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Choose an operational workspace context to open the Unified Retail Management Dashboard.
            Workspace selection tailors UI navigation only and does not represent user authentication or RBAC.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {WORKSPACES.map((ws) => {
            const Icon = WORKSPACE_ICONS[ws.id]
            return (
              <Card key={ws.id} className="flex flex-col justify-between transition-shadow hover:shadow-md">
                <CardHeader>
                  <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <CardTitle className="text-lg">{ws.label}</CardTitle>
                  <CardDescription>{ws.shortDescription}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button
                    className="w-full justify-between"
                    onClick={() => handleSelectWorkspace(ws.id)}
                  >
                    Open Workspace
                    <ArrowRight className="h-4 w-4" />
                  </Button>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
    </div>
  )
}

import { Badge } from '@/components/ui/badge'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useWorkspaceStore } from '@/stores/useWorkspaceStore'
import { getNavItemDetails, getWorkspaceById } from '@/utils/modules'

/** Clean foundation placeholder view showing selected module scope without mock data. */
export function ModulePlaceholderView() {
  const activeWorkspace = useWorkspaceStore((state) => state.activeWorkspace)
  const activeNavItem = useWorkspaceStore((state) => state.activeNavItem)

  const workspace = getWorkspaceById(activeWorkspace)
  const details = getNavItemDetails(activeNavItem)

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono">
              {details.item.id}
            </Badge>
            <Badge variant="secondary">
              {details.kind === 'core' ? details.item.group : 'Group 6 — Supporting Capability'}
            </Badge>
          </div>
          <Badge variant="outline">Foundation Placeholder</Badge>
        </div>
        <CardTitle className="pt-2 text-2xl">{details.item.name}</CardTitle>
        <CardDescription>{details.item.description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        <p>
          Active Workspace Context: <strong className="text-foreground">{workspace.label}</strong>
        </p>
        <p>
          This module view is an intentional Phase 2/3 foundation placeholder. Feature workflows,
          validated forms, charts, and backend persistence for{' '}
          <span className="font-medium text-foreground">{details.item.id}</span> will be built in
          dedicated upcoming module tasks without fabricated placeholder figures.
        </p>
      </CardContent>
    </Card>
  )
}

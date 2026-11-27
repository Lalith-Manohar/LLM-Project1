import { Activity } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { useBackendHealth } from '@/hooks/useBackendHealth'

/** Displays live FastAPI /health connectivity without inventing mock status. */
export function BackendStatusBadge() {
  const { data, isLoading, isError } = useBackendHealth()

  if (isLoading) {
    return (
      <Badge variant="outline" className="gap-1.5 font-normal">
        <Activity className="h-3.5 w-3.5 animate-pulse text-amber-600" />
        Checking API...
      </Badge>
    )
  }

  if (isError || !data) {
    return (
      <Badge variant="outline" className="gap-1.5 border-red-200 bg-red-50 text-red-700 font-normal">
        <Activity className="h-3.5 w-3.5" />
        API Offline
      </Badge>
    )
  }

  return (
    <Badge variant="outline" className="gap-1.5 border-emerald-200 bg-emerald-50 text-emerald-700 font-normal">
      <Activity className="h-3.5 w-3.5" />
      API Online ({data.version})
    </Badge>
  )
}

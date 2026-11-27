import { useQuery } from '@tanstack/react-query'
import { fetchHealthStatus } from '@/services/api/healthApi'

/** Lightweight TanStack Query hook polling FastAPI liveness (GET /health). */
export function useBackendHealth() {
  return useQuery({
    queryKey: ['backend-health'],
    queryFn: fetchHealthStatus,
    retry: 1,
    refetchOnWindowFocus: false,
  })
}

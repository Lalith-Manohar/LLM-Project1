import { Navigate, Route, Routes } from 'react-router-dom'
import { WorkspaceSelectionPage } from '@/pages/WorkspaceSelection/WorkspaceSelectionPage'
import { DashboardPage } from '@/pages/Dashboard/DashboardPage'

/** Strictly two primary application pages: "/" (Workspace Selection) and "/dashboard" (Unified Dashboard). */
export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<WorkspaceSelectionPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

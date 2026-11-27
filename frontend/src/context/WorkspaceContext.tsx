import React, { createContext, useContext, useState } from 'react'
import {
  NEXORA_WORKSPACES,
  WorkspaceCode,
  WorkspaceDefinition,
  getWorkspaceDefinition
} from '../types/workspace'

const STORAGE_KEY = 'nexora_active_workspace'

interface WorkspaceContextValue {
  workspace: WorkspaceCode
  workspaceDef: WorkspaceDefinition
  setWorkspace: (next: WorkspaceCode) => void
  allWorkspaces: readonly WorkspaceDefinition[]
}

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined)

function loadInitialWorkspace(): WorkspaceCode {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY)
    if (
      saved === 'store_manager' ||
      saved === 'inventory_staff' ||
      saved === 'purchase_manager' ||
      saved === 'finance_staff'
    ) {
      return saved
    }
  } catch {
    // Ignore sessionStorage unavailability in restricted browser contexts
  }
  return 'store_manager'
}

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [workspace, setWorkspaceState] = useState<WorkspaceCode>(loadInitialWorkspace)

  const setWorkspace = (next: WorkspaceCode) => {
    setWorkspaceState(next)
    try {
      sessionStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Ignore storage failure
    }
  }

  return (
    <WorkspaceContext.Provider
      value={{
        workspace,
        workspaceDef: getWorkspaceDefinition(workspace),
        setWorkspace,
        allWorkspaces: NEXORA_WORKSPACES
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  )
}

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext)
  if (!ctx) {
    throw new Error('useWorkspace must be used inside WorkspaceProvider')
  }
  return ctx
}

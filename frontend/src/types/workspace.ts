/** Exact four stakeholder workspaces (UI navigation context only — not auth/RBAC). */
export type WorkspaceId =
  | 'store_manager'
  | 'inventory_staff'
  | 'purchase_manager'
  | 'finance_staff'

export interface WorkspaceDefinition {
  id: WorkspaceId
  label: string
  shortDescription: string
}

export type ModuleGroupName =
  | 'Group 1 — Retail Foundation'
  | 'Group 2 — Business Intelligence'
  | 'Group 3 — Inventory & Procurement'
  | 'Group 4 — AI & Predictive Intelligence'
  | 'Group 5 — Business Operations'

export type CoreModuleId =
  | 'M01' | 'M02' | 'M03' | 'M04' | 'M05'
  | 'M06' | 'M07' | 'M08'
  | 'M09' | 'M10' | 'M11'
  | 'M12' | 'M13' | 'M14' | 'M15'
  | 'M16' | 'M17' | 'M18'

export type SupportingCapabilityId = 'SYS-01' | 'SYS-02' | 'SYS-03' | 'SYS-04'

export type NavItemId = CoreModuleId | SupportingCapabilityId

export interface CoreModuleDefinition {
  id: CoreModuleId
  name: string
  group: ModuleGroupName
  description: string
  visibleIn: WorkspaceId[]
}

export interface SupportingCapabilityDefinition {
  id: SupportingCapabilityId
  name: string
  description: string
  visibleIn: WorkspaceId[]
}

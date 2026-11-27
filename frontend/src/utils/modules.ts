import type {
  CoreModuleDefinition,
  NavItemId,
  SupportingCapabilityDefinition,
  WorkspaceDefinition,
  WorkspaceId,
} from '@/types/workspace'

export const WORKSPACES: WorkspaceDefinition[] = [
  {
    id: 'store_manager',
    label: 'Store Manager (Admin)',
    shortDescription: 'Full operational visibility across all 18 core modules and governance capabilities.',
  },
  {
    id: 'inventory_staff',
    label: 'Inventory Staff',
    shortDescription: 'Warehouse stock balances, cycle counts, pick/pack dispatch, and return disposition.',
  },
  {
    id: 'purchase_manager',
    label: 'Purchase Manager',
    shortDescription: 'Supplier mappings, predictive replenishment risk, and Tier 1 Purchase Order workflow.',
  },
  {
    id: 'finance_staff',
    label: 'Finance Staff',
    shortDescription: 'Customer profiles, INR invoicing, manual payments, credit notes, refunds, and reconciliation.',
  },
]

/**
 * Exact 18 core NEXORA modules (Groups 1-5).
 * M03 Customer Management is restricted in UI navigation to Store Manager (Admin) and Finance Staff.
 */
export const CORE_MODULES: CoreModuleDefinition[] = [
  {
    id: 'M01',
    name: 'Product Management',
    group: 'Group 1 — Retail Foundation',
    description: 'Catalog SKUs, categories, INR pricing, and UoM conversions.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager', 'finance_staff'],
  },
  {
    id: 'M02',
    name: 'Supplier Management',
    group: 'Group 1 — Retail Foundation',
    description: 'Vendor directory, supplier-product mappings, and hierarchical lead times.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager'],
  },
  {
    id: 'M03',
    name: 'Customer Management',
    group: 'Group 1 — Retail Foundation',
    description: 'Manual customer directory, billing/shipping contacts, and soft status control.',
    visibleIn: ['store_manager', 'finance_staff'],
  },
  {
    id: 'M04',
    name: 'Sales Management',
    group: 'Group 1 — Retail Foundation',
    description: 'Operational and historical UCI realized sales streams and traceable reversals.',
    visibleIn: ['store_manager', 'finance_staff'],
  },
  {
    id: 'M05',
    name: 'Order Management',
    group: 'Group 1 — Retail Foundation',
    description: 'Draft orders, confirmation stock reservation, partial/full fulfilment, and cancellation.',
    visibleIn: ['store_manager', 'inventory_staff', 'finance_staff'],
  },
  {
    id: 'M06',
    name: 'Business Intelligence',
    group: 'Group 2 — Business Intelligence',
    description: 'Sales trends, country splits, and SKU leaderboards separating GBP vs INR.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager', 'finance_staff'],
  },
  {
    id: 'M07',
    name: 'Seasonal Demand Calendar',
    group: 'Group 2 — Business Intelligence',
    description: 'Monthly and day-of-week clean demand intensity calendars.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager'],
  },
  {
    id: 'M08',
    name: 'Product Lifecycle Intelligence',
    group: 'Group 2 — Business Intelligence',
    description: 'Introduction-to-Discontinued stage tracking with hysteresis and manual retirement.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager'],
  },
  {
    id: 'M09',
    name: 'Inventory Control',
    group: 'Group 3 — Inventory & Procurement',
    description: 'Five separate stock metrics (Physical, Reserved, Available, Incoming, Projected) and adjustments.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager'],
  },
  {
    id: 'M10',
    name: 'Stock Movement Tracking',
    group: 'Group 3 — Inventory & Procurement',
    description: 'Read-only immutable ledger of physical inventory movements.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager', 'finance_staff'],
  },
  {
    id: 'M11',
    name: 'Purchase Planning Simulator',
    group: 'Group 3 — Inventory & Procurement',
    description: 'Stateless replenishment simulation, draft POs, dual-control approval, and goods receipt.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager'],
  },
  {
    id: 'M12',
    name: 'Demand Forecasting',
    group: 'Group 4 — AI & Predictive Intelligence',
    description: '7/15/30/90-day multi-horizon ML inference and planned B2B operational demand pipelines.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager', 'finance_staff'],
  },
  {
    id: 'M13',
    name: 'Price & Revenue Intelligence',
    group: 'Group 4 — AI & Predictive Intelligence',
    description: 'Read-only observational price distribution and revenue contribution analytics.',
    visibleIn: ['store_manager', 'purchase_manager', 'finance_staff'],
  },
  {
    id: 'M14',
    name: 'Predictive Planner',
    group: 'Group 4 — AI & Predictive Intelligence',
    description: 'Supplier lead-time demand risk classification (CRITICAL/ELEVATED/SAFE/UNAVAILABLE).',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager'],
  },
  {
    id: 'M15',
    name: 'Anomaly Detection',
    group: 'Group 4 — AI & Predictive Intelligence',
    description: 'Hybrid statistical and deterministic alerts across demand, returns, stock, and POs.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager', 'finance_staff'],
  },
  {
    id: 'M16',
    name: 'Return Intelligence',
    group: 'Group 5 — Business Operations',
    description: 'Customer return intake (excess_stock vs defective/damaged) and over-return capping.',
    visibleIn: ['store_manager', 'inventory_staff', 'finance_staff'],
  },
  {
    id: 'M17',
    name: 'Billing & Finance',
    group: 'Group 5 — Business Operations',
    description: 'Immutable INR invoices, centralized tax snapshots, manual payments, credit notes, and refunds.',
    visibleIn: ['store_manager', 'finance_staff'],
  },
  {
    id: 'M18',
    name: 'Shipping & Delivery',
    group: 'Group 5 — Business Operations',
    description: 'Internal warehouse pick lists, split shipments, packing slips, and routing labels.',
    visibleIn: ['store_manager', 'inventory_staff', 'finance_staff'],
  },
]

/** Exact 4 supporting capabilities kept strictly separate from the 18 core modules. */
export const SUPPORTING_CAPABILITIES: SupportingCapabilityDefinition[] = [
  {
    id: 'SYS-01',
    name: 'Workspace Selection',
    description: 'UI operational context switcher (not authentication, login, or server RBAC).',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager', 'finance_staff'],
  },
  {
    id: 'SYS-02',
    name: 'Centralized History & Audit',
    description: 'Cross-module immutable audit timeline and Tier 2 outbox diagnostics.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager', 'finance_staff'],
  },
  {
    id: 'SYS-03',
    name: 'Smart Alerts',
    description: 'Actionable deduplicated operational notifications across modules.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager', 'finance_staff'],
  },
  {
    id: 'SYS-04',
    name: 'Reports & Export',
    description: 'Paginated data previews, printable views, and formula-safe CSV/JSON exports.',
    visibleIn: ['store_manager', 'inventory_staff', 'purchase_manager', 'finance_staff'],
  },
]

export function getWorkspaceById(id: WorkspaceId): WorkspaceDefinition {
  return WORKSPACES.find((w) => w.id === id) ?? WORKSPACES[0]
}

export function getVisibleCoreModules(workspace: WorkspaceId): CoreModuleDefinition[] {
  return CORE_MODULES.filter((mod) => mod.visibleIn.includes(workspace))
}

export function getVisibleSupportingCapabilities(workspace: WorkspaceId): SupportingCapabilityDefinition[] {
  return SUPPORTING_CAPABILITIES.filter((cap) => cap.visibleIn.includes(workspace))
}

export function getNavItemDetails(itemId: NavItemId) {
  const core = CORE_MODULES.find((m) => m.id === itemId)
  if (core) return { kind: 'core' as const, item: core }
  const sys = SUPPORTING_CAPABILITIES.find((s) => s.id === itemId)
  return sys ? { kind: 'supporting' as const, item: sys } : { kind: 'core' as const, item: CORE_MODULES[0] }
}

# M02 — Supplier Management

- **Module ID & Official Name:** `M02` — Supplier Management
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 1 (Retail Foundation)

## Purpose
Manage vendor directory profiles, `supplier_products` mappings (`DDR-07`), and hierarchical supplier lead times (`DDR-01`).

## Main Responsibilities & Boundaries
- Maintain supplier contact details, active/preferred status, and supplier-product terms.
- Provide verified product-level and supplier-level lead times without inventing missing lead times (`DDR-01`).
- Does **not** draft Purchase Orders (`M11`) or automatically dispatch orders to suppliers (`EXCL-03`).

## Related Modules & Dependencies
- **Depends on:** `M01` (Product Management).
- **Consumed by:** `M11` (Purchase Planning Simulator) and `M14` (Predictive Planner) for lead-time resolution.

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Hidden

## Known Backend / API Integration Status
- Operational supplier and `supplier_products` CRUD endpoints are **PLANNED** (not yet implemented on `main`).

# M01 — Product Management

- **Module ID & Official Name:** `M01` — Product Management
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 1 (Retail Foundation)

## Purpose
Provide the central catalog UI for managing NEXORA SKUs, categories, `INR` unit prices, unit-of-measure (UoM) conversions, and soft product activation.

## Main Responsibilities & Boundaries
- Manage product catalog metadata, base UoM, and commercial-to-base UoM conversions (`DDR-06`).
- Enforce soft activation/deactivation rather than destructive deletion of referenced SKUs.
- Does **not** own live warehouse stock balances (`M09`) or supplier pricing/lead-time mappings (`M02`).

## Related Modules & Dependencies
- **Foundational dependency for:** `M02` (supplier-product mappings), `M04`/`M05` (sales & orders), `M09`/`M10` (inventory & movements), `M11` (purchase planning), `M12` (demand forecasting), and `M16`/`M17`/`M18` (returns, billing, shipping).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Visible

## Known Backend / API Integration Status
- Operational catalog and UoM CRUD endpoints are **PLANNED** (`0` live MySQL tables or `/api/v1/products` routes on `main`).

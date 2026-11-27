# M16 — Return Intelligence

- **Module ID & Official Name:** `M16` — Return Intelligence
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 4 (Business Operations)

## Purpose
Manage customer return intake, disposition (`excess_stock` vs. `defective`/`damaged`), over-return capping, and net product health metrics.

## Main Responsibilities & Boundaries
- Separate restockable `excess_stock` returns from `defective`/`damaged` returns so defective goods never distort demand reductions (`DDR-06`) or restockable inventory.
- Enforce over-return quantity caps against fulfilled quantities.
- Coordinate refund/credit workflows with `M17` (Billing & Finance).

## Related Modules & Dependencies
- **Depends on:** `M04` (Sales Management), `M05` (Order Management), and `M01` (Product Management).
- **Integrates with:** `M09`/`M10` (restockable movements) and `M17` (credit notes & refunds).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Finance Staff`: Visible
- `Purchase Manager`: Hidden

## Known Backend / API Integration Status
- Return intake, approval, and disposition endpoints are **PLANNED** (not yet implemented on `main`).

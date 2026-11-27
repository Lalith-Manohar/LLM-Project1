# M04 — Sales Management

- **Module ID & Official Name:** `M04` — Sales Management
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 1 (Retail Foundation)

## Purpose
Display and manage realized operational sales (`transactions`) separately from historical UCI sales streams, along with traceable reversals.

## Main Responsibilities & Boundaries
- Keep historical `GBP` UCI records strictly separated from live `INR` operational realized sales.
- Preserve the approved distinction between **Orders (`M05`)** and **Realized Sales (`M04`)** (`DDR-05`).
- Support traceable compensating reversals without mutating historical records.

## Related Modules & Dependencies
- **Depends on:** `M01` (Product Management), `M03` (Customer Management), and `M05` (Order Management).
- **Connected to:** `M17` (Billing & Finance) and `M16` (Return Intelligence).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Finance Staff`: Visible
- `Inventory Staff`: Hidden
- `Purchase Manager`: Hidden

## Known Backend / API Integration Status
- Operational sales/transaction endpoints are **PLANNED** (not yet implemented on `main`).

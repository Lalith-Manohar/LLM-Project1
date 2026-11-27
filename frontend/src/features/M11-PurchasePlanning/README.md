# M11 — Purchase Planning Simulator

- **Module ID & Official Name:** `M11` — Purchase Planning Simulator
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 3 (Inventory & Procurement)

## Purpose
Support stateless replenishment what-if simulations, Purchase Order (PO) drafting, tiered dual-control approvals (`DDR-09`), and partial/full goods receipts.

## Main Responsibilities & Boundaries
- Keep stateless simulations distinct from persisted `draft`, `submitted`, `approved`, and `received` POs.
- Enforce mandatory human approval (`EXCL-03`, `DDR-09`); zero automatic supplier email/API dispatch.
- Post-approval edits invalidate prior approval; only `approved`/`partially_received` POs contribute to `Incoming Stock` (`DDR-02`).

## Related Modules & Dependencies
- **Depends on:** `M01` (Product Management), `M02` (Supplier Management), `M09` (Inventory Control), `M12` (Demand Forecasting), and `M14` (Predictive Planner).
- **Updates:** `M09`/`M10` on goods receipt.

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Hidden

## Known Backend / API Integration Status
- Purchase simulation and PO workflow endpoints are **PLANNED** (not yet implemented on `main`).

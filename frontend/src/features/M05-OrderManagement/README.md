# M05 — Order Management

- **Module ID & Official Name:** `M05` — Order Management
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 1 (Retail Foundation)

## Purpose
Manage customer orders from draft creation through confirmation (reserving available stock), partial/full fulfilment (`DDR-05`), and cancellation.

## Main Responsibilities & Boundaries
- Support order drafting, confirmation (which reserves `Available Stock`), partial/full fulfilment batches, and controlled cancellation.
- Keep **Orders (`M05`)** distinct from **Realized Sales (`M04`)** and **Shipments (`M18`)**.
- Deduct physical inventory only on actual fulfilment, never on draft creation.

## Related Modules & Dependencies
- **Depends on:** `M01` (Product Management) and `M03` (Customer Management).
- **Integrates with:** `M09` (Inventory Control), `M04` (Sales Management), `M16` (Return Intelligence), `M17` (Billing & Finance), and `M18` (Shipping & Delivery).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Finance Staff`: Visible
- `Purchase Manager`: Hidden

## Known Backend / API Integration Status
- Operational order and fulfilment endpoints are **PLANNED** (not yet implemented on `main`).

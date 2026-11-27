# M10 — Stock Movement Tracking

- **Module ID & Official Name:** `M10` — Stock Movement Tracking
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 3 (Inventory & Procurement)

## Purpose
Provide a read-only, immutable audit ledger of all physical inventory delta movements (`inventory_movements`).

## Main Responsibilities & Boundaries
- Display physical stock movements (receipts, fulfilments, fulfilment reversals, excess-stock returns, approved adjustments) with timestamps and references.
- Must **not** mutate ledger rows or duplicate live inventory ownership (`M09`).

## Related Modules & Dependencies
- **Records movements from:** `M05` (Order Management), `M09` (Inventory Control), `M11` (Purchase Planning Simulator), and `M16` (Return Intelligence).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Visible

## Known Backend / API Integration Status
- Stock movement ledger query endpoints are **PLANNED** (not yet implemented on `main`).

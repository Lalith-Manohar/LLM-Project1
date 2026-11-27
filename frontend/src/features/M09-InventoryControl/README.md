# M09 — Inventory Control

- **Module ID & Official Name:** `M09` — Inventory Control
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 3 (Inventory & Procurement)

## Purpose
Manage live warehouse stock balances across the five required NEXORA metrics (`DDR-03`), safety thresholds, and locked manual adjustments.

## Main Responsibilities & Boundaries
- Always display **Physical**, **Reserved**, **Available**, **Incoming** (approved POs only), and **Projected Available** stock separately (`DDR-03`).
- Never treat incoming PO units as physically available before receipt (`DDR-02`).
- Owns live inventory state; does **not** duplicate immutable ledger history (`M10`).

## Related Modules & Dependencies
- **Depends on:** `M01` (Product Management).
- **Integrates with:** `M05` (Order Management), `M10` (Stock Movement Tracking), `M11` (Purchase Planning Simulator), `M14` (Predictive Planner), and `M16` (Return Intelligence).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Hidden

## Known Backend / API Integration Status
- Live MySQL inventory endpoints are **PLANNED** (not yet implemented on `main`).

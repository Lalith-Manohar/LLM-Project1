# M14 — Predictive Planner

- **Module ID & Official Name:** `M14` — Predictive Planner
- **Implementation Status:** `Not Implemented` *(new React module view not yet implemented)*
- **Provisional Developer Ownership:** Developer 2 (Business Intelligence & Predictive)

## Purpose
Classify SKU stockout risk (`CRITICAL`, `ELEVATED`, `SAFE`, `UNAVAILABLE`) and compute deterministic replenishment recommendations using forecast demand, live stock, and verified supplier lead times (`DDR-01`–`DDR-03`, `DDR-07`).

## Main Responsibilities & Boundaries
- **Distinct from `M12`:** `M14` consumes forecast demand from `M12` and combines it with `M09` stock metrics and `M02` supplier lead times to assess **replenishment risk**. It does **not** train or serve raw ML demand models (`M12`).
- Must display supplier lead-time-based risk explicitly as `UNAVAILABLE` when no verified supplier lead time exists (`DDR-01`, never invent missing lead times).

## Related Modules & Dependencies
- **Depends on:** `M12` (Demand Forecasting), `M09` (Inventory Control), and `M02` (Supplier Management).
- **Feeds:** `M11` (Purchase Planning Simulator).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Hidden

## Known Backend / API Integration Status
- **Partially Implemented Prototype on `main`:** Stateless `POST /api/v1/inventory/recommend` exists as a Phase 1 prototype accepting caller-supplied stock/lead-time parameters.
- **PLANNED:** Full MySQL-backed live stock + hierarchical `supplier_products` / `suppliers` lead-time planning (`DDR-01`–`DDR-03`, `DDR-07`).

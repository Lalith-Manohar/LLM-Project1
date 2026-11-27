# M08 — Product Lifecycle Intelligence

- **Module ID & Official Name:** `M08` — Product Lifecycle Intelligence
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 2 (Business Intelligence & Predictive)

## Purpose
Track product lifecycle stages (`Introduction` through `Discontinued`) with hysteresis and manual retirement governance (`DDR-08`).

## Main Responsibilities & Boundaries
- Surface lifecycle stage classifications, dormant/dead-stock review queues, and transition alerts.
- Enforce that `Discontinued` status is **never assigned automatically** and requires an explicit Store Manager action (`DDR-08`).

## Related Modules & Dependencies
- **Depends on:** `M01` (Product Management) and clean sales/demand history (`M04`/`M06`).
- **Emits alerts to:** `SYS-03` (Smart Alerts).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Hidden

## Known Backend / API Integration Status
- Lifecycle classification and transition endpoints are **PLANNED** (not yet implemented on `main`).

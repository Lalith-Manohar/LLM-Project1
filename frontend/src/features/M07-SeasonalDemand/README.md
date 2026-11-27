# M07 — Seasonal Demand Calendar

- **Module ID & Official Name:** `M07` — Seasonal Demand Calendar
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 2 (Business Intelligence & Predictive)

## Purpose
Visualize monthly and day-of-week clean demand intensity calendars to highlight recurring seasonal patterns.

## Main Responsibilities & Boundaries
- Present clean positive-demand calendar heatmaps and day-of-week/monthly concentration views.
- Does **not** generate ML horizon forecasts (`M12`) or replenishment orders (`M11`).

## Related Modules & Dependencies
- **Complements:** `M06` (Business Intelligence) and `M12` (Demand Forecasting).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Hidden

## Known Backend / API Integration Status
- Seasonal demand calendar API endpoints are **PLANNED** (not yet implemented on `main`).

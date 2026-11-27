# M06 — Business Intelligence

- **Module ID & Official Name:** `M06` — Business Intelligence
- **Implementation Status:** `Not Implemented`
- **Provisional Developer Ownership:** Developer 2 (Business Intelligence & Predictive)

## Purpose
Provide executive and operational analytics views: time-series sales trends, country breakdowns, and SKU rankings.

## Main Responsibilities & Boundaries
- Render analytical charts and rankings while strictly separating historical `GBP` UCI analytics from live `INR` operational sales.
- Remain read-only analytics; does **not** perform automated price cuts (`EXCL-04`) or forecast inference (`M12`).

## Related Modules & Dependencies
- **Draws from:** `M01` (Product Management), `M04` (Sales Management), and UCI historical sales data.
- **Complements:** `M07` (Seasonal Demand Calendar) and `M13` (Price & Revenue Intelligence).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Visible

## Known Backend / API Integration Status
- Dedicated BI aggregation endpoints are **PLANNED** (not yet implemented on `main`).

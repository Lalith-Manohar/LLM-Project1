# M06 — Business Intelligence

- **Module ID & Official Name:** `M06` — Business Intelligence
- **Implementation Status:** `Migrated to Main Feature Architecture` (UCI GBP CSV + injectable operational INR repository; awaiting Phase 2 MySQL `transactions`/`transaction_items` & Phase 5 `SYS-04` `/api/v1/reports/export`)
- **Provisional Developer Ownership:** Developer 2 (Business Intelligence & Predictive)

## Purpose
Provide read-only executive and operational analytics views: executive KPIs, time-series sales trends, geographical country breakdowns, MoM/QoQ/YoY comparisons, and top/slow-moving SKU velocity leaderboards while strictly separating historical `GBP` UCI records from live `INR` operational sales.

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Visible

## Implemented Backend Endpoints
- `GET /api/v1/analytics/summary`
- `GET /api/v1/analytics/timeseries`
- `GET /api/v1/analytics/countries`
- `GET /api/v1/analytics/sku-rankings`
- `GET /api/v1/analytics/comparisons`

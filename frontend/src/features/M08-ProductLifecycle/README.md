# M08 — Product Lifecycle Intelligence

- **Module ID & Official Name:** `M08` — Product Lifecycle Intelligence
- **Implementation Status:** `Migrated to Main Feature Architecture` (UCI GBP + operational adapter; awaiting Phase 2 MySQL `product_lifecycle_snapshots` & `operational_settings` persistence)
- **Provisional Developer Ownership:** Developer 2 (Business Intelligence & Predictive)

## Purpose
Track product lifecycle stages (`Introduction`, `Growth`, `Maturity`, `Decline`, `Discontinued`) with anti-flicker hysteresis, dead-stock valuation, bounded `operational_settings` administration, and explicit manual discontinuation governance (`DDR-08`, `DDR-10`).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible (full lifecycle evaluation, bounded settings/reset, and manual Discontinued approval)
- `Inventory Staff`: Visible (dormant/dead-stock & Decline inspection)
- `Purchase Manager`: Visible (pre-PO lifecycle check)
- `Finance Staff`: Hidden

## Implemented Backend Endpoints
- `GET /api/v1/intelligence/lifecycle`
- `GET /api/v1/intelligence/lifecycle/{product_id}`
- `GET /api/v1/intelligence/lifecycle/{product_id}/history`
- `POST /api/v1/intelligence/lifecycle/evaluate`
- `GET /api/v1/intelligence/dead-stock`
- `PATCH /api/v1/intelligence/lifecycle/{product_id}/discontinue`
- `GET /api/v1/settings/lifecycle`
- `PUT /api/v1/settings/lifecycle`
- `POST /api/v1/settings/lifecycle/reset`

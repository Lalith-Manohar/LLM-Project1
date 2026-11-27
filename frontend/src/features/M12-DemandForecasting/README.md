# M12 — Demand Forecasting

- **Module ID & Official Name:** `M12` — Demand Forecasting
- **Implementation Status:** `Not Implemented` *(new React module view not yet implemented)*
- **Provisional Developer Ownership:** Developer 2 (Business Intelligence & Predictive)

## Purpose
Provide multi-horizon ML demand forecasting (`7`, `15`, `30`, `90` days) from pre-trained models and future operational B2B demand pipelines (`DDR-06`).

## Main Responsibilities & Boundaries
- **Distinct from `M14`:** `M12` generates and displays **demand forecasts** (predicted unit demand over `7/15/30/90` days, non-negative $\hat{y} \ge 0$, plus model metrics/info). It does **not** calculate supplier lead-time stockout risk or replenishment quantities (`M14`).
- Never trigger ML retraining inside HTTP requests.

## Related Modules & Dependencies
- **Depends on:** `M01` (Product Management) and historical/operational demand streams.
- **Feeds:** `M14` (Predictive Planner) and `M11` (Purchase Planning Simulator).

## Workspace Visibility (`modules.ts`)
- `Store Manager (Admin)`: Visible
- `Inventory Staff`: Visible
- `Purchase Manager`: Visible
- `Finance Staff`: Visible

## Known Backend / API Integration Status
- **Implemented on `main` (UCI Historical Baseline):** `GET /api/v1/forecast/horizons`, `GET /api/v1/forecast/model-metrics`, `GET /api/v1/forecast/model-info`, `POST /api/v1/forecast/`, `POST /api/v1/forecast/predict` (plus isolated experimental routes under `/api/v1/experimental/*`).
- **PLANNED:** Operational MySQL B2B demand (`DDR-06`), `forecasts`/`model_runs` persistence, and scheduled retraining.

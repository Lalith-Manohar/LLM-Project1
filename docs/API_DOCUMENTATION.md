# NEXORA — API Documentation

- **Project:** NEXORA – AI-Powered Retail Management & Intelligence System
- **Document Version:** 2.0 — Blueprint v2.2 & Database Schema v2.8 Consolidated API Reference
- **Last Updated:** 26 November 2026
- **Repository Baseline:** `Lalith-Manohar/LLM-Project1` (Branch `main`, aligned against commit `e74ae8970195a3609c8701799137154aa3f35d30`)
- **Authoritative Sources:**
  - Live Source Code & Tests: [`backend/app/main.py`](../backend/app/main.py), [`backend/app/api/routes/`](../backend/app/api/routes/__init__.py), [`backend/app/schemas/`](../backend/app/schemas/forecast.py), [`backend/tests/`](../backend/tests/test_forecast_api.py)
  - Master Architecture: [`docs/NEXORA — Technical Blueprint v1.0.md`](NEXORA%20%E2%80%94%20Technical%20Blueprint%20v1.0.md) *(Version 2.2)*
  - Feature Status Registry: [`docs/FEATURES_STATUS.md`](FEATURES_STATUS.md) *(Version 2.3)*
  - Operational Workflows: [`docs/NEXORA — Application Functionality & System Workflow Guide.md`](NEXORA%20%E2%80%94%20Application%20Functionality%20%26%20System%20Workflow%20Guide.md) *(Version 1.0)*
  - Target Relational Schema: [`docs/DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) *(Version 2.8)*

> [!IMPORTANT]
> **Reality vs. Planned Architecture:** Only **health/readiness probes**, **production demand forecasting routes**, **Task 12 experimental/comparative forecasting routes**, and a **stateless Phase 1 inventory recommendation prototype** are implemented on `main` today (`20` route handlers total, `17` visible in `/openapi.json`). **Zero live MySQL tables, zero SQLAlchemy ORM models, zero Alembic migrations, and zero operational CRUD endpoints exist yet on `main`.** All Section 7 operational modules (`M01`–`M18`, `SYS-01`–`SYS-04`) are **PLANNED** only.

---

## Table of Contents

1. [Section 1 — API Overview and Architecture](#section-1--api-overview-and-architecture)
2. [Section 2 — Implementation Status and API Classification](#section-2--implementation-status-and-api-classification)
3. [Section 3 — Currently Implemented General Endpoints](#section-3--currently-implemented-general-endpoints)
4. [Section 4 — Production Forecasting API](#section-4--production-forecasting-api)
5. [Section 5 — Experimental Forecasting API](#section-5--experimental-forecasting-api)
6. [Section 6 — Inventory Recommendation API](#section-6--inventory-recommendation-api)
7. [Section 7 — Planned Operational API Architecture](#section-7--planned-operational-api-architecture)
   - [7.1 Procurement and Approval APIs](#71-procurement-and-approval-apis)
   - [7.2 Order, Fulfilment and Shipping APIs](#72-order-fulfilment-and-shipping-apis)
   - [7.3 Finance APIs](#73-finance-apis)
   - [7.4 Audit and Alerts APIs](#74-audit-and-alerts-apis)
   - [7.5 UoM API Planning](#75-uom-api-planning)
8. [Section 8 — Request and Response Conventions](#section-8--request-and-response-conventions)
9. [Section 9 — HTTP Status Codes and Error Handling](#section-9--http-status-codes-and-error-handling)
10. [Section 10 — API Testing and Demonstration](#section-10--api-testing-and-demonstration)
11. [Section 11 — Implementation Roadmap and Limitations](#section-11--implementation-roadmap-and-limitations)
12. [Section 12 — API Change and Version History](#section-12--api-change-and-version-history)

---

## Section 1 — API Overview and Architecture

### 1.1 Verified Backend Stack & Runtime Versions

| Component | Declared Minimum ([`backend/requirements.txt`](../backend/requirements.txt)) | Verified Runtime (`backend/.venv`) | Role in System |
| :--- | :--- | :--- | :--- |
| **Python** | `>= 3.10` | `3.11.9` | Backend API runtime and ML execution |
| **FastAPI** | `fastapi>=0.110.0` | `0.163.1` | REST framework, router composition, OpenAPI generation |
| **Pydantic / Settings** | `pydantic>=2.6.0`, `pydantic-settings>=2.2.0` | `2.14.3` | Request/response validation and environment configuration |
| **Scikit-learn / Joblib** | `scikit-learn>=1.4.0`, `joblib>=1.3.0` | `1.9.1` (sklearn) | Read-only pre-trained estimator loading into RAM |
| **Pandas / NumPy** | `pandas>=2.2.0`, `numpy>=1.26.0` | Installed in `.venv` | Historical demand lookup and PIT feature construction |
| **SQLAlchemy / PyMySQL** | `sqlalchemy>=2.0.0`, `pymysql>=1.1.0` | Installed as target dependencies | Planned Phase 2 persistence (not yet active in code) |

### 1.2 Interactive API Documentation & Routing Topology

- **ASGI Application Entrypoint:** [`backend/app/main.py`](../backend/app/main.py) (`FastAPI` app version `"0.1.0"`, title `"NEXORA Retail Management & Intelligence System"`).
- **Base API Prefix:** `/api/v1` (`settings.API_V1_STR` in [`backend/app/core/config.py`](../backend/app/core/config.py)), aggregated in [`backend/app/api/routes/__init__.py`](../backend/app/api/routes/__init__.py):
  - `forecast.router` mounted at `/api/v1/forecast`
  - `experimental_forecast.router` mounted at `/api/v1/experimental`
  - `inventory.router` mounted at `/api/v1/inventory`
- **Interactive OpenAPI Documentation:**
  - Swagger UI: `/docs`
  - ReDoc: `/redoc`
  - OpenAPI 3.x JSON Schema: `/openapi.json`
- **Configured CORS Origins (`backend/app/main.py`):** `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:8000`, `http://127.0.0.1:8000`.
- **Current Frontend Integration State:** [`frontend/src/App.tsx`](../frontend/src/App.tsx) and [`frontend/src/services/api.ts`](../frontend/src/services/api.ts) currently implement only a single-screen Phase 1 demonstration client calling `GET /health` and `POST /api/v1/forecast/` using a narrower [`frontend/src/types/forecast.ts`](../frontend/src/types/forecast.ts) contract. The planned two-page Tailwind + Chart.js dashboard is not yet implemented.

### 1.3 Current Implementation Architecture vs. Planned Operational Persistence

At application startup (`lifespan` context manager in [`backend/app/main.py`](../backend/app/main.py)), the backend initializes in-memory inference artifacts read-only:

1. **`prediction_service` ([`backend/app/services/prediction_service.py`](../backend/app/services/prediction_service.py)):** Loads four serialized production `.joblib` models (`D_7`, `D_15`, `D_30`, `D_90`) and `models_metadata.json` from `backend/ml/models/`.
2. **`historical_data_service` ([`backend/app/services/historical_data_service.py`](../backend/app/services/historical_data_service.py)):** Loads `backend/ml/data/processed/daily_product_demand.csv` (`4,905` SKUs, `2,287,495` daily records from `2009-12-01` to `2011-12-09`) and initializes `PITPriceService` (`backend/ml/data/processed/pit_sku_price_history.json`, derived from `clean_gross_sales.csv`, covering `4,905` SKUs across `1,037,089` transactions and `604` trading dates).
3. **`experimental_prediction_service` ([`backend/app/services/experimental_prediction_service.py`](../backend/app/services/experimental_prediction_service.py)):** Independently loads four Task 12 experimental `.joblib` models (`D_7`, `D_15`, `D_30`, `D_90`) and metadata from `backend/ml/models_task12/`. Failure here never blocks production readiness or production inference.
4. **`store_wide_service` ([`backend/app/services/store_wide_service.py`](../backend/app/services/store_wide_service.py)):** Reads experimental comparative evaluation and store-wide macro forecast JSON artifacts from `backend/ml/models_experimental/` on demand.

> [!WARNING]
> **Explicit Database Status on `main`:**
> - **Zero live MySQL tables** are created or queried by the backend today.
> - **Zero SQLAlchemy ORM model classes** exist under `backend/app/`.
> - **Zero Alembic migration scripts** exist under `backend/`.
> - `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` in [`backend/app/core/config.py`](../backend/app/core/config.py) are unconsumed configuration placeholders only.
> - All currently implemented APIs are **stateless** or **CSV / JSON / Joblib-backed**. Never treat the planned **41-table MySQL schema** in [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.8 as operational on `main`.

### 1.4 Approved Two-Page Architecture, Four Workspaces & Non-Authentication Boundary

Under Blueprint v2.2 (`Sections 3, 13, 14, 15`), NEXORA's target system design is strictly scoped as follows:

- **Two Primary Pages Only:** Page 1 (`/` — *"Welcome to NEXORA — Select Your Workspace"*) and Page 2 (`/dashboard` — *Unified Retail Management Dashboard*).
- **Four Stakeholder Workspaces (UI Operational Contexts Only):**
  1. `Store Manager (Admin)`
  2. `Inventory Staff`
  3. `Purchase Manager`
  4. `Finance Staff`
- **No Authentication or Server-Side RBAC:** NEXORA explicitly omits login, registration, password storage (`Passlib`/`bcrypt`), JWT issuance/validation, `/api/v1/auth/*` endpoints, and legacy role models (`Admin`, `Executive`, `Inventory Manager`, `Warehouse Worker`, `Finance Employee`, `Sales Employee`).
- **Workspace Provenance vs. Identity:** Planned operational requests carry `X-NEXORA-Workspace` (UI context attribution) and optional `X-Correlation-ID` headers for traceability in `audit_logs`. Selecting a workspace filters UI navigation and records workspace provenance only — it **must never** be documented or treated as verified user identity or cryptographic access control.

---

## Section 2 — Implementation Status and API Classification

### 2.1 Classification Definitions

| Status | Meaning |
| :--- | :--- |
| **`IMPLEMENTED`** | Route exists in current FastAPI source code, executes live on `main`, and has automated `pytest` verification. |
| **`PARTIALLY IMPLEMENTED`** | A working prototype or narrow subset exists on `main`, but the complete Blueprint module and MySQL persistence are not yet built. |
| **`EXPERIMENTAL`** | Working experimental or comparative research endpoint on `main`, isolated from the production baseline contract. |
| **`PLANNED`** | Approved target API capability defined by Technical Blueprint v2.2, `FEATURES_STATUS.md` v2.3, and `DATABASE_SCHEMA.md` v2.8; **does not exist on `main`**. |
| **`EXCLUDED`** | Functionality explicitly outside approved project scope (`EXCL-01`–`EXCL-08`); must not be built or documented as planned endpoints. |

> [!NOTE]
> A route path appearing in Technical Blueprint v2.2 (`Section 13.3`) or a Postman example collection does **not** make that endpoint `IMPLEMENTED`. Only verified route decorators in `backend/app/` count as implemented.

### 2.2 Complete Live Route Inventory on `main` (`20` Handlers Verified)

| # | Method | Exact Path | Source File | OpenAPI (`/openapi.json`) | Classification | Supporting Tests |
| :-: | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `GET` | `/` | `backend/app/main.py` | Included | `IMPLEMENTED` | `test_main.py` |
| 2 | `GET` | `/health` | `backend/app/main.py` | Included | `IMPLEMENTED` | `test_main.py`, `test_startup_readiness.py`, `test_experimental_forecast.py` |
| 3 | `GET` | `/ready` | `backend/app/main.py` | Included | `IMPLEMENTED` | `test_startup_readiness.py`, `test_experimental_forecast.py` |
| 4 | `GET` | `/api/v1/health` | `backend/app/main.py` | **Excluded** (`include_in_schema=False`) | `IMPLEMENTED` | Alias to `health_check()` (manual / Postman verified) |
| 5 | `GET` | `/api/v1/ready` | `backend/app/main.py` | **Excluded** (`include_in_schema=False`) | `IMPLEMENTED` | Alias to `readiness_check()` (Postman collection verified) |
| 6 | `GET` | `/api/v1/forecast/horizons` | `routes/forecast.py` | Included | `IMPLEMENTED` | `test_main.py`, `test_forecast_api.py` |
| 7 | `GET` | `/api/v1/forecast/model-metrics` | `routes/forecast.py` | Included | `IMPLEMENTED` | `test_forecast_api.py` |
| 8 | `GET` | `/api/v1/forecast/model-info` | `routes/forecast.py` | Included | `IMPLEMENTED` | `test_forecast_api.py` |
| 9 | `POST` | `/api/v1/forecast/` | `routes/forecast.py` | Included | `IMPLEMENTED` | `test_forecast_api.py`, `test_historical_forecast.py`, `test_startup_readiness.py` |
| 10 | `POST` | `/api/v1/forecast/predict` | `routes/forecast.py` | Included | `IMPLEMENTED` | `test_forecast_api.py`, `test_historical_forecast.py`, `test_experimental_forecast.py` |
| 11 | `GET` | `/api/v1/forecast/evaluation-comparison` | `routes/forecast.py` | Included | `EXPERIMENTAL` | `test_experimental_forecast.py` (`test_evaluation_comparison_endpoint`) |
| 12 | `GET` | `/api/v1/forecast/store-wide` | `routes/forecast.py` | Included | `EXPERIMENTAL` | `test_experimental_forecast.py` (`test_store_wide_forecast_endpoint`) |
| 13 | `GET` | `/api/v1/experimental/ready` | `routes/experimental_forecast.py` | Included | `EXPERIMENTAL` | `test_experimental_forecast.py` |
| 14 | `GET` | `/api/v1/experimental/forecast/horizons` | `routes/experimental_forecast.py` | Included | `EXPERIMENTAL` | `test_experimental_forecast.py` |
| 15 | `GET` | `/api/v1/experimental/forecast/model-metrics` | `routes/experimental_forecast.py` | Included | `EXPERIMENTAL` | `test_experimental_forecast.py` |
| 16 | `GET` | `/api/v1/experimental/forecast/model-info` | `routes/experimental_forecast.py` | Included | `EXPERIMENTAL` | `test_experimental_forecast.py` |
| 17 | `POST` | `/api/v1/experimental/forecast/predict` | `routes/experimental_forecast.py` | Included | `EXPERIMENTAL` | `test_experimental_forecast.py` |
| 18 | `POST` | `/api/v1/experimental/forecast` | `routes/experimental_forecast.py` | Included | `EXPERIMENTAL` | `test_experimental_forecast.py` |
| 19 | `POST` | `/api/v1/experimental/forecast/` | `routes/experimental_forecast.py` | **Excluded** (`include_in_schema=False`) | `EXPERIMENTAL` | Trailing-slash compatibility alias delegating to `/forecast/predict` |
| 20 | `POST` | `/api/v1/inventory/recommend` | `routes/inventory.py` | Included | `PARTIALLY IMPLEMENTED` | `test_inventory_recommend.py` |

*(Plus FastAPI built-in documentation routes `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, and `/redoc`.)*

---

## Section 3 — Currently Implemented General Endpoints

All general application endpoints are declared in [`backend/app/main.py`](../backend/app/main.py).

### 3.1 Liveness vs. Readiness Semantics

| Probe Type | Endpoint(s) | Guarantees Checked | Failure Behavior | When to Use |
| :--- | :--- | :--- | :--- | :--- |
| **Root Metadata** | `GET /` | FastAPI process responding | None (`200 OK`) | Quick service discovery |
| **Liveness Probe** | `GET /health`<br>`GET /api/v1/health` | HTTP event loop / ASGI worker alive; does **not** touch ML artifacts or CSV data | Always `200 OK` if process is up | Container/process liveness ping |
| **Readiness Probe** | `GET /ready`<br>`GET /api/v1/ready` | Production `prediction_service` (4 models loaded) **AND** `historical_data_service` (`daily_product_demand.csv` indexed) | Returns HTTP `503` with `status: "not_ready"` and component `error` details | Traffic routing / pre-forecast check |

> [!NOTE]
> **Schema Visibility & Experimental Failure Isolation:**
> 1. Both `/api/v1/health` and `/api/v1/ready` are registered with `include_in_schema=False`, so they work at runtime while staying hidden from `/docs` and `/openapi.json`.
> 2. `GET /ready` includes an `experimental_models` block when `experimental_prediction_service` is loaded or present (`models_count > 0` or `ready`), or an error summary on failure, but **Task 12 experimental availability does NOT gate `/ready`**. Production `/ready` remains HTTP `200 OK` even if Task 12 models are absent (`test_experimental_models_unavailable_failure_isolation`).

### 3.2 Endpoint Specifications & Verified Responses

#### `GET /` — Root Service Metadata (`IMPLEMENTED`)
- **OpenAPI:** Included (`tag: General`, `response_model: None`).
- **Response (`200 OK` — verified live):**
  ```json
  {
    "project": "NEXORA Retail Management & Intelligence System",
    "version": "0.1.0",
    "status": "online",
    "documentation": "/docs"
  }
  ```
- **Tests:** [`backend/tests/test_main.py`](../backend/tests/test_main.py) (`test_root_endpoint`).

#### `GET /health` and `GET /api/v1/health` — Liveness Probe (`IMPLEMENTED`)
- **OpenAPI:** `/health` included (`tag: General`); `/api/v1/health` excluded (`include_in_schema=False`, delegates to `health_check()`).
- **Response (`200 OK` — verified live):**
  ```json
  {
    "status": "healthy",
    "service": "backend",
    "version": "0.1.0"
  }
  ```
- **Tests:** `test_main.py` (`test_health_check_endpoint`), `test_startup_readiness.py` (`test_09_liveness_probe_returns_200`), `test_experimental_forecast.py` (`test_production_health_check`).

#### `GET /ready` and `GET /api/v1/ready` — Readiness Probe (`IMPLEMENTED`)
- **OpenAPI:** `/ready` included (`tag: General`, `response_model: ReadinessResponse`); `/api/v1/ready` excluded (`include_in_schema=False`, delegates to `readiness_check(response)`).
- **Response Schema:** `ReadinessResponse` (`status`, `service`, `version`, `models: ComponentReadiness`, `historical_data: ComponentReadiness`, `experimental_models: Optional[ComponentReadiness]`).
- **HTTP Status Codes:**
  - `200 OK`: When `prediction_service.get_status()["ready"] and historical_data_service.get_status()["ready"]`.
  - `503 Service Unavailable`: Sets `response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE` and returns `status: "not_ready"` with populated `error` fields on failing component(s). Note: FastAPI returns the structured `ReadinessResponse` payload directly rather than `{"detail": ...}`.
- **Response (`200 OK` — verified live):**
  ```json
  {
    "status": "ready",
    "service": "backend",
    "version": "0.1.0",
    "models": {
      "ready": true,
      "models_count": 4,
      "loaded_horizons": [7, 15, 30, 90],
      "total_skus": null,
      "total_records": null,
      "dataset_file": null,
      "demand_data_ready": null,
      "price_service_ready": null,
      "models_dir": null,
      "price_service": null,
      "error": null
    },
    "historical_data": {
      "ready": true,
      "models_count": null,
      "loaded_horizons": null,
      "total_skus": 4905,
      "total_records": 2287495,
      "dataset_file": "daily_product_demand.csv",
      "demand_data_ready": true,
      "price_service_ready": true,
      "models_dir": null,
      "price_service": {
        "ready": true,
        "total_skus": 4905,
        "global_dates_count": 604,
        "cache_file": "pit_sku_price_history.json",
        "cache_metadata": {
          "source_file": "clean_gross_sales.csv",
          "total_skus": 4905,
          "total_transactions": 1037089,
          "global_dates_count": 604,
          "schema_version": "1.1"
        },
        "error": null
      },
      "error": null
    },
    "experimental_models": {
      "ready": true,
      "models_count": 4,
      "loaded_horizons": [7, 15, 30, 90],
      "total_skus": null,
      "total_records": null,
      "dataset_file": null,
      "demand_data_ready": null,
      "price_service_ready": true,
      "models_dir": "models_task12",
      "price_service": null,
      "error": null
    }
  }
  ```
- **Tests:** `test_startup_readiness.py` (`test_10_readiness_probe_returns_200_when_ready`, `test_11_readiness_returns_503_when_model_service_fails`, `test_12_readiness_returns_503_when_historical_data_fails`), `test_experimental_forecast.py` (`test_production_readiness_probe_backward_compatibility`, `test_readiness_distinguishes_demand_from_price_service`, `test_experimental_models_unavailable_failure_isolation`).

---

## Section 4 — Production Forecasting API

All seven routes under `/api/v1/forecast` live in [`backend/app/api/routes/forecast.py`](../backend/app/api/routes/forecast.py) (`tag: "Forecast"`). Five belong to the **Production Baseline (`IMPLEMENTED`)**, and two (`/evaluation-comparison`, `/store-wide`) are **`EXPERIMENTAL`** comparative/macro research endpoints co-located on the same router.

### 4.1 Automatic Historical CSV Feature Extraction vs. Manual Input

When calling `POST /api/v1/forecast/` or `POST /api/v1/forecast/predict`:

1. **Auto-Generated Mode (`is_auto_generated: true`):** Triggered automatically whenever nested `request.features` is omitted (`None`) **and** all six required core flat lag/rolling fields (`lag_1`, `lag_7`, `lag_14`, `lag_28`, `rolling_mean_7`, `rolling_mean_28`) are omitted (`None`).
   - Looks up `stock_code` in `HistoricalDataService` (`backend/ml/data/processed/daily_product_demand.csv`, `4,905` indexed SKUs).
   - Missing SKU raises `HistoricalDataNotFoundError` $\rightarrow$ **`404 Not Found`**.
   - SKUs with fewer than **`29` continuous calendar days** cannot form 28-day lag and rolling features and raise `InsufficientHistoryError` $\rightarrow$ **`422 Unprocessable Content`** (e.g., SKU `90004A` with 1 day, or `20877` with 9 days).
   - Automatically extracts leakage-free lag/rolling features as of the SKU's latest observation date (up to `2011-12-09`) and emits an informational notice inside `warnings`.
2. **Manual Mode (`is_auto_generated: false`):** Caller supplies either nested `features` (`HistoricalFeatures`) or all six core flat lag/rolling fields (`lag_1`, `lag_7`, `lag_14`, `lag_28`, `rolling_mean_7`, `rolling_mean_28`). Partial manual lag specifications (some core fields supplied, others missing) fail validation with **`422 Unprocessable Content`**. Optional calendar fields (`day_of_week`, `month`, `day_of_month`) default safely if omitted in manual mode (`0`, `1`, `1`).
3. **Supported Planning Horizons:** `[7, 15, 30, 90]` days. Empty or unsupported horizons (e.g., `[999]`) fail validation with **`422 Unprocessable Content`**. Omitting both `horizons` and legacy `horizon_days` forecasts all four horizons `[7, 15, 30, 90]`.
4. **Non-Negativity Clamp:** All model predictions are clamped to `max(0.0, pred)` and rounded to 4 decimal places.

### 4.2 Request & Response Schemas ([`backend/app/schemas/forecast.py`](../backend/app/schemas/forecast.py))

#### `ForecastRequest`

| Field | Type | Required | Constraints / Default | Notes |
| :--- | :--- | :---: | :--- | :--- |
| `stock_code` | `str` | Yes | `min_length=1`, stripped | Must not be blank/whitespace |
| `horizons` | `Optional[List[int]]` | No | Values in `{7, 15, 30, 90}`; deduplicated preserving order | Defaults to `[7, 15, 30, 90]` if omitted |
| `horizon_days` | `Optional[int]` | No | Must be in `{7, 15, 30, 90}` | Legacy single-horizon alias (used only if `horizons` omitted) |
| `features` | `Optional[HistoricalFeatures]` | No | Nested feature object | Mutually redundant with flat feature fields |
| `day_of_week` | `Optional[int]` | No | `0 <= x <= 6` | Flat alias |
| `month` | `Optional[int]` | No | `1 <= x <= 12` | Flat alias |
| `day_of_month` | `Optional[int]` | No | `1 <= x <= 31` | Flat alias |
| `lag_1`, `lag_7`, `lag_14`, `lag_28` | `Optional[float]` | Conditional | `>= 0.0`, finite (no `NaN`/`Inf`) | All 4 + rolling 7 & 28 required if any manual lag provided |
| `rolling_mean_7`, `rolling_mean_28` | `Optional[float]` | Conditional | `>= 0.0`, finite | Required in manual mode |
| `lag_60`, `rolling_mean_14`, `rolling_mean_60`, `rolling_std_7`, `rolling_std_28`, `momentum_ratio`, `unit_price` | `Optional[float]` | No | `>= 0.0`, finite | Optional extended Task 12 features |
| `zero_fraction_28`, `has_60d_history` | `Optional[float]` | No | `0.0 <= x <= 1.0`, finite | Optional extended Task 12 features |
| `observation_date` | `Optional[str]` | No | Default `None` | Optional historical cutoff / inference date (`YYYY-MM-DD`) |

#### `HistoricalFeatures`
Same feature fields (`day_of_week`, `month`, `day_of_month` optional `None`; `lag_1`, `lag_7`, `lag_14`, `lag_28`, `rolling_mean_7`, `rolling_mean_28` required `float >= 0.0` and finite; plus optional Task 12 extended features above).

#### `ForecastResponse`

| Field | Type | Default / Source | Description |
| :--- | :--- | :--- | :--- |
| `stock_code` | `str` | Echoed trimmed SKU | Product identifier |
| `horizons` | `List[int]` | Requested / `[7, 15, 30, 90]` | Forecasted horizons in days |
| `predictions` | `Dict[str, float]` | `{ "7": ..., ... }` | Stringified horizon keys mapped to clamped non-negative demand |
| `horizon_details` | `List[HorizonPredictionDetail]` | `horizon_days`, `predicted_demand`, `model_name`, `wape` | Per-horizon prediction + model + WAPE (%) breakdown |
| `units` | `str` | `"units"` | Demand unit label |
| `model_version` | `str` | `"v1.0"` default; live uses registry milestone | Active model registry identifier |
| `timestamp` | `str` | UTC ISO-8601 (`+00:00`) | Inference generation time |
| `warnings` | `List[str]` | `[]` | Auto-generation notice, unseen-SKU notice, experimental notice |
| `observation_date` | `Optional[str]` | `None` or date string | Latest historical observation date used |
| `history_days` | `Optional[int]` | `None` or integer | Available continuous daily history count |
| `is_auto_generated` | `bool` | `False` | `true` when features extracted from CSV |
| `status` | `str` | `"success"` | Status string |
| `total_predicted_demand` | `Optional[float]` | First predicted horizon value | Backward-compatibility legacy scalar |
| `horizon_days` | `Optional[int]` | Single integer or `None` | Populated only for legacy `horizon_days` requests; `null` otherwise |

---

### 4.3 Production Baseline Route Reference

#### 1. `GET /api/v1/forecast/horizons`
1. **HTTP Method:** `GET`
2. **Exact Path:** `/api/v1/forecast/horizons`
3. **Implementation Status:** `IMPLEMENTED`
4. **Purpose:** Returns supported planning horizons `[7, 15, 30, 90]` and operational retail descriptions.
5. **Request:** None.
6. **Verified Live Response (`200 OK`):**
   ```json
   {
     "supported_horizons_days": [7, 15, 30, 90],
     "description": "Multi-horizon retail demand planning windows (7 to 90 days).",
     "horizon_definitions": {
       "7": "Weekly fast-moving replenishment & shelf restock",
       "15": "Bi-weekly supplier batch ordering",
       "30": "Monthly inventory planning & space allocation",
       "90": "Quarterly supplier volume quotas & supply chain planning"
     }
   }
   ```
7. **Errors:** `500` on unexpected error.
8. **Pydantic Schema:** `SupportedHorizonsResponse`.
9. **Tests:** `test_main.py` (`test_forecast_horizons_endpoint`), `test_forecast_api.py` (`test_01_supported_horizons_endpoint`).

#### 2. `GET /api/v1/forecast/model-metrics`
1. **HTTP Method:** `GET`
2. **Exact Path:** `/api/v1/forecast/model-metrics`
3. **Implementation Status:** `IMPLEMENTED`
4. **Purpose:** Exposes chronological out-of-time evaluation benchmarks (MAE, RMSE, WAPE, split cutoffs, embargo gaps, candidate model comparisons) for production models.
5. **Request:** None.
6. **Verified Live Summary (`200 OK` — `backend/ml/models/models_metadata.json`):**
   - `milestone`: `"Phase 1 (Task 5 Model Training & Serialization)"`
   - `dataset_reference`: `"ml_feature_dataset.csv"`
   - `encoding_strategy`: `"OneHotEncoder(max_categories=50, handle_unknown='infrequent_if_exist', sparse_output=False)"`
   - `backtesting_strategy`: `"Single chronological out-of-time holdout per horizon with strict purge/embargo gap"`
   - **Verified Selected Metrics (`models`):**
     - `D_7`: `Linear Regression` (`Ridge alpha=1.0`), `mae=37.4318`, `rmse=92.5686`, `wape=55.654%`, `embargo_gap_days=8` (`42,091` val samples)
     - `D_15`: `Random Forest` (`n_estimators=25, max_depth=10`), `mae=72.9252`, `rmse=217.4885`, `wape=50.0048%`, `embargo_gap_days=16` (`57,840` val samples)
     - `D_30`: `Random Forest`, `mae=125.0314`, `rmse=406.2522`, `wape=48.7296%`, `embargo_gap_days=31` (`100,262` val samples)
     - `D_90`: `Random Forest`, `mae=343.3591`, `rmse=890.1797`, `wape=53.2187%`, `embargo_gap_days=91` (`98,157` val samples)
7. **Errors:** `503 Service Unavailable` when production models/metadata fail to load; `500` on unexpected error.
8. **Pydantic / Return Type:** Route signature declares `Dict[str, Any]` (`response_model=None` in OpenAPI; `ModelMetricsResponse` is defined in `forecast.py` but not enforced on the decorator).
9. **Tests:** `test_forecast_api.py` (`test_03_model_metrics_endpoint`).

#### 3. `GET /api/v1/forecast/model-info`
1. **HTTP Method:** `GET`
2. **Exact Path:** `/api/v1/forecast/model-info`
3. **Implementation Status:** `IMPLEMENTED`
4. **Purpose:** Reports runtime Python/scikit-learn versions, loaded estimator classes per horizon, categorical/numerical feature contracts, and unseen SKU handling.
5. **Request:** None.
6. **Verified Live Response (`200 OK`):**
   ```json
   {
     "project": "NEXORA – AI-Powered Retail Management & Intelligence System",
     "version": "1.0.0",
     "status": "ready",
     "python_version": "3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]",
     "scikit_learn_version": "1.9.1",
     "supported_horizons": [7, 15, 30, 90],
     "active_models": {
       "D_7": "Ridge",
       "D_15": "RandomForestRegressor",
       "D_30": "RandomForestRegressor",
       "D_90": "RandomForestRegressor"
     },
     "feature_columns": [
       "StockCode", "DayOfWeek", "Month", "DayOfMonth",
       "Lag1", "Lag7", "Lag14", "Lag28", "RollingMean7", "RollingMean28"
     ],
     "categorical_columns": ["StockCode"],
     "numerical_columns": [
       "DayOfWeek", "Month", "DayOfMonth",
       "Lag1", "Lag7", "Lag14", "Lag28", "RollingMean7", "RollingMean28"
     ],
     "unseen_sku_handling": "OneHotEncoder infrequent category mapping (scikit-learn native)"
   }
   ```
7. **Errors:** `503 Service Unavailable` if production registry is unready.
8. **Pydantic / Return Type:** Route declares `Dict[str, Any]` (`ModelInfoResponse` exists in `forecast.py` matching this key structure).
9. **Tests:** `test_forecast_api.py` (`test_02_model_info_endpoint`).

#### 4 & 5. `POST /api/v1/forecast/` and `POST /api/v1/forecast/predict`
1. **HTTP Method:** `POST`
2. **Exact Paths:** `/api/v1/forecast/` (primary) and `/api/v1/forecast/predict` (Blueprint alias delegating directly to `predict_demand`)
3. **Implementation Status:** `IMPLEMENTED`
4. **Purpose:** Generates single- or multi-horizon retail SKU demand forecasts from automatic historical CSV feature extraction or manual input.
5. **Request Body (`ForecastRequest`):**
   ```json
   {
     "stock_code": "85123A"
   }
   ```
6. **Verified Live Response (`200 OK` for `{"stock_code": "85123A"}`):**
   ```json
   {
     "stock_code": "85123A",
     "horizons": [7, 15, 30, 90],
     "predictions": {
       "7": 771.5717,
       "15": 3009.3201,
       "30": 3062.395,
       "90": 9427.142
     },
     "horizon_details": [
       { "horizon_days": 7, "predicted_demand": 771.5717, "model_name": "Linear Regression", "wape": 55.65 },
       { "horizon_days": 15, "predicted_demand": 3009.3201, "model_name": "Random Forest", "wape": 50.0 },
       { "horizon_days": 30, "predicted_demand": 3062.395, "model_name": "Random Forest", "wape": 48.73 },
       { "horizon_days": 90, "predicted_demand": 9427.142, "model_name": "Random Forest", "wape": 53.22 }
     ],
     "units": "units",
     "model_version": "Phase 1 (Task 5 Model Training & Serialization)",
     "timestamp": "2026-11-26T17:49:26.792577+00:00",
     "warnings": [
       "Historical demand features automatically generated from 739 daily records up to observation date 2011-12-09 (UCI Online Retail II dataset)."
     ],
     "observation_date": "2011-12-09",
     "history_days": 739,
     "is_auto_generated": true,
     "status": "success",
     "total_predicted_demand": 771.5717,
     "horizon_days": null
   }
   ```
7. **Verified Error Responses:**
   - `404 Not Found` (`HistoricalDataNotFoundError`):
     ```json
     {
       "detail": "Product SKU 'NON_EXISTENT_SKU_99999' was not found in historical sales records. Ensure the SKU exists in the UCI Online Retail II catalog."
     }
     ```
   - `422 Unprocessable Content` (`InsufficientHistoryError`, e.g., `90004A` with `< 29` calendar days):
     ```json
     {
       "detail": "Insufficient historical sales data for SKU '90004A' (1 calendar days available; minimum 29 days required to compute 28-day lag and rolling average features)."
     }
     ```
   - `422 Unprocessable Content` (Pydantic validation failure, e.g., `horizons: [999]`): Standard FastAPI list `{"detail": [{"type": "value_error", "loc": ["body"], "msg": "..."}]}`.
   - `503 Service Unavailable`: Model registry unready (`FileNotFoundError`, `RuntimeError`, or `DatasetUnavailableError`).
   - `500 Internal Server Error`: Unexpected unhandled exception.
8. **Pydantic Schemas:** Request `ForecastRequest` (`HistoricalFeatures`); Response `ForecastResponse` (`HorizonPredictionDetail`).
9. **Tests:** `test_forecast_api.py` (`test_04`–`test_15`), `test_historical_forecast.py` (`test_05`–`test_10`), `test_startup_readiness.py` (`test_13`–`test_15`), `test_experimental_forecast.py` (`test_production_forecast_predict_unchanged`).

---

### 4.4 Comparative & Store-Wide Routes on `/api/v1/forecast` (`EXPERIMENTAL`)

Although mounted inside [`backend/app/api/routes/forecast.py`](../backend/app/api/routes/forecast.py) under tag `"Forecast"`, these two routes read experimental benchmark files under `backend/ml/models_experimental/` via `store_wide_service.py` rather than serving single-SKU production predictions.

#### 6. `GET /api/v1/forecast/evaluation-comparison`
1. **HTTP Method:** `GET`
2. **Exact Path:** `/api/v1/forecast/evaluation-comparison`
3. **Implementation Status:** `EXPERIMENTAL` *(Implemented comparative evaluation endpoint)*
4. **Purpose:** Compares SKU-level production baseline benchmarks, intermediate experimental optimized SKU benchmarks, and aggregated 3,922-SKU store-wide macro WAPE (`5.61%`–`12.15%`) across horizons `7`, `15`, `30`, and `90`.
5. **Request:** None.
6. **Verified Live Response Summary (`200 OK`):** Returns `title`, `investigation_summary`, and `evaluation_tiers` array containing `D_7`, `D_15`, `D_30`, and `D_90` objects with nested `production_baseline_sku`, `optimized_experimental_sku`, and `store_wide_macro` blocks (`D_7` store WAPE `8.87%`, `D_15` `12.15%`, `D_30` `7.56%`, `D_90` `5.61%`).
7. **Errors:** `500 Internal Server Error` if metadata loading fails.
8. **Return Type:** `Dict[str, Any]`.
9. **Tests:** `test_experimental_forecast.py` (`test_evaluation_comparison_endpoint`).

#### 7. `GET /api/v1/forecast/store-wide`
1. **HTTP Method:** `GET`
2. **Exact Path:** `/api/v1/forecast/store-wide`
3. **Implementation Status:** `EXPERIMENTAL` *(Implemented store-wide macro forecast endpoint)*
4. **Purpose:** Serves store-wide aggregate macro demand forecasts summed across 3,922 catalog SKUs (`scope: "STORE_WIDE_AGGREGATE"`).
5. **Request:** None.
6. **Verified Live Response (`200 OK`):**
   ```json
   {
     "scope": "STORE_WIDE_AGGREGATE",
     "description": "Macro-level retail sales volume aggregated across all 3,922 catalog SKUs.",
     "observation_date": "2011-12-09",
     "latest_daily_store_demand": 93980,
     "historical_run_rates": {
       "rolling_mean_7d": 27602.57,
       "rolling_mean_14d": 24228.29,
       "rolling_mean_28d": 25081.75
     },
     "predictions": {
       "7": 175572.2,
       "15": 376226.2,
       "30": 752452.5,
       "90": 2257357.5
     },
     "horizon_details": [
       { "horizon_days": 7, "predicted_store_demand": 175572.2, "model_name": "Moving_Average_28", "store_wape": 8.87, "mae": 15100.0, "bias_pct": 0.97 },
       { "horizon_days": 15, "predicted_store_demand": 376226.2, "model_name": "Random_Forest", "store_wape": 12.15, "mae": 45795.7, "bias_pct": 5.79 },
       { "horizon_days": 30, "predicted_store_demand": 752452.5, "model_name": "HistGradientBoosting", "store_wape": 7.56, "mae": 53221.7, "bias_pct": 6.0 },
       { "horizon_days": 90, "predicted_store_demand": 2257357.5, "model_name": "HistGradientBoosting", "store_wape": 5.61, "mae": 101012.7, "bias_pct": 5.32 }
     ],
     "status": "success"
   }
   ```
7. **Errors:** `503 Service Unavailable` (`FileNotFoundError`), `500 Internal Server Error` otherwise.
8. **Return Type:** `Dict[str, Any]`.
9. **Tests:** `test_experimental_forecast.py` (`test_store_wide_forecast_endpoint`).

---

## Section 5 — Experimental Forecasting API

The **Task 12 Experimental Forecasting API** lives in [`backend/app/api/routes/experimental_forecast.py`](../backend/app/api/routes/experimental_forecast.py) (`/api/v1/experimental`, `tag: "Experimental Forecast"`). Every route in this group is strictly classified **`EXPERIMENTAL`** and isolated from the Production Baseline (`Section 4`).

### 5.1 Architectural Differences vs. Production Baseline

| Dimension | Production Baseline (`/api/v1/forecast/*`) | Task 12 Experimental (`/api/v1/experimental/*`) |
| :--- | :--- | :--- |
| **Artifact Directory** | `backend/ml/models/` | `backend/ml/models_task12/` |
| **Service Class** | `PredictionService` | `ExperimentalPredictionService` |
| **Training Span & CV** | 1-year `ml_feature_dataset.csv`, single out-of-time split | 2-year dataset (`2009-12-01` to `2011-12-09`, `738` days), 3-fold `DateGroupedTimeSeriesSplit` + holdout |
| **Feature Contract** | 10 columns (`StockCode`, calendar, 4 lags, 2 rolling means) | 20-column input (`19` model features + `date` for chronological encoding & PIT pricing) |
| **SKU Encoding** | `OneHotEncoder(max_categories=50, handle_unknown='infrequent_if_exist')` | `ChronologicalTargetEncoder` (point-in-time cumulative mean with global-mean fallback) |
| **Price Integration** | None | `PITPriceService` — point-in-time historical median `UnitPrice` strictly before `date` `t` |
| **Selected Estimators** | `Ridge` (7d), `RandomForestRegressor` (15/30/90d) | `ElasticNet` (7/30/90d), `Residual_RollingMean28_Ridge_a_100.0` (15d) |
| **Holdout WAPE** | `55.65%` / `50.00%` / `48.73%` / `53.22%` | `54.20%` / `44.88%` / `45.10%` / `48.22%` |
| **Readiness Isolation** | Gates `GET /ready` (`200` / `503`) | Separate `GET /api/v1/experimental/ready`; requires `pit_price_service`; **never breaks production `/ready`** |

> [!NOTE]
> **Historical Feature & Pricing Fallback:** During experimental prediction, `HistoricalDataService` extracts extended features (`Lag60`, `RollingMean14/60`, `RollingStd7/28`, `ZeroFraction28`, `MomentumRatio`, `Has60dHistory`) and looks up cutoff-aware median `UnitPrice` via `PITPriceService` (excluding date `t` and all future dates to preserve causal invariance). If `PITPriceService` is disabled (`use_pit_price` unavailable), `HistoricalDataService` safely falls back to `0.0` while `/api/v1/experimental/ready` degrades to `503`.

### 5.2 Experimental Route Reference (`7` Handlers Verified)

| # | Method | Exact Path | OpenAPI Visibility | Status | Purpose / Notes |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | `GET` | `/api/v1/experimental/ready` | Included | `EXPERIMENTAL` | Experimental readiness (`200` only if `experimental_prediction_service.is_ready()` including `pit_price_service` AND `historical_data_service.is_ready()`; otherwise `503`) |
| 2 | `GET` | `/api/v1/experimental/forecast/horizons` | Included | `EXPERIMENTAL` | Supported `[7, 15, 30, 90]` horizons plus Task 12 selected model names per horizon |
| 3 | `GET` | `/api/v1/experimental/forecast/model-metrics` | Included | `EXPERIMENTAL` | Task 12 CV + holdout benchmarks (`WAPE`, `MAE`, `RMSE`, `bias_pct`, `task10_benchmark_*`); `503` if unready |
| 4 | `GET` | `/api/v1/experimental/forecast/model-info` | Included | `EXPERIMENTAL` | Runtime Task 12 model types, 20-column contract, encoder, and pricing strategy; `503` if unready |
| 5 | `POST` | `/api/v1/experimental/forecast/predict` | Included | `EXPERIMENTAL` | Task 12 multi-horizon inference (`ForecastRequest` $\rightarrow$ `ForecastResponse`) |
| 6 | `POST` | `/api/v1/experimental/forecast` | Included | `EXPERIMENTAL` | Root alias calling `predict_experimental_demand` |
| 7 | `POST` | `/api/v1/experimental/forecast/` | **Excluded** (`include_in_schema=False`) | `EXPERIMENTAL` | Trailing-slash compatibility alias calling `predict_experimental_demand` |

#### Verified Experimental Outputs (`test_experimental_forecast.py` & Live Run)

- **`GET /api/v1/experimental/ready` (`200 OK`):** Reports `status: "ready"`, `service: "experimental_forecast"`, `experimental_models: {"ready": true, "models_count": 4, "loaded_horizons": [7, 15, 30, 90], "models_dir": "models_task12", "price_service_ready": true}`, and full `historical_data` + `price_service` telemetry.
- **`POST /api/v1/experimental/forecast/predict` (`{"stock_code": "85123A"}` — `200 OK` verified live):**
  ```json
  {
    "stock_code": "85123A",
    "horizons": [7, 15, 30, 90],
    "predictions": {
      "7": 897.1411,
      "15": 1903.8282,
      "30": 3903.9246,
      "90": 11325.054
    },
    "horizon_details": [
      { "horizon_days": 7, "predicted_demand": 897.1411, "model_name": "ElasticNet_a_0.01_l1_0.8", "wape": 54.2 },
      { "horizon_days": 15, "predicted_demand": 1903.8282, "model_name": "Residual_RollingMean28_Ridge_a_100.0", "wape": 44.88 },
      { "horizon_days": 30, "predicted_demand": 3903.9246, "model_name": "ElasticNet_a_0.01_l1_0.2", "wape": 45.1 },
      { "horizon_days": 90, "predicted_demand": 11325.054, "model_name": "ElasticNet_a_0.1_l1_0.8", "wape": 48.22 }
    ],
    "units": "units",
    "model_version": "Task 12 Experimental (2009-12-01 to 2011-12-09 (738 calendar days))",
    "timestamp": "2026-11-26T17:49:26.871425+00:00",
    "warnings": [
      "Historical demand features automatically generated from 739 daily records up to observation date 2011-12-09 (UCI Online Retail II 2-year recovered dataset).",
      "Experimental Task 12 ML models active (chronological TargetEncoder, PIT price, 2-year data)."
    ],
    "observation_date": "2011-12-09",
    "history_days": 739,
    "is_auto_generated": true,
    "status": "success",
    "total_predicted_demand": 897.1411,
    "horizon_days": null
  }
  ```
- **Verified Errors:** `404` (`HistoricalDataNotFoundError`), `422` (`InsufficientHistoryError`, e.g., SKU `20877` with `9` calendar days, or Pydantic validation error), `503` (`DatasetUnavailableError` / unready experimental service or price service on `/ready`), `500`.

---

## Section 6 — Inventory Recommendation API

Implemented in [`backend/app/api/routes/inventory.py`](../backend/app/api/routes/inventory.py), [`backend/app/schemas/inventory.py`](../backend/app/schemas/inventory.py), and [`backend/app/services/inventory_service.py`](../backend/app/services/inventory_service.py).

- **Endpoint:** `POST /api/v1/inventory/recommend`
- **Classification:** **`PARTIALLY IMPLEMENTED`** *(Stateless Phase 1 Replenishment Prototype)*
- **Tests:** [`backend/tests/test_inventory_recommend.py`](../backend/tests/test_inventory_recommend.py) (`13` test cases)

### 6.1 Request & Response Contracts

#### `InventoryRecommendationRequest`

| Field | Type | Required | Default | Validation Constraints |
| :--- | :--- | :---: | :--- | :--- |
| `stock_code` | `str` | Yes | — | `min_length=1`, whitespace stripped; blank rejected (`422`) |
| `current_stock` | `float` | Yes | — | `>= 0.0`, finite (caller-supplied!) |
| `lead_time_days` | `int` | No | `7` | `1 <= x <= 180` |
| `review_period_days` | `int` | No | `7` | `1 <= x <= 180` |
| `safety_stock_days` | `float` | No | `3.0` | `0.0 <= x <= 90.0`, finite |
| `use_experimental` | `bool` | No | `False` | Verified: routes demand forecast through Task 12 models when `true` (`test_13_task12_experimental_model_support`) |

#### `InventoryRecommendationResponse`

| Field | Type | Computation / Semantics |
| :--- | :--- | :--- |
| `stock_code` | `str` | Requested product SKU |
| `current_stock` | `float` | Rounded input (`round(..., 2)`) |
| `lead_time_days` | `int` | Requested supplier lead time |
| `review_period_days` | `int` | Requested review interval |
| `coverage_period_days` | `int` | `lead_time_days + review_period_days` |
| `forecast_demand` | `float` | Piecewise linear interpolation across `[7, 15, 30, 90]` forecasts (capped/scaled past 90d using `D_90 / 90.0`) rounded to 2 decimals |
| `daily_demand_rate` | `float` | `forecast_demand / coverage_period_days`, rounded to 4 decimals |
| `safety_stock_days` | `float` | Requested buffer days |
| `safety_stock` | `float` | `(forecast_demand / coverage_period_days) * safety_stock_days`, rounded to 2 decimals |
| `target_stock` | `float` | `forecast_demand + safety_stock`, rounded to 2 decimals |
| `recommended_purchase_quantity` | `float` | `max(0.0, round(target_stock - current_stock, 2))` |
| `stock_condition` | `str` | `"CRITICAL"` (`current < forecast_demand`), `"ELEVATED"` (`forecast_demand <= current < target_stock`), or `"SAFE"` (`current >= target_stock`) |
| `recommendation` | `str` | Actionable plain-English text (displaying rounded `int` counts in prose) |
| `calculation_explanation` | `str` | Step-by-step transparent breakdown of all numbers |
| `model_used` | `str` | `"Production Baseline (...)"` or `"Task 12 Experimental (...)"` |
| `timestamp` | `str` | UTC ISO-8601 timestamp (`+00:00`) |

### 6.2 Verified Example Response (`POST /api/v1/inventory/recommend` — `200 OK`)

Request: `{"stock_code": "85123A", "current_stock": 100.0, "lead_time_days": 7, "review_period_days": 7, "safety_stock_days": 3.0}`

```json
{
  "stock_code": "85123A",
  "current_stock": 100.0,
  "lead_time_days": 7,
  "review_period_days": 7,
  "coverage_period_days": 14,
  "forecast_demand": 2729.6,
  "daily_demand_rate": 194.9715,
  "safety_stock_days": 3.0,
  "safety_stock": 584.91,
  "target_stock": 3314.51,
  "recommended_purchase_quantity": 3214.51,
  "stock_condition": "CRITICAL",
  "recommendation": "Purchase 3215 additional units to restore target inventory and protect against stockout risk through the 14-day replenishment cycle.",
  "calculation_explanation": "Coverage window of 14 days (lead time 7d + review period 7d) has projected demand of 2729.60 units (daily rate 194.97 units/day). Safety stock buffer of 3.0 days requires 584.91 units. Target stock level is 3314.51 units (2729.60 forecast + 584.91 safety stock). With current stock of 100.00 units, recommended purchase quantity is max(0, 3314.51 - 100.00) = 3214.51 units. Stock condition: CRITICAL.",
  "model_used": "Production Baseline (Phase 1 (Task 5 Model Training & Serialization))",
  "timestamp": "2026-11-26T17:49:27.020232+00:00"
}
```

- **Verified Errors:** `404` (`Product SKU '...' not found in historical retail catalog.`), `422` (`InsufficientHistoryError` or Pydantic constraint error like negative stock), `503` (missing historical service / unready models), `500`.

### 6.3 Critical Limitations (Do Not Confuse with Blueprint `M09` / `M14`)

> [!WARNING]
> **`POST /api/v1/inventory/recommend` is a stateless Phase 1 prototype — NOT the completed `M09 Inventory Control` or `M14 Predictive Planner` module:**
> - **Caller-Supplied Stock:** The caller manually passes `current_stock`; the endpoint does **not** query MySQL `inventory` tables or subtract `reserved_quantity` / add `incoming_stock`.
> - **Caller-Supplied Lead Time Defaults:** `lead_time_days` defaults to `7` and `review_period_days` defaults to `7` in the prototype request schema. Under approved **`DDR-01`**, live `M14` must look up `supplier_products.lead_time_days` $\rightarrow$ `suppliers.lead_time_days` and return **`UNAVAILABLE`** (never silently fabricate a 7-day lead time) when neither is configured.
> - **Formula Variance:** The prototype interpolates `lead_time_days + review_period_days` with `safety_stock_days`, whereas approved `DDR-01`–`DDR-03` defines `Lead-Time Demand = (Forecast_H / H) * L`, `Reorder Threshold = Lead-Time Demand * safety_factor`, `Projected Available = (Physical - Reserved) + Approved Outstanding Incoming`, and `Suggested Purchase Qty = max(0, Reorder Threshold - Projected Available)`.
> - **No PO Creation:** Never persists drafts to `purchase_orders` or emits automatic supplier orders.

---

## Section 7 — Planned Operational API Architecture

> [!IMPORTANT]
> **ENTIRE SECTION `7` IS `PLANNED` (NOT IMPLEMENTED ON `main`):**
> **Zero endpoints documented below exist in `backend/app/` today.** Prefix domains shown in Technical Blueprint v2.2 (`Section 13.3`) represent approved module entrypoints, while specific sub-resource routes and action paths labeled ***[Illustrative]*** are proposed REST designs subject to Phase 2–6 implementation review.

All planned operational routes preserve strict separation between distinct bounded contexts:
- **Orders != Sales** (`orders` / `order_fulfillments` vs. `transactions`)
- **Inventory Control != Stock Movement Tracking** (`inventory` live stock buckets vs. immutable `inventory_movements` ledger)
- **Demand Forecasting != Predictive Planner** (pure ML demand predictions vs. MySQL stock + supplier lead-time replenishment risk)
- **Anomaly Detection != Smart Alerts** (`anomaly_events` evidence vs. duplicate-suppressed `alerts`)
- **Stock Movements != Centralized Audit Logs** (unit inventory delta ledger vs. cross-system `audit_logs` governance trail)

### Module-by-Module Planned API Matrix (`18` Core Modules + `4` Supporting Capabilities)

#### Group 1 — Retail Foundation (`M01`–`M05`)

| Module | Blueprint Domain Prefix | Primary Planned REST Endpoints (`PLANNED`) | Backing MySQL Tables ([`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.8) | Audit Tier & Notes |
| :--- | :--- | :--- | :--- | :--- |
| **M01 Product Management** | `/api/v1/products` | `GET /api/v1/products` (filter/search/paginate)<br>`GET /api/v1/products/{product_id}`<br>`POST /api/v1/products` *(atomic SKU + initial `inventory` row)*<br>`PUT /api/v1/products/{product_id}`<br>`PATCH /api/v1/products/{product_id}/status` *(soft-deactivate/reactivate; `Discontinued` guard)*<br>`GET`/`POST`/`PUT` `/api/v1/categories` ***[Illustrative]***<br>UoM conversions $\rightarrow$ see [Section 7.5](#75-uom-api-planning) | `products`, `categories`, `uom_conversions`, `inventory` | **Tier 1** for lifecycle/price/status mutations (`is_uci_baseline` protected from deletion) |
| **M02 Supplier Management** | `/api/v1/suppliers` | `GET /api/v1/suppliers`<br>`GET /api/v1/suppliers/{supplier_id}`<br>`POST /api/v1/suppliers`<br>`PUT /api/v1/suppliers/{supplier_id}`<br>`PATCH /api/v1/suppliers/{supplier_id}/status`<br>`GET /api/v1/suppliers/{supplier_id}/products` *(`DDR-07`)*<br>`POST` / `PUT` / `PATCH /{id}/status` `/api/v1/suppliers/{supplier_id}/products` ***[Illustrative]*** | `suppliers`, `supplier_products` | Inactive `supplier_products` rows retained forever for historical traceability (`DDR-07`) |
| **M03 Customer Management** | `/api/v1/customers` | `GET /api/v1/customers` *(search/filter/paginate)*<br>`GET /api/v1/customers/{customer_id}`<br>`POST /api/v1/customers`<br>`PUT /api/v1/customers/{customer_id}`<br>`PATCH /api/v1/customers/{customer_id}/status` | `customers` | Deactivate-only if referenced by orders, transactions, or invoices |
| **M04 Sales Management** | `/api/v1/sales` | `GET /api/v1/sales` *(filter `source_origin`: `uci_historical` \| `operational`, `transaction_type`)*<br>`GET /api/v1/sales/{sale_id}`<br>`POST /api/v1/sales` *(direct completed sale capture)*<br>`POST /api/v1/sales/{sale_id}/reverse` ***[Illustrative]*** *(compensating reversal + `cancelled`/`reversed` state)* | `transactions`, `transaction_items` | Strictly distinct from Orders; completed rows retained permanently; **Tier 1** audit on reversals |
| **M05 Order Management** | `/api/v1/orders` | `GET /api/v1/orders`, `GET /api/v1/orders/{order_id}`<br>`POST /api/v1/orders` *(draft creation; `requested_delivery_date`, B2B demand type)*<br>`PUT /api/v1/orders/{order_id}` *(draft items edit)*<br>`POST /api/v1/orders/{order_id}/confirm` *(reserves stock)*<br>`POST /api/v1/orders/{order_id}/fulfill` *(partial/full batch)*<br>`POST /api/v1/orders/{order_id}/fulfillments/{fulfillment_id}/reverse` ***[Illustrative]***<br>`POST /api/v1/orders/{order_id}/cancel` | `orders`, `order_items`, `order_fulfillments`, `order_fulfillment_items` | See [Section 7.2](#72-order-fulfilment-and-shipping-apis); **Tier 1** atomic audit + `FOR UPDATE` locking |

#### Group 2 — Business Intelligence (`M06`–`M08`)

| Module | Blueprint Domain Prefix | Primary Planned REST Endpoints (`PLANNED`) | Backing MySQL Tables | Key Scope Rules |
| :--- | :--- | :--- | :--- | :--- |
| **M06 Business Intelligence** | `/api/v1/analytics` | `GET /api/v1/analytics/overview` ***[Illustrative]*** *(dataset vs. operational separated KPIs)*<br>`GET /api/v1/analytics/sales-trends` ***[Illustrative]***<br>`GET /api/v1/analytics/sku-rankings` ***[Illustrative]*** *(Gross, Returns, Cancellations, Net)*<br>`GET /api/v1/analytics/countries` ***[Illustrative]*** | `transactions`, `transaction_items`, `products`, `orders`, `returns` | Separates `GBP` UCI 2009–2011 baseline from `INR` live operational records |
| **M07 Seasonal Demand Calendar** | `/api/v1/intelligence/seasonality` | `GET /api/v1/intelligence/seasonality/heatmap` ***[Illustrative]*** *(month x day-of-week index)*<br>`GET /api/v1/intelligence/seasonality/peaks` ***[Illustrative]*** | `daily_demand_observations`, `transactions` | Uses positive clean demand only (`DDR-06` normalized) |
| **M08 Product Lifecycle Intelligence** | `/api/v1/intelligence/lifecycle` | `GET /api/v1/intelligence/lifecycle` ***[Illustrative]*** *(filter `Introduction`, `Growing`, `Mature`, `Declining`, `Dormant`, `Discontinued`)*<br>`POST /api/v1/intelligence/lifecycle/evaluate` ***[Illustrative]*** *(writes append-only snapshots; `DDR-08` hysteresis)*<br>`GET /api/v1/intelligence/lifecycle/{product_id}/history` ***[Illustrative]***<br>`PUT /api/v1/settings/lifecycle` ***[Illustrative]*** *(bounded settings)* | `product_lifecycle_snapshots`, `products`, `operational_settings` | `Discontinued` cannot be auto-assigned; historical snapshots never retroactively rewritten (`DDR-08`) |

#### Group 3 — Inventory & Procurement (`M09`–`M11`)

| Module | Blueprint Domain Prefix | Primary Planned REST Endpoints (`PLANNED`) | Backing MySQL Tables | Key Scope Rules |
| :--- | :--- | :--- | :--- | :--- |
| **M09 Inventory Control** | `/api/v1/inventory` | `GET /api/v1/inventory` *(returns separate `physical`, `reserved`, `available`, `incoming`, `projected_available`)*<br>`GET /api/v1/inventory/{product_id}`<br>`GET /api/v1/inventory/low-stock`<br>`POST /api/v1/inventory/adjustments` *(manual count/damage adjustment + ledger write)*<br>`PUT /api/v1/inventory/{product_id}/settings` *(`minimum_stock`, `safety_factor >= 1.00`)* | `inventory`, `inventory_movements`, `purchase_orders`, `purchase_order_items` | Strictly separate from `/inventory/movements`; direct silent updates to `current_quantity` forbidden; **Tier 1** audit on adjustments & settings; supersedes Phase 1 stateless `/recommend` |
| **M10 Stock Movement Tracking** | `/api/v1/inventory/movements` | `GET /api/v1/inventory/movements` *(filter `product_id`, `movement_type`, `reference_type`, `date_from`, `date_to`)*<br>`GET /api/v1/inventory/movements/{product_id}` ***[Illustrative]*** | `inventory_movements` | Strictly **read-only append-only ledger** (`adjustment`, `purchase_receipt`, `sale_fulfillment`, `return_restock`, `damaged`, `fulfillment_reversal`) |
| **M11 Purchase Planning Simulator** | `/api/v1/simulator` & `/api/v1/purchase-orders` | See detailed breakdown in [Section 7.1](#71-procurement-and-approval-apis) | `purchase_orders`, `purchase_order_items`, `purchase_order_approvals`, `purchase_order_receipts`, `purchase_order_receipt_items`, `operational_settings` | Stateless simulator separated from durable PO persistence + `DDR-09` dual-control approvals |

#### Group 4 — AI & Predictive Intelligence (`M12`–`M15`)

| Module | Blueprint Domain Prefix | Primary Planned REST Endpoints (`PLANNED`) | Backing MySQL Tables | Key Scope Rules |
| :--- | :--- | :--- | :--- | :--- |
| **M12 Demand Forecasting** | `/api/v1/forecast` | Existing routes preserved (`Section 4`) + Planned MySQL extensions:<br>`GET /api/v1/forecast/{product_id}`<br>`POST /api/v1/forecast/by-sku` *(persisted run + normalized base-UoM B2B observations)*<br>`GET /api/v1/forecast/runs` ***[Illustrative]*** | `model_runs`, `forecasts`, `daily_demand_observations`, `demand_adjustments`, `demand_quarantine` | Strictly separated from Predictive Planner; excludes `defective` returns from demand adjustments (`DDR-06`) |
| **M13 Price & Revenue Intelligence** | `/api/v1/intelligence` | `GET /api/v1/intelligence/price-distribution` ***[Illustrative]***<br>`GET /api/v1/intelligence/revenue-concentration` ***[Illustrative]*** | `products`, `transaction_items`, `invoice_items` | Read-only analytical elasticity/concentration; autonomous price markdowns **excluded (`EXCL-04`)** |
| **M14 Predictive Planner** | `/api/v1/predictive-planner` | `POST /api/v1/predictive-planner/recommend` *(live SKU risk evaluation)*<br>`GET /api/v1/predictive-planner/portfolio` *(multi-SKU risk portfolio)*<br>`POST /api/v1/predictive-planner/refresh` *(batch forecast + live stock risk evaluation)* | `forecasts`, `inventory`, `supplier_products`, `suppliers`, `purchase_orders`, `purchase_order_items` | Enforces `DDR-01`/`02`/`03`: `(Forecast/H)*L`, explicit `UNAVAILABLE` lead-time state, approved incoming stock only |
| **M15 Anomaly Detection** | `/api/v1/intelligence/anomalies` | `GET /api/v1/intelligence/anomalies` *(filter severity, type, date)*<br>`POST /api/v1/intelligence/anomalies/scan` *(runs statistical z-score w/ zero-variance guard + threshold scans)*<br>`PUT /api/v1/settings/anomalies` ***[Illustrative]*** *(bounded config `DDR-08`)* | `anomaly_events`, `operational_settings` | Stores immutable detection evidence; optionally triggers `alerts` (`SYS-03`) without conflating tables |

#### Group 5 — Business Operations (`M16`–`M18`)

| Module | Blueprint Domain Prefix | Primary Planned REST Endpoints (`PLANNED`) | Backing MySQL Tables | Key Scope Rules |
| :--- | :--- | :--- | :--- | :--- |
| **M16 Return Intelligence** | `/api/v1/returns` & `/api/v1/intelligence/returns` | `GET /api/v1/returns`, `GET /api/v1/returns/{return_id}`<br>`POST /api/v1/returns` *(records `excess_stock`/`defective`/`damaged`/`other`, disposition `restock`/`damaged`, over-return cap against fulfilled qty, `demand_adjustments` if `excess_stock`)*<br>`GET /api/v1/intelligence/returns/summary` *(health, net vs. gross returns & cancellations)* | `returns`, `return_items`, `inventory_movements`, `demand_adjustments` | Strictly blocks over-returns; defective returns restock/shrink-log stock without corrupting net demand (`DDR-06`) |
| **M17 Billing & Finance** | `/api/v1/invoices`, `/api/v1/payments`, `/api/v1/credit-notes`, `/api/v1/refunds`, `/api/v1/finance` | See detailed breakdown in [Section 7.3](#73-finance-apis) | `invoices`, `invoice_items`, `payments`, `credit_notes`, `refunds` | `INR` default, frozen `tax_rate` & `billing_snapshot` (`DDR-04`), `'fully_credited'` vs. `'refunded'` state separation |
| **M18 Shipping & Delivery** | `/api/v1/shipping` | See detailed breakdown in [Section 7.2](#72-order-fulfilment-and-shipping-apis) | `shipments`, `shipment_items`, `packing_slips`, `shipment_events` | Internal pick lists, packing slips, routing labels & split shipments only; external carrier APIs **excluded (`EXCL-02`)** |

#### Supporting Capabilities (`SYS-01`–`SYS-04`)

| Capability | Planned Domain / Endpoints (`PLANNED`) | Purpose & Constraints |
| :--- | :--- | :--- |
| **SYS-01 Workspace Selection** | `GET /api/v1/workspaces` ***[Illustrative]*** *(static UI metadata only, if served)* | Lists the 4 UI operational contexts (`Store Manager (Admin)`, `Inventory Staff`, `Purchase Manager`, `Finance Staff`). Zero login/passwords/JWT/RBAC (`Section 1.4`). |
| **SYS-02 Centralized History & Audit** | `GET /api/v1/history`, `GET /api/v1/history/{audit_id}` ***[Illustrative]***, `GET/POST /api/v1/history/outbox` ***[Illustrative]*** | See [Section 7.4](#74-audit-and-alerts-apis). Searchable `audit_logs` + Tier 2 `audit_outbox` reconciliation. Separate from `inventory_movements`. |
| **SYS-03 Smart Alerts** | `GET /api/v1/alerts`, `PATCH /api/v1/alerts/{alert_id}/acknowledge`, `PATCH /api/v1/alerts/{alert_id}/resolve` | See [Section 7.4](#74-audit-and-alerts-apis). Duplicate-suppressed unresolved notifications (`low_stock`, `anomaly_spike`, `po_escalation`, `audit_failure`). |
| **SYS-04 Reports & Export** | `GET /api/v1/reports` ***[Illustrative]*** *(catalog)*, `POST /api/v1/reports/preview` ***[Illustrative]***, `POST /api/v1/reports/export` ***[Illustrative]*** | Formula-neutralized CSV (`=`, `+`, `-`, `@`, tab, CR escaped) and JSON exports. Always emits a `REPORT_EXPORTED` audit entry. |

---

### 7.1 Procurement and Approval APIs

Designed around **`DDR-01`**, **`DDR-02`**, **`DDR-07`**, and **`DDR-09`** (`purchase_orders`, `purchase_order_items`, `purchase_order_approvals`, `purchase_order_receipts`, `purchase_order_receipt_items`):

1. **Replenishment Simulation (`M11` — Stateless):**
   - `POST /api/v1/simulator/calculate` *(Blueprint)* — Evaluates "what-if" safety factors and lead-time assumptions without creating MySQL records or modifying `inventory`.
   - `POST /api/v1/simulator/draft-po` *(Blueprint)* — Converts approved simulation lines (using explicit or mapped `supplier_products` pricing/MOQ/lead times) into an editable `draft` Purchase Order.
2. **Purchase Order Drafting & Editing:**
   - `POST /api/v1/purchase-orders` — Creates a `draft` PO for a supplier (optionally flagged `split_review_flagged` when another open PO exists for the same supplier within the rolling split-detection window).
   - `PUT /api/v1/purchase-orders/{po_id}` — Edits lines, supplier, or unit costs while `draft` or previously `approved` prior to receipt; **any mutation to supplier, quantities, or prices on a previously approved PO automatically invalidates prior approval** (`approval_revoked`), forces re-submission, and emits a **Tier 1** audit record.
3. **Submission & Dual-Control Approval (`DDR-09`):**
   - `POST /api/v1/purchase-orders/{po_id}/submit` — Moves `draft` $\rightarrow$ `pending_approval` and evaluates escalation rules (`total_cost > procurement_tier1_limit`, `split_review_flagged`, active high anomaly event, or supplier price spike).
   - `POST /api/v1/purchase-orders/{po_id}/approve` — Records an explicit approval event in `purchase_order_approvals`:
     - **Tier 1 Routine Approval (`Purchase Manager` workspace, non-escalated & `<= limit`):** Transitions to `approved` and automatically emits a routine oversight digest alert for `Store Manager (Admin)`.
     - **Tier 2 / Escalated Approval:** Blocked with `409 Conflict` / escalation guard unless executed from `Store Manager (Admin)` workspace with reason logging; enforces **`DDR-02`** so **only `approved` and `partially_received` PO outstanding quantities count toward `Incoming Stock`**.
   - `POST /api/v1/purchase-orders/{po_id}/reject` — Transitions to `rejected` and retains `review_notes` permanently (`audit_logs` + `purchase_order_approvals`; rejected POs are never deleted).
4. **Goods Receipt & Partial Receipt (`DDR-02`):**
   - `POST /api/v1/purchase-orders/{po_id}/receive` — Accepts line receipts (`received_now > 0`, capped `<= ordered_quantity - received_quantity`), writes immutable `purchase_order_receipts` + `purchase_order_receipt_items` (`idempotency_key` deduplicated), increments `inventory.current_quantity` (`SELECT ... FOR UPDATE`), writes `inventory_movements` (`movement_type='purchase_receipt'`), and transitions PO status (`partially_received` $\rightarrow$ `received`).
   - `PUT /api/v1/settings/procurement` — Bounded adjustment of `procurement_tier1_limit` (`Store Manager (Admin)` workspace, **Tier 1** atomic audit).
   - *Explicit Exclusion:* Automatic PO transmission or supplier EDI dispatch is **excluded (`EXCL-03`)**.

---

### 7.2 Order, Fulfilment and Shipping APIs

Designed around **`DDR-03`**, **`DDR-05`**, and **`DATABASE_SCHEMA.md` v2.6–v2.8** (`orders`, `order_items`, `order_fulfillments`, `order_fulfillment_items`, `shipments`, `shipment_items`, `packing_slips`, `shipment_events`):

1. **Order Creation & Confirmation (`M05`):**
   - `POST /api/v1/orders` — Creates a `draft` order with line items (freezing `uom_code`, `base_uom_conversion_factor`, `unit_price`), customer reference, and `requested_delivery_date`. Zero stock deducted or reserved yet.
   - `PUT /api/v1/orders/{order_id}` — Edits items/notes while `draft`.
   - `POST /api/v1/orders/{order_id}/confirm` — Locks catalog `inventory` rows (`FOR UPDATE`), verifies `Available Stock = Physical - Reserved >= quantity`, allocates `Reserved Stock` (`inventory.reserved_quantity += qty`), marks order `confirmed` (recording confirmed demand in `daily_demand_observations` after UoM conversion to `base_uom`). Rejects insufficient stock with `409 Conflict`.
2. **Partial & Multi-Batch Fulfilment:**
   - `POST /api/v1/orders/{order_id}/fulfill` — Executes one fulfilment batch (`idempotency_key` mandatory; duplicate retries return `409` or prior idempotent batch without double-deducting):
     - Creates `order_fulfillments` (`fulfillment_status='fulfilled'`) and `order_fulfillment_items`.
     - Increments `order_items.fulfilled_quantity` (capped `<= quantity`).
     - Deducts `inventory.current_quantity` **and** `inventory.reserved_quantity` strictly for fulfilled batch quantities, writing `inventory_movements` (`movement_type='sale_fulfillment'`).
     - Transitions `orders.order_status` cleanly between `partially_fulfilled` and `fulfilled` (100% items fulfilled).
   - **Duplicate Billing Protection (`v2.6`):** Linked invoices enforce `UNIQUE` constraint `uq_inv_fulfillment` on `order_fulfillment_id`, preventing two invoices from billing the same fulfilment batch.
3. **Fulfilment Reversal & Order Cancellation (`v2.6`):**
   - `POST /api/v1/orders/{order_id}/fulfillments/{fulfillment_id}/reverse` ***[Illustrative]*** — Reverses an eligible fulfilment batch **only if** unbilled (no active non-voided invoice) and unshipped (`shipments` empty/cancelled): atomically sets batch status `reversed`, decrements `order_items.fulfilled_quantity`, restores `Physical` and `Reserved` stock, and appends a compensating `inventory_movements` (`fulfillment_reversal`) row.
   - `POST /api/v1/orders/{order_id}/cancel` — Transitions `draft`/`confirmed` order to `cancelled` (blocked if unreversed `fulfilled` batches or active shipments exist): releases all remaining `reserved_quantity` back to `Available Stock` and logs compensating `demand_adjustments` (`adjustment_reason='cancellation'`) for confirmed demand.
4. **Split Shipments & Delivery Tracking (`M18` — Strictly Distinct from Fulfilment):**
   - `GET /api/v1/shipping/orders`, `GET /api/v1/shipping/pick-lists` — Lists fulfilled/ready parcels and warehouse pick quantities.
   - `POST /api/v1/shipping` — Creates a shipment linked to an `order_id` (and optionally `order_fulfillment_id`/`invoice_id`) for specific `shipment_items`; supports **`1:N` split shipments** across parcels up to total fulfilled item quantities without mutating inventory again.
   - `POST /api/v1/shipping/{shipment_id}/packing-slip` & `GET /api/v1/shipping/{shipment_id}/label` — Generates printable `packing_slips` and internal dispatch routing labels (no external carrier APIs, **`EXCL-02`**).
   - `PATCH /api/v1/shipping/{shipment_id}/status` — Appends immutable `shipment_events` along valid transitions (`pending` $\rightarrow$ `picking` $\rightarrow$ `packed` $\rightarrow$ `dispatched` $\rightarrow$ `delivered`), distinguishing physical logistics delivery from inventory fulfilment.

---

### 7.3 Finance APIs

Designed around **`DDR-04`** and **`DATABASE_SCHEMA.md` v2.4–v2.8** (`invoices`, `invoice_items`, `payments`, `credit_notes`, `refunds`):

| Endpoint (`PLANNED`) | Purpose & Database Schema v2.8 Invariants |
| :--- | :--- |
| `POST /api/v1/invoices`<br>`GET /api/v1/invoices`<br>`GET /api/v1/invoices/{invoice_id}` | Issues an **immutable** accounting invoice (`INR` default `currency_code`, frozen `billing_snapshot` JSON, historical `tax_rate` & `tax_amount` computed via `DECIMAL`, nullable `order_fulfillment_id` guarded by `uq_inv_fulfillment`). Printable view only; E-Way bills **excluded (`EXCL-01`)**. |
| `POST /api/v1/invoices/{invoice_id}/payments` | Appends an immutable `payments` entry (`amount > 0`, `payment_reference`, `payment_method`), updates `invoices.amount_paid`, and recomputes `payment_status` (`unpaid` $\rightarrow$ `partially_paid` $\rightarrow$ `paid`). |
| `POST /api/v1/credit-notes`<br>`GET /api/v1/credit-notes`<br>`GET /api/v1/credit-notes/{credit_note_id}` | Issues an immutable **credit note** adjusting net receivable value (optionally referencing `return_id`), strictly capped `<= remaining_uncredited_invoice_balance`. Reduces net collectible total; if an unpaid invoice is credited to zero, `payment_status` transitions cleanly to **`fully_credited`** (never mislabeled **`refunded`**!). |
| `POST /api/v1/refunds`<br>`GET /api/v1/refunds`<br>`PATCH /api/v1/refunds/{refund_id}/settle` ***[Illustrative]***<br>`POST /api/v1/refunds/{refund_id}/cancel` ***[Illustrative]*** | Records actual cash/bank/UPI **refund payout** in `refunds` (default `refund_status = 'pending'`). Strictly distinct from `credit_notes` and **never mutates original `payments` rows**. Capped simultaneously by **(a)** remaining refundable balance on its linked `credit_note_id` AND **(b)** total settled `payments` net of pending/completed refunds (`pending` refunds actively reserve entitlement to prevent duplicate payout initiation). Only `pending`/`failed` refunds may be cancelled before settlement. |
| `GET /api/v1/finance/reconciliation` | Summarizes `gross_invoiced`, `total_paid`, `total_credited`, `total_refunded_completed`, `pending_refund_reserved`, `net_collectible_balance`, and `payment_status` per invoice. |

---

### 7.4 Audit and Alerts APIs

Designed around **`DDR-08`**, **`DDR-10`**, and **`DATABASE_SCHEMA.md` v2.8**:

1. **Anomaly Events (`M15` — `anomaly_events`):**
   - `GET /api/v1/intelligence/anomalies` & `POST /api/v1/intelligence/anomalies/scan` ***[Illustrative]*** evaluate demand spikes/dips and return surges (preserving zero-variance `std == 0` guards) into append-only evidence rows.
2. **Smart Alerts (`SYS-03` — `alerts`):**
   - `GET /api/v1/alerts`, `PATCH /api/v1/alerts/{alert_id}/acknowledge`, `PATCH /api/v1/alerts/{alert_id}/resolve` manage operator action queues with a database uniqueness key suppressing duplicate unresolved alerts for the same `(product_id, source_module, anomaly_event_id)` signature.
3. **Centralized Audit Logs (`SYS-02` — `audit_logs` & `audit_outbox`, `DDR-10`):**
   - `GET /api/v1/history` queries immutable `audit_logs` by `module`, `action`, `selected_workspace`, `outcome`, `correlation_id`, and UTC timestamp range (application DB account lacks `UPDATE`/`DELETE` privileges).
   - **Tier 1 Fail-Closed Atomic Audit:** Order confirmation/fulfilment/reversal/cancellation, stock adjustments, `operational_settings` edits, PO submissions/approvals/rejections/receipts, invoices, payments, credit notes, refunds, returns, lifecycle `Discontinued` transitions, and UoM rollovers write `audit_logs` inside the **same MySQL transaction** — if the audit insert fails, the business transaction rolls back completely and alerts administrators.
   - **Tier 2 Resilient Non-Blocking Audit:** Read telemetry, report exports, forecast requests, and non-critical informational events write to `audit_outbox` on transient failure (retried idempotently via unique `idempotency_key` up to `dead_letter` status without blocking business continuity). `GET /api/v1/history/outbox` & `POST /api/v1/history/outbox/{id}/retry` ***[Illustrative]*** support operational drain/inspection.
4. **Bounded Configuration (`operational_settings`):**
   - Bounded configuration endpoints (`PUT /api/v1/settings/procurement`, `/settings/lifecycle`, `/settings/anomalies`, plus `POST .../reset` ***[Illustrative]***) validate `min_bound <= value <= max_bound` and require **Tier 1** atomic audit logging.

---

### 7.5 UoM API Planning

Designed around **`DDR-06`** and **`DATABASE_SCHEMA.md` v2.8** (`uom_conversions`, Section 6.6 Immediate Rollover Integrity):

> [!WARNING]
> **Zero UoM Management Endpoints Exist Today (`PLANNED` Only).** No `/uom-conversions` route exists in `backend/app/`.

When implemented under `M01 Product Management` (proposed path `GET / POST /api/v1/products/{product_id}/uom-conversions` ***[Illustrative]***), the API **must** enforce every v2.8 immediate-rollover invariant:

1. **Strictly Immediate Operational Rollover:** Operational UoM changes take effect immediately at transaction execution time (`tx_now = NOW(6)` captured once on the MySQL database server inside `with session.begin():`).
2. **Future-Dated and Backdated Rollovers Prohibited:** Omitting caller-controlled effective timestamp fields entirely from the planned request schema is preferred; if a caller supplies an unsupported effective timestamp (such as `effective_from` or `effective_to`), the API **must reject the request with `HTTP 422 Unprocessable Content`** (caller timestamps must never override `tx_now`).
3. **Half-Open Interval Closure & Single Active Factor Guarantee:** Within one locked transaction (`SELECT ... FOR UPDATE` on existing active conversion for `(product_id, uom_code)`):
   - Previous active row closes at exact database timestamp `effective_to = tx_now` and sets `is_active = FALSE`.
   - New row opens at exact database timestamp `[tx_now, NULL)` with `is_active = TRUE` and `conversion_to_base > 0`.
   - Database `VIRTUAL` generated columns `active_product_id` and `active_uom_code` with unique constraint `uq_uom_one_active (active_product_id, active_uom_code)` guarantee at most one active conversion per `(product_id, uom_code)`.
4. **Frozen Historical Snapshots Preserved:** Existing `order_items.base_uom_conversion_factor` and `demand_adjustments.base_uom_quantity_delta` retain their original point-in-time conversion snapshots and are **never** recalculated by subsequent UoM rollovers.

---

### 7.6 Explicitly Excluded Scope (`EXCL-01`–`EXCL-08` — `EXCLUDED`)

The following capabilities **must never** be implemented or documented as planned endpoints:

| Exclusion ID | Excluded Capability | Boundary Reason |
| :--- | :--- | :--- |
| **`EXCL-01`** | Government E-Way Bill integration | Regulatory tax portal outside academic/internal retail scope |
| **`EXCL-02`** | External shipping carrier APIs (FedEx, UPS, DHL, Shiprocket) | Internal pick lists, packing slips, and routing labels (`M18`) only |
| **`EXCL-03`** | Automatic supplier PO dispatch / EDI / automated emails | Mandatory human approval and manual PO execution (`DDR-09`) |
| **`EXCL-04`** | Autonomous dynamic pricing or automated markdown engines | Read-only price/revenue analytics (`M13`) only |
| **`EXCL-05`** | Conversational AI chatbot or natural-language POS | Form/table/chart workflows within Two-Page UI only |
| **`EXCL-06`** | Market basket / association rule mining (`apriori`) | Focused SKU demand forecasting only |
| **`EXCL-07`** | Complex multi-supplier linear optimization solvers | Direct supplier mapping + transparent simulator (`M11`, `DDR-07`) only |
| **`EXCL-08`** | Automatic customer address scraping | Manual customer intake (`M03`) only |

---

## Section 8 — Request and Response Conventions

| Convention Area | Verified Current Implementation (`main`) | Planned Standard (`PLANNED` Blueprint v2.2 / Schema v2.8) |
| :--- | :--- | :--- |
| **Content Type** | `application/json; charset=utf-8` | `application/json; charset=utf-8` (plus `text/csv` download for `SYS-04` exports) |
| **Schema Validation** | Pydantic v2 (`2.14.3`): `min_length=1` after stripping whitespace, numeric range bounds (`ge`, `le`), finite float validation (`math.isfinite`), horizon whitelist validation | Same Pydantic v2 strict validation + `Decimal` range/scale enforcement |
| **Query & Path Params** | Zero query/path parameters currently implemented on live routes | Resource IDs in path (`/{id}`), pagination (`page=1`, `page_size=25`, max `100`), `sort_by`, `sort_dir` |
| **Pagination Envelope** | **Not implemented today** (all live routes return single objects or dictionaries) | Planned standard: `{"items": [...], "total": int, "page": int, "page_size": int, "total_pages": int}` |
| **Date / Time Format** | `datetime.now(timezone.utc).isoformat()` (e.g., `"2026-11-26T17:49:26.792577+00:00"`) and `"YYYY-MM-DD"` calendar `observation_date` | ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ` or `+00:00`) & `YYYY-MM-DD`; UoM `NOW(6)` microsecond server time |
| **Numeric Precision** | Python `float` rounded to `4` decimals (`predictions`, `daily_demand_rate`) or `2` decimals (`inventory/recommend` totals & `wape`) | **`DECIMAL(10,2)` / `DECIMAL(12,2)` / `DECIMAL(12,6)` (UoM)** via Python `decimal.Decimal` (`ROUND_HALF_UP`); zero `FLOAT`/`DOUBLE` for `INR` money |
| **Idempotency Keys** | **Not implemented today** | Mandatory for planned `POST /orders/{id}/fulfill`, `POST /purchase-orders/{id}/receive`, and Tier 2 `audit_outbox` entries |
| **Workspace & Correlation Headers** | **Not read or propagated by middleware today** | Optional `X-NEXORA-Workspace` (`Store Manager (Admin)`, `Inventory Staff`, `Purchase Manager`, `Finance Staff`) and `X-Correlation-ID` (auto-generated UUID/prefixed ID if omitted) |

---

## Section 9 — HTTP Status Codes and Error Handling

### 9.1 Verified Status Codes on `main`

| Status Code | Trigger on Live Routes | Verified Response Format (`main`) |
| :--- | :--- | :--- |
| **`200 OK`** | Successful GET metadata/probes, `POST /forecast*`, `POST /experimental/forecast*`, `POST /inventory/recommend` | Schema-specific JSON (`ForecastResponse`, `InventoryRecommendationResponse`, `ReadinessResponse`, `Dict`) |
| **`404 Not Found`** | Unknown `stock_code` in `HistoricalDataService` (e.g., `NON_EXISTENT_SKU_99999`) | `{"detail": "Product SKU '...' was not found..."}` |
| **`422 Unprocessable Content`** | *(1)* Pydantic schema error (`current_stock < 0`, invalid horizon, blank SKU, NaN/Inf, partial manual lags)<br>*(2)* Business rule error: `InsufficientHistoryError` (`< 29` calendar days) | *(1)* Standard FastAPI list `{"detail": [{"type": ..., "loc": [...], "msg": ..., "input": ...}]}`<br>*(2)* Custom string `{"detail": "Insufficient historical sales data for SKU '...' (...)"}` |
| **`500 Internal Server Error`** | Unhandled service exceptions or missing comparative JSON during `/evaluation-comparison` / `/store-wide` non-FileNotFound errors | FastAPI HTTPException `{"detail": "..."}` |
| **`503 Service Unavailable`** | *(1)* Production models/historical CSV unready on `/ready`, `/api/v1/forecast/*`, `/api/v1/inventory/recommend`<br>*(2)* Experimental models/PIT price unready on `/api/v1/experimental/*`<br>*(3)* Missing `store-wide` JSON file | On `GET /ready` & `GET /api/v1/experimental/ready`: JSON readiness payload (`status: "not_ready"`, `error` populated). On operational `POST`/`GET` routes: `{"detail": "..."}`. |

*(Implementation Note: Live test runs emit a benign `StarletteDeprecationWarning` because `routes/forecast.py` and `routes/experimental_forecast.py` reference `status.HTTP_422_UNPROCESSABLE_ENTITY`; FastAPI emits HTTP `422` cleanly in all cases.)*

### 9.2 Planned Operational Error Contract (`PLANNED` — Blueprint v2.2 Section 13.1)

Planned Phase 2–6 operational routers will add `201 Created` (entity creation), `400 Bad Request` (non-schema malformed query/parameter), and `409 Conflict` (duplicate `stock_code`, invalid state transition, insufficient available stock, duplicate `idempotency_key`, over-return, or financial immutability violation) alongside a unified error envelope:

```json
{
  "status": "error",
  "error_code": "INSUFFICIENT_STOCK",
  "message": "Cannot fulfill order: SKU '85123A' has 5 available units, 12 requested.",
  "details": { "stock_code": "85123A", "available": 5, "requested": 12 },
  "correlation_id": "req-9f4c12a8",
  "timestamp": "2026-11-26T17:49:27+00:00"
}
```

*(Note: Unified `error_code` handling is **not** implemented on `main` today; existing Phase 1 routes return FastAPI's standard `{"detail": ...}` structure.)*

---

## Section 10 — API Testing and Demonstration

### 10.1 Automated Backend Verification (`pytest`)

Run inside the mandatory virtual environment (`pytest.ini` configures `pythonpath = backend` and `timeout = 30`):

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/ -q --tb=short
```

- **Latest Verified Result on `HEAD` `e74ae89`:** **`168 passed in 50.62s`** across all `13` test suites (`0` failures, `0` skipped):

| Category | Test File | Collected Cases | Scope Covered |
| :--- | :--- | :---: | :--- |
| **API General** | [`test_main.py`](../backend/tests/test_main.py) | `3` | Root `/`, `/health`, `/api/v1/forecast/horizons` |
| **API Readiness** | [`test_startup_readiness.py`](../backend/tests/test_startup_readiness.py) | `14` | Startup ML/CSV loading, `/health` `200`, `/ready` `200`/`503`, `503` prediction guard |
| **API Forecast** | [`test_forecast_api.py`](../backend/tests/test_forecast_api.py) | `16` | Horizons, metrics, info, multi/single/legacy prediction, flat features, validation (`422`) |
| **API Historical** | [`test_historical_forecast.py`](../backend/tests/test_historical_forecast.py) | `10` | SKU-only CSV auto-features, `/forecast/` vs `/forecast/predict`, `404` unknown SKU, `422` `< 29` days |
| **API Inventory** | [`test_inventory_recommend.py`](../backend/tests/test_inventory_recommend.py) | `13` | `CRITICAL`/`ELEVATED`/`SAFE` stock cases, lead-time sensitivity, `404`/`422`, monotonicity, `use_experimental=true` |
| **Experimental + PIT** | [`test_experimental_forecast.py`](../backend/tests/test_experimental_forecast.py) | `50` | All `/api/v1/experimental/*` routes, `/evaluation-comparison`, `/store-wide`, PIT pricing leakage/cache, failure isolation |
| **ML Pipeline & Leakage** | `test_preprocessing.py`, `test_feature_engineering.py`, `test_ml_features.py`, `test_leakage_corrections.py`, `test_model_training.py`, `test_model_evaluation.py`, `test_model_selection_task12.py` | `62` | 4-stream separation, zero-padding, causal shifts, purge/embargo CV, Task 12 selection (`168` total with above) |

### 10.2 Manual Postman Collections & Demonstration Guides

Automated `pytest` tests invoke ASGI `TestClient` deterministically with strict invariance and error-path assertions for CI/regression safety, whereas Postman collections support live interactive HTTP / `uvicorn` walkthroughs (such as localhost or ngrok academic demonstrations).

| Asset | Relative Path | Count / Scope | Verified Contents |
| :--- | :--- | :---: | :--- |
| **Academic Baseline Collection** | [`docs/postman/NEXORA_Academic_API.postman_collection.json`](postman/NEXORA_Academic_API.postman_collection.json) | `6` requests | `/health`, `/ready`, `/forecast/horizons`, valid `85123A`, `404` `NON_EXISTENT_SKU_99999`, `422` `21777` |
| **Complete Demonstration Suite** | [`docs/postman/NEXORA_Complete_Demonstration.postman_collection.json`](postman/NEXORA_Complete_Demonstration.postman_collection.json) | `19` requests (`12` root + `7` `Inventory Purchase Recommendations`) | `/health`, `/ready`, `/api/v1/ready`, forecast success/404/422, invalid `404` path, plus 7 `POST /api/v1/inventory/recommend` scenarios (low/sufficient/zero stock, lead-time 14d, negative stock `422`, `404`, `422` insufficient history) |
| **Experimental Task 12 Suite** | [`docs/postman/NEXORA_Experimental_API.postman_collection.json`](postman/NEXORA_Experimental_API.postman_collection.json) | `12` requests | `/health`, `/ready`, `/api/v1/experimental/ready`, horizons/metrics/info, auto & selective `[7, 30]` forecasts, manual 20-feature forecast, `404`, `422` SKU `20877`, and baseline `/api/v1/forecast/predict` comparison |
| **YAML Export Folder** | [`docs/postman/NEXORA Academic Deployment API/`](postman/NEXORA%20Academic%20Deployment%20API/.resources/definition.yaml) | `18` `.request.yaml` + `6` `.example.yaml` | Standalone YAML requests & saved HTTP examples (originally targeting demo ngrok host) |
| **Written Walkthrough Guides** | [`DEMONSTRATION_GUIDE.md`](postman/DEMONSTRATION_GUIDE.md), [`EXPERIMENTAL_DEMONSTRATION_GUIDE.md`](postman/EXPERIMENTAL_DEMONSTRATION_GUIDE.md), [`NEXORA_Postman_Demonstration_Guide.md`](postman/NEXORA_Postman_Demonstration_Guide.md) | `3` guides | Step-by-step live demo scripts and talking points |

> [!NOTE]
> **Postman Guide Sample Drift Observed:** Historical sample snippets in [`NEXORA_Postman_Demonstration_Guide.md`](postman/NEXORA_Postman_Demonstration_Guide.md) show minor illustrative drift vs. live FastAPI schemas (for example, `supported_horizons` vs. live `supported_horizons_days`, and `"ceil(...)"` vs. live 2-decimal `round(...)` in `inventory_service.py`), while the `.example.yaml` response for SKU `85123A` lists `history_days: 374` from the 1-year snapshot vs. live `history_days: 739` on the recovered 2-year dataset. **Always treat the live Pydantic schemas and test suite in `backend/app/` as authoritative.**

---

## Section 11 — Implementation Roadmap and Limitations

This document intentionally avoids maintaining a duplicate feature matrix; the single source of truth for per-feature completion across all `277` tracked capabilities is [`docs/FEATURES_STATUS.md`](FEATURES_STATUS.md) *(Version 2.3)*:

- **Implemented (`22` features in `FEATURES_STATUS.md` v2.3):** Health/readiness probes, historical UCI 4-stream dataset engineering, leakage-free feature matrix, multi-horizon ML forecasting (`D_7`/`D_15`/`D_30`/`D_90`), comparative macro evaluation, Task 12 experimental endpoints, and 168 passing automated `pytest` assertions.
- **Partially Implemented (`8` features):** `POST /api/v1/inventory/recommend` stateless Phase 1 replenishment prototype (lacks MySQL stock/PO integration and `DDR-01` supplier lead-time rules) and initial frontend Phase 1 demo shell (`frontend/src/App.tsx`).
- **Planned (`247` features):** Phase 2 MySQL + Foundation + Inventory + Audit (`DDR-10`), Phase 3 Two-Page React UI + 4 Workspaces (`/` & `/dashboard`), Phase 4 Predictive Planner (`DDR-01`–`03`) + BI + Lifecycle/Anomalies (`DDR-08`), Phase 5 Procurement (`DDR-09`) + Returns (`DDR-06`) + Billing (`DDR-04`, `refunds` v2.8) + Shipping (`DDR-05`) + Reports, and Phase 6 E2E QA (`Sections 17.2` of Technical Blueprint v2.2).
- **Excluded (`EXCL-01`–`EXCL-08`):** E-Way bills, external carriers, auto PO dispatch, autonomous price discounts, chatbots, market basket analysis, multi-supplier solvers, address scraping.

---

## Section 12 — API Change and Version History

| Version | Date | Authoritative Baseline | Summary of Changes |
| :--- | :--- | :--- | :--- |
| **1.0** | November 2026 | Early Phase 1 Draft | Initial FastAPI outline featuring legacy 6-role RBAC, planned `/api/v1/auth/login`, `/logout`, `/me` endpoints, `JWT` + `Passlib` dependencies, and early draft CRUD route lists without experimental/Task 12 routes or prototype inventory documentation. |
| **2.0** | 26 November 2026 | Technical Blueprint v2.2, `FEATURES_STATUS.md` v2.3, Workflow Guide v1.0, `DATABASE_SCHEMA.md` v2.8 | Full consolidation and architectural realignment: *(1)* documented all `20` live route handlers (general probes, production baseline forecasting, Task 12 experimental routes, comparative/store-wide routes, partial stateless `POST /api/v1/inventory/recommend`) with verbatim live JSON payloads and test coverage; *(2)* explicitly removed obsolete `/api/v1/auth/*`, JWT, Passlib, server-side RBAC, and 6 legacy employee roles; *(3)* documented Two-Page / 4-Workspace provenance (`X-NEXORA-Workspace`), `DDR-01`–`DDR-10`, immediate-only UoM rollover (`tx_now = NOW(6)`), `refunds` vs. `credit_notes` (`'fully_credited'`), fulfilment batch reversal, and all `18` modules (`M01`–`M18`) + `4` supporting capabilities (`SYS-01`–`SYS-04`) cleanly as **`PLANNED`**; *(4)* enumerated `EXCL-01`–`EXCL-08` and reconciled Postman collections & `168` `pytest` tests. |

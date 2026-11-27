# NEXORA — Project Overview

- **Project:** NEXORA – AI-Powered Retail Management & Intelligence System
- **Document Version:** 2.0 — Approved Architecture & Implementation Reality Alignment
- **Last Updated:** 26 November 2026
- **Repository Baseline:** `Lalith-Manohar/LLM-Project1` (Branch `main`, commit `3844cd2b32faed98914a04bf85448007a6bd5cac`)

> [!IMPORTANT]
> **Purpose & Scope Distinction:** This document is the concise architectural and implementation entry point for **NEXORA**. Detailed specifications live in the authoritative documents listed in [Section 11](#11-documentation-references-and-version-history). All `18` core operational modules and `4` supporting capabilities are **designed** target architecture, while verified implementation on `main` currently spans **Phase 1 ML demand pipelines, production and experimental forecast inference endpoints, a stateless replenishment recommendation prototype, and a Phase 1 single-screen React forecasting demo** — with **zero live MySQL tables, ORM models, or Alembic migrations** implemented yet.

---

## 1. Project Identity, Vision & Objectives

**NEXORA – AI-Powered Retail Management & Intelligence System** is a modular monolithic retail operations and predictive decision-support platform designed to unify store catalog, inventory, procurement, billing, return, shipping, and analytics workflows with machine-learning-driven multi-horizon demand forecasting (**7, 15, 30, and 90 days**).

Rather than functioning as an isolated ML notebook or a standalone CRUD tracker without demand intelligence, NEXORA bridges empirical historical demand baselines with structured relational retail transactions and rule-based stock-risk indicators (`CRITICAL`, `ELEVATED`, `SAFE`).

### Core Engineering Objectives
1. **Leakage-Free Multi-Horizon ML Forecasting:** Clean multi-year historical retail transactions into separate demand streams and generate non-negative predictions across `7`, `15`, `30`, and `90` days without temporal target leakage.
2. **Unified Operational Retail Foundation:** Manage products, unit-of-measure (UoM) conversions, suppliers, supplier-product terms, customers, confirmed orders, and realized sales cleanly inside MySQL 8.x (InnoDB).
3. **Stock Accountability & Predictive Replenishment:** Maintain five distinct stock metrics (`Physical`, `Reserved`, `Available`, `Incoming`, `Projected Available`), enforce immutable movement ledgers, and feed ML forecasts plus supplier lead times into replenishment risk scoring.
4. **Human-Governed Purchasing & Financial Integrity:** Support replenishment simulations, tiered dual-control Purchase Order (PO) approvals, goods receipts, return disposition, `INR` invoicing, credit notes, refund payouts, and internal dispatch preparation.
5. **Two-Page Stakeholder Workspace UI:** Deliver focused operational navigation across four stakeholder workspaces inside a single unified dashboard without password login or server-enforced RBAC complexity.
6. **Centralized Governance & Historical Traceability:** Record mutations, correlation IDs, workspace provenance, alerts, and formula-safe exports reliably across server restarts.

---

## 2. Project Scope, Boundaries & Exclusions

NEXORA enforces explicit operational boundaries to keep core retail workflows deterministic, auditable, and aligned with academic engineering standards:

- **Historical Dataset vs. Operational Persistence:** Historical demand baselines come from the **UCI Online Retail II** transaction dataset; live stock, suppliers, customers, orders, POs, invoices, shipments, and audit records are designed to live natively in MySQL.
- **Human-in-the-Loop Decisions:** Purchase simulations and risk classifications inform human operators; every PO and lifecycle `Discontinued` decision requires explicit human action.
- **Manual Customer Intake & Internal Logistics Only:** Customer billing/shipping details are entered manually through operational workflows, and shipping tools generate internal pick lists, packing slips, and dispatch labels only.

### Explicitly Excluded Capabilities (`EXCL-01`–`EXCL-08`)

Per [`Technical Blueprint v2.2`](NEXORA%20%E2%80%94%20Technical%20Blueprint%20v1.0.md), the following capabilities are **permanently excluded** (`EXCLUDED`) from approved scope:

| ID | Excluded Capability | Operational Boundary Rule |
| :---: | :--- | :--- |
| `EXCL-01` | **Government E-Way Bill Generation** | Statutory tax portal integration lies outside approved project scope. |
| `EXCL-02` | **External Shipping Carrier APIs** (FedEx, UPS, DHL, etc.) | Internal warehouse pick lists, packing slips, and routing labels (`M18`) only. |
| `EXCL-03` | **Automatic Supplier Order Dispatch** | Automated vendor emails or API ordering prohibited; POs require human approval (`DDR-09`). |
| `EXCL-04` | **Autonomous Price Markdowns** | Price analytics (`M13`) provide observational insight without automated price cuts. |
| `EXCL-05` | **Conversational AI Chatbot or NL POS** | Structured tabular interfaces, charts, and deterministic formulas only. |
| `EXCL-06` | **Market Basket / Purchase Affinity Mining** | Outside multi-horizon SKU demand forecasting and retail ERP scope. |
| `EXCL-07` | **Complex Multi-Supplier Optimization Solvers** | Uses direct supplier-product terms and rule-based simulation (`M11`, `DDR-07`). |
| `EXCL-08` | **Automated Customer-Address Scraping** | Customer records originate solely through manual `M03` intake forms. |

---

## 3. Approved Application Architecture

*(Target application design defined in [`Technical Blueprint v2.2`](NEXORA%20%E2%80%94%20Technical%20Blueprint%20v1.0.md) and [`Workflow Guide v1.0`](NEXORA%20%E2%80%94%20Application%20Functionality%20%26%20System%20Workflow%20Guide.md).)*

### 3.1 Strict Two-Page Web Structure (`PLANNED`)
NEXORA organizes the entire target web experience into **two primary application pages** (with **no** separate pages or dashboards per stakeholder):

- **Page 1 (`/`): Stakeholder Workspace Selection** — Displays the exact heading **`Welcome to NEXORA — Select Your Workspace`** and four workspace selection cards with no login form.
- **Page 2 (`/dashboard`): Unified Retail Management Dashboard** — Hosts all operational and analytical tabs, KPIs, Chart.js views, modals, in-header **Workspace Switcher**, and **Smart Alerts** drawer in one cohesive layout.

### 3.2 Four Stakeholder Workspaces (UI Contexts — No Login or RBAC)
Page 1 and the Page 2 switcher scope navigation across **four stakeholder workspaces**:

1. **Store Manager (Admin)**
2. **Inventory Staff**
3. **Purchase Manager**
4. **Finance Staff**

> [!NOTE]
> **Explicit Non-Authentication Boundary:** Workspace selection controls UI navigation focus and supplies `X-NEXORA-Workspace` provenance metadata for operational records and audit logs. It is **not** user login, identity verification, password authentication, JWT session management, or server-enforced RBAC, and must never be presented as a security access-control boundary.

### 3.3 Eighteen Core Modules (`M01`–`M18`, All `PLANNED` Except Partial `M12` & `M14`)

| Group | Core Module ID & Name | Concise Scope |
| :--- | :--- | :--- |
| **Group 1 — Retail Foundation** | **M01 Product Management** | Master SKU catalog, `INR` prices, categories, UoM conversions (`DDR-06`), soft status toggles |
| **Group 1 — Retail Foundation** | **M02 Supplier Management** | Vendor profiles, effective-dated `supplier_products` terms (`DDR-07`), hierarchical lead times |
| **Group 1 — Retail Foundation** | **M03 Customer Management** | Manual customer intake, billing/shipping contacts, active status control |
| **Group 1 — Retail Foundation** | **M04 Sales Management** | Historical UCI vs. operational sales streams (`transactions`), traceable compensating reversals |
| **Group 1 — Retail Foundation** | **M05 Order Management** | Order drafting, stock-reserving confirmation, idempotent partial fulfilment (`DDR-05`), cancellation |
| **Group 2 — Business Intelligence** | **M06 Business Intelligence** | Revenue/volume KPIs, time-series trends, SKU rankings, country analysis (UCI `GBP` vs. live `INR`) |
| **Group 2 — Business Intelligence** | **M07 Seasonal Demand Calendar** | Monthly and day-of-week clean demand intensity calendars and recurring peak views |
| **Group 2 — Business Intelligence** | **M08 Product Lifecycle Intelligence** | Hysteresis-governed SKU stage classification (`Introduction`–`Discontinued` per `DDR-08`) |
| **Group 3 — Inventory & Procurement** | **M09 Inventory Control** | Live five-bucket stock registry, locked manual adjustments (`FOR UPDATE`), safety thresholds |
| **Group 3 — Inventory & Procurement** | **M10 Stock Movement Tracking** | Immutable append-only `inventory_movements` quantity ledger distinct from stock balances & audits |
| **Group 3 — Inventory & Procurement** | **M11 Purchase Planning Simulator** | "What-if" replenishment scratchpad, PO drafting, `DDR-09` tiered approvals, partial/full receipts |
| **Group 4 — AI & Predictive Intelligence** | **M12 Demand Forecasting** | Multi-horizon (`7/15/30/90`d) ML pipelines, CSV inference (`main`), and planned B2B demand ingestion |
| **Group 4 — AI & Predictive Intelligence** | **M13 Price & Revenue Intelligence** | Observational unit-price distributions and SKU revenue concentration studies (`EXCL-04` read-only) |
| **Group 4 — AI & Predictive Intelligence** | **M14 Predictive Planner** | Live MySQL stock + ML demand + supplier lead-time risk evaluation (`DDR-01`/`02`/`03`; partial prototype today) |
| **Group 4 — AI & Predictive Intelligence** | **M15 Anomaly Detection** | Hybrid statistical/rule anomaly detection (`anomaly_events`) for demand, returns, stock, and PO spikes |
| **Group 5 — Business Operations** | **M16 Return Intelligence** | Return intake (`excess_stock` vs. `defective`/`damaged`), disposition (`restock`/`damaged`), net return analytics |
| **Group 5 — Business Operations** | **M17 Billing & Finance** | Immutable `INR` invoices with frozen tax snapshots (`DDR-04`), payments, credit notes, refund payouts, reconciliation |
| **Group 5 — Business Operations** | **M18 Shipping & Delivery** | Pick lists, `1:N` split shipments (`DDR-05`), printable packing slips, internal routing labels, status log |

### 3.4 Four Supporting System Capabilities (`SYS-01`–`SYS-04`, All `PLANNED`)
Cross-cutting capabilities live in a **dedicated Group 6 supporting category** — **they are 4 supporting capabilities alongside 18 core modules, not 22 core modules**:

| Capability ID & Name | Concise Scope |
| :--- | :--- |
| **SYS-01 Workspace Selection** | Two-page workspace selector, in-header Workspace Switcher, workspace-scoped navigation & `X-NEXORA-Workspace` context |
| **SYS-02 Centralized History & Audit** | Append-only `audit_logs` (`Tier 1` fail-closed atomic commits) + `audit_outbox` (`Tier 2` resilient retry/dead-letter per `DDR-10`) |
| **SYS-03 Smart Alerts** | Actionable operational alerts (`low_stock`, anomalies, PO escalations) with duplicate unresolved-alert suppression (`DDR-08`) |
| **SYS-04 Reports & Export** | Query previews and spreadsheet-formula-safe CSV (`=`, `+`, `-`, `@`, tab, CR escaped) and JSON exports logged to audit |

---

## 4. Core Business Workflows & Operating Principles

NEXORA's operational design is governed by ten resolved Design Decisions (`DDR-01`–`DDR-10`) and [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.9 invariants:

1. **Orders vs. Realized Sales:** Confirmed customer orders (`orders`) represent demand commitments, while realized sales (`transactions`) record completed commercial revenue separately.
2. **Exact Once-Only Stock Deduction:** Inventory (`inventory.current_quantity`) is deducted **only** for actually fulfilled quantities inside locked (`FOR UPDATE`) idempotent fulfilment batches (`order_fulfillments`).
3. **Five Separate Stock Metrics (`DDR-03`):** **Physical**, **Reserved**, **Available** (`Physical - Reserved`), **Incoming**, and **Projected Available** (`Available + Incoming`) are always tracked and surfaced individually.
4. **Approved Incoming Stock Only (`DDR-02`):** Strictly `approved` and `partially_received` PO outstanding balances count as **Incoming Stock**; `draft`, `pending_approval`/`submitted`, `rejected`, `received`, and `cancelled` POs contribute `0`.
5. **Product-Specific Supplier Lead Times (`DDR-01`, `DDR-07`):** Lead-time lookup checks active `supplier_products.lead_time_days` first and falls back to `suppliers.lead_time_days`.
6. **No Invented Lead Times (`DDR-01`):** When neither mapping defines a supplier lead time, supplier lead-time risk status explicitly reports **`UNAVAILABLE`** rather than substituting arbitrary defaults.
7. **Sequential Procurement Lifecycle (`DDR-09`):** Purchase simulations (`M11`), draft POs, submitted POs, Tier 1/Store Manager approvals, and partial/full goods receipts are separated stages with post-approval edit invalidation.
8. **Partial Fulfilment & Split Shipments (`DDR-05`):** An order supports multiple fulfilment batches, eligible unbilled/unshipped fulfilment reversal, and independent `1:N` split parcel shipments without double-deducting inventory.
9. **Separated Return Disposition (`DDR-06`):** Returns track physical disposition (`restock` vs. `damaged`) alongside classification (`excess_stock` adjusts net demand in `demand_adjustments`, whereas `defective`/`damaged` leaves clean demand intact).
10. **Distinct Financial Ledgers:** Invoices, `payments`, `credit_notes`, and actual payout `refunds` are separate immutable tables; crediting an unpaid invoice yields `fully_credited` (not `refunded`), and refunds never alter original payment rows.
11. **`INR` Currency & Historical Tax Snapshots (`DDR-04`):** `INR` (`DECIMAL`) is default operational currency; centrally configured tax rates apply forward-only while issued invoices freeze historical tax snapshots.
12. **Immediate UoM Rollovers & Frozen Snapshots (`DDR-06`, Schema v2.9):** `uom_conversions` updates execute immediately using one DB transaction timestamp `tx_now = NOW(6)` across `[effective_from, effective_to)` intervals (unsupported caller timestamps are rejected with `HTTP 422`), while existing documents retain frozen conversion factors.
13. **Governed Lifecycle & Anomalies (`DDR-08`):** Threshold changes require bounded validation, cannot rewrite prior `product_lifecycle_snapshots` or `anomaly_events`, and reserve `Discontinued` for explicit manual confirmation.
14. **Audit vs. Movement vs. Transaction Separation:** Cross-module `audit_logs` track operator actions/errors and remain completely distinct from unit `inventory_movements` and commercial `transactions`.
15. **Tiered PO Approval & Audit Integrity (`DDR-09`, `DDR-10`):** Routine non-escalated POs within `Tier 1` limits approve under `Purchase Manager` with Store Manager oversight digest while escalations require `Store Manager (Admin)`; critical mutations enforce **Tier 1** atomic fail-closed audit writes while routine events use **Tier 2** `audit_outbox` retries.

---

## 5. Technology Stack (Verified Current vs. Planned Target)

| Layer | Technology | Declared Spec ([`requirements.txt`](../backend/requirements.txt) / [`package.json`](../frontend/package.json)) | Status on `main` | Role |
| :--- | :--- | :--- | :---: | :--- |
| **Backend Web Framework** | FastAPI + Uvicorn | `fastapi>=0.110.0`, `uvicorn[standard]>=0.29.0` | **Active** | REST API serving, OpenAPI `/docs`, startup lifespan loading |
| **Runtime & Validation** | Python + Pydantic v2 | Python `>=3.10` (`.venv` `3.11.9`), `pydantic>=2.6.0`, `pydantic-settings>=2.2.0` | **Active** | Schema validation, service logic, ML runtime |
| **Data & ML Engine** | Pandas, NumPy, Scikit-learn, Joblib, OpenPyXL | `pandas>=2.2.0`, `numpy>=1.26.0`, `scikit-learn>=1.4.0`, `joblib>=1.3.0`, `openpyxl>=3.1.2` | **Active** | Preprocessing, lag/rolling features, training, evaluation, inference |
| **Automated Testing** | Pytest + HTTPX | `pytest>=8.0.0`, `pytest-timeout>=2.3.0`, `httpx>=0.27.0` | **Active** | `168` automated backend & ML tests (`13` suites) |
| **Frontend Core** | React + TypeScript + Vite | `react ^18.3.1`, `typescript ^5.4.5`, `vite ^5.3.1` | **Active (Phase 1 Demo)** | Single-screen demand forecasting SPA (`frontend/src/App.tsx`) |
| **Frontend Styling & Charts** | Tailwind CSS, Chart.js, `react-chartjs-2`, React Router | Not yet in `frontend/package.json` | **Planned** | Target Two-Page Unified Dashboard visual layer |
| **Database Engine** | MySQL 8.x (InnoDB) | Configured placeholder `DB_*` keys only (`config.py`, `.env.example`) | **Planned** | Target 41-table operational ACID relational persistence |
| **ORM & Migrations** | SQLAlchemy + PyMySQL / Alembic | `sqlalchemy>=2.0.0`, `pymysql>=1.1.0` pinned (`alembic` not yet added) | **Planned (Not Integrated)** | `0` ORM model classes and `0` migrations on `main` |

*(Auth packages such as JWT, `Passlib`, and `bcrypt` are intentionally omitted and are not part of NEXORA's stack.)*

---

## 6. Implementation Status & Verified Repository Reality

Using strict repository verification standards (`FEATURES_STATUS.md` v2.3 & `API_DOCUMENTATION.md` v2.0), components are classified as **`IMPLEMENTED`**, **`PARTIALLY IMPLEMENTED`**, **`EXPERIMENTAL`**, **`PLANNED`**, or **`EXCLUDED`**:

| Component / Capability | Classification | Verified Repository Evidence (`main` at `3844cd2`) |
| :--- | :---: | :--- |
| **UCI Dataset Ingestion & 4-Stream Preprocessing** | **`IMPLEMENTED`** | `backend/ml/data/raw/online_retail_II.csv` & `.xlsx`; `data_loader.py` & `preprocessing.py` generate `clean_gross_sales.csv`, `cancellation_transactions.csv`, `return_transactions.csv`, `exceptional_transactions.csv` (`test_preprocessing.py`: `5/5`). |
| **Daily Aggregation & Leakage-Free Features** | **`IMPLEMENTED`** | `feature_engineering.py` produces continuous lifespan-padded `daily_product_demand.csv` (`4,905` SKUs, `2,287,495` rows) & `ml_feature_dataset.csv` (`test_feature_engineering.py`: `7/7`, `test_ml_features.py`: `10/10`). |
| **Multi-Horizon Training, Evaluation & Joblib Persistence** | **`IMPLEMENTED`** | `train.py`, `evaluate.py`, `predict.py` train & serialize `demand_model_{7,15,30,90}d.joblib` + `models_metadata.json` in `backend/ml/models/` (`test_model_training.py`: `10/10`, `test_model_evaluation.py`: `9/9`, `test_leakage_corrections.py`: `11/11`). |
| **FastAPI Core & Production Forecast API (`M12` Core)** | **`IMPLEMENTED`** | `main.py` (`/`, `/health`, `/ready`, hidden `/api/v1/health` & `/api/v1/ready`) + `forecast.py` (`/horizons`, `/model-metrics`, `/model-info`, `/`, `/predict`) + `historical_data_service.py` (`test_main.py`: `3/3`, `test_startup_readiness.py`: `14/14`, `test_forecast_api.py`: `16/16`, `test_historical_forecast.py`: `10/10`). |
| **Experimental Task 12 & Store-Wide Macro Forecasting** | **`EXPERIMENTAL`** | `experimental_forecast.py` (`/api/v1/experimental/ready`, `/forecast/horizons`, `/model-metrics`, `/model-info`, `/predict`, `/forecast`, hidden `/forecast/`) + `models_task12/` + `PITPriceService` + `forecast.py` (`/evaluation-comparison`, `/store-wide`) in `models_experimental/` (`test_model_selection_task12.py`: `10/10`, `test_experimental_forecast.py`: `50/50`). |
| **Stateless Inventory Replenishment Prototype (`M14` Subset)** | **`PARTIALLY IMPLEMENTED`** | `POST /api/v1/inventory/recommend` (`inventory.py`, `inventory_service.py`, `schemas/inventory.py`) runs piecewise horizon demand interpolation using **caller-supplied** `current_stock` and lead-time inputs (`test_inventory_recommend.py`: `13/13`). Not full MySQL/DDR-01–03 `M09` or `M14`. |
| **React + TypeScript Frontend (`frontend/`)** | **`PARTIALLY IMPLEMENTED`** | Phase 1 single-screen demo SPA (`package.json`, `vite.config.ts`, `src/App.tsx`, `src/services/api.ts`, `src/types/forecast.ts`) calling `GET /health` & `POST /api/v1/forecast/`. Planned Two-Page (`/` & `/dashboard`), 4-workspace Tailwind/Chart.js UI & UI tests remain **`PLANNED`**. |
| **MySQL Operational Database, ORM & Alembic** | **`PLANNED`** | `0` live MySQL tables, `0` SQLAlchemy ORM classes, `0` Alembic migrations/scripts, `0` DB connection pools in `backend/app/`; target 41-table schema defined in `DATABASE_SCHEMA.md` v2.9. |
| **Core Modules `M01`–`M11`, `M13`, `M15`–`M18` & `SYS-01`–`SYS-04`** | **`PLANNED`** | Zero retail/procurement/finance/shipping CRUD routers, audit/outbox services, alerts, or reports exist yet (`FEATURES_STATUS.md` v2.3: `22` Implemented, `8` Partially Implemented, `247` Planned across `277` tracked features; `168/168` pytest tests passing). |
| **Out-of-Scope Capabilities (`EXCL-01`–`EXCL-08`)** | **`EXCLUDED`** | E-Way bills, carrier APIs, auto PO dispatch, auto markdowns, chatbots, affinity mining, multi-supplier solvers, address scraping. |

---

## 7. ML Dataset and Intelligence Overview

- **Historical Ground Truth:** Trained on the UCI Online Retail II dataset (`2009-12-01` to `2011-12-09` recovered 2-year commercial span), separating clean gross sales (`clean_gross_sales.csv`, `1,037,089` commercial records across `4,905` SKUs) cleanly from `'C'` cancellations, non-`'C'` returns, and zero/negative-price exceptional records (`daily_product_demand.csv`: `2,287,495` lifespan-padded rows).
- **Production vs. Experimental Isolation:** Production inference (`backend/ml/models/`) uses Ridge Linear Regression (`D_7`) and Random Forest (`D_15`, `D_30`, `D_90`) with leakage-free `OneHotEncoder(max_categories=50)` + lag/rolling predictors; Task 12 experimental endpoints (`backend/ml/models_task12/`) test `ChronologicalTargetEncoder` and cutoff-aware `PITPriceService` pricing in failure-isolated endpoints.
- **Planned Operational ML Integration (`DDR-06`):** Future Phase 4 pipelines will ingest confirmed MySQL B2B demand converted to `base_uom` (`daily_demand_observations`, `demand_adjustments`, `demand_quarantine`) while preserving historical UCI baselines intact.

---

## 8. Database and Persistence Architecture

> [!WARNING]
> **Target Specification Only:** The relational schema is **not yet implemented on `main`** (`0` live MySQL tables exist). All operational routes remain **`PLANNED`**.

The approved target persistence layer in [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.9 specifies **41 MySQL 8.x InnoDB tables** across domain groups featuring:
- Strict foreign keys (`ON DELETE RESTRICT` on commercial/financial history) and pessimistic row locking (`SELECT ... FOR UPDATE`) for concurrent stock safety.
- Exact `DECIMAL(10, 2)` / `DECIMAL(12, 2)` (`INR` money) and `DECIMAL(12, 6)` (UoM factors) with zero floating-point financial columns.
- Separate immutable ledgers (`inventory_movements`, `transactions`, `invoices`, `payments`, `credit_notes`, `refunds`, `audit_logs`, `audit_outbox`), idempotency keys (`order_fulfillments`, `uq_inv_fulfillment`), and immediate `tx_now = NOW(6)` UoM rollovers.

---

## 9. API and Frontend Architecture

- **Backend REST API (`FastAPI` `/api/v1`):** Currently serves `20` verified handlers (`17` visible in `/openapi.json`, `3` hidden schema aliases) covering health/readiness probes, production forecasting, Task 12 experimental/macro forecasting, and the stateless inventory prototype ([`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) v2.0). Three Postman collections and demonstration guides reside in [`docs/postman/`](postman/NEXORA_Complete_Demonstration.postman_collection.json). Operational CRUD domains (`/products`, `/suppliers`, `/customers`, `/orders`, `/sales`, `/inventory`, `/purchase-orders`, `/simulator`, `/predictive-planner`, `/analytics/*`, `/intelligence/*`, `/returns`, `/invoices`, `/payments`, `/credit-notes`, `/refunds`, `/shipping`, `/alerts`, `/history`, `/reports`) are **`PLANNED`**.
- **Frontend SPA (`React 18 + TypeScript + Vite`):** Currently a single-screen Phase 1 forecasting demo calling `/health` and `POST /api/v1/forecast/`. Planned Phase 3 work transforms [`frontend/`](../frontend/README.md) into the strict Two-Page (`/` Workspace Selection & `/dashboard` Unified Dashboard) React + Tailwind CSS + Chart.js application injecting `X-NEXORA-Workspace` with explicit loading, empty, `422` field-validation, and confirmation modal guards.

---

## 10. Development Direction and Remaining Work

Development follows the six-phase Blueprint v2.2 sequence (see [`Technical Blueprint Section 17.2`](NEXORA%20%E2%80%94%20Technical%20Blueprint%20v1.0.md)):
1. **Phase 1 (Implemented Baseline on `main`):** ML ingestion/preprocessing/features, multi-horizon models (`7/15/30/90`d), FastAPI forecast routes, experimental Task 12 isolation, stateless inventory prototype, Phase 1 demo SPA, and `168` passing tests.
2. **Phase 2 (Next Target — MySQL Core & Operational CRUD):** Add SQLAlchemy 2.x models, Alembic migrations, Retail Foundation CRUD (`M01`–`M05`), locked Inventory/Movements (`M09`–`M10`), and `DDR-10` Tier 1/Tier 2 audit logging (`SYS-02`).
3. **Phase 3 (Two-Page React & Workspace UI):** Build Page 1 (`Welcome to NEXORA — Select Your Workspace`), Page 2 Unified Dashboard (`/dashboard`), Workspace Switcher (`SYS-01`), and Tailwind/Chart.js operational views.
4. **Phase 4 (Predictive Integration, BI & Alerts):** Connect live stock + supplier lead times (`M14` `DDR-01`–`03`), BI & Seasonality (`M06`–`M07`), Lifecycle hysteresis (`M08`), Hybrid Anomaly Detection (`M15`), Smart Alerts (`SYS-03`), and B2B demand/quarantine persistence (`DDR-06`).
5. **Phase 5 (Procurement, Returns, Billing, Shipping & Reports):** Implement Simulator & Dual-Control POs (`M11` `DDR-09`), Returns (`M16`), `INR` Billing/Credits/Refunds (`M17` `DDR-04`), Split Shipping (`M18` `DDR-05`), and formula-safe Exports (`SYS-04`).
6. **Phase 6 (End-to-End Integration & QA):** Execute full database transaction, API, UI, and 15-step connected integration verification.

---

## 11. Documentation References and Version History

### Authoritative Documentation Suite
- **Master Architecture Specification:** [`docs/NEXORA — Technical Blueprint v1.0.md`](NEXORA%20%E2%80%94%20Technical%20Blueprint%20v1.0.md) *(Version 2.2)*
- **Detailed Feature Status Registry:** [`docs/FEATURES_STATUS.md`](FEATURES_STATUS.md) *(Version 2.3)*
- **User & System Workflow Reference:** [`docs/NEXORA — Application Functionality & System Workflow Guide.md`](NEXORA%20%E2%80%94%20Application%20Functionality%20%26%20System%20Workflow%20Guide.md) *(Version 1.0)*
- **Target Relational Database Specification:** [`docs/DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) *(Version 2.9)*
- **API Reference & Implementation Matrix:** [`docs/API_DOCUMENTATION.md`](API_DOCUMENTATION.md) *(Version 2.1)*
- **ML Pipeline Notes & Evaluation Archive:** [`docs/ML_DOCUMENTATION.md`](ML_DOCUMENTATION.md), [`docs/DEVELOPMENT_LOG.md`](DEVELOPMENT_LOG.md), [`docs/TECHNICAL_DECISIONS.md`](TECHNICAL_DECISIONS.md), [`docs/KNOWN_ISSUES.md`](KNOWN_ISSUES.md)

### Revision History

| Version | Date | Authoritative Alignment | Summary of Changes |
| :---: | :--- | :--- | :--- |
| **1.0** | November 2026 | Legacy Early Draft | Initial overview assuming `13` modules, `6` employee roles, password hashing/`JWT` server-enforced RBAC, separate role dashboards, an empty `frontend/`, and unimplemented ML pipelines. |
| **2.0** | 26 November 2026 | Blueprint v2.2, `FEATURES_STATUS.md` v2.3, Workflow Guide v1.0, `DATABASE_SCHEMA.md` v2.8, `API_DOCUMENTATION.md` v2.0 | Complete architectural and reality realignment: retired the legacy 13-module/6-role/JWT/RBAC model; adopted the Two-Page (`Welcome to NEXORA — Select Your Workspace` + `/dashboard`), 4-workspace UI context design; documented the `18` core modules (`M01`–`M18`), `4` separate supporting capabilities (`SYS-01`–`SYS-04`), `15` DDR-aligned business principles, and `8` scope exclusions (`EXCL-01`–`EXCL-08`); reconciled actual `main` implementation across ML artifacts, FastAPI production/experimental routes, partial stateless `inventory/recommend`, Phase 1 demo React SPA, `168` passing `pytest` tests, and confirmed `0` live MySQL tables/ORM models/migrations. |

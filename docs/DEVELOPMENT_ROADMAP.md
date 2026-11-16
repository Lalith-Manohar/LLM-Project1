# NEXORA – Development Roadmap

## 1. Phased Development Plan (Blueprint Alignment)

The NEXORA project follows a structured 7-phase architecture:

```mermaid
flowchart LR
    P1["Phase 1: ML Engine & FastAPI (Target: 21 Nov 2026)"] --> P2["Phase 2: MySQL & Operational CRUD"]
    P2 --> P3["Phase 3: Auth & RBAC Permissions"]
    P3 --> P4["Phase 4: Core Application & React UI"]
    P4 --> P5["Phase 5: Advanced BI & Calendars"]
    P5 --> P6["Phase 6: Billing, POs & Shipping Prep"]
    P6 --> P7["Phase 7: System Integration & Defense Prep"]
```

---

## 2. Phase-by-Phase Breakdown & Tracking

### Phase 1: ML Demand Forecasting & API Serving (Target: 21 November 2026)
*Deliverable: A functioning ML prediction API delivering non-negative multi-horizon forecasts tested via Swagger UI.*
- [x] **Project Structure & Layout:** Clean separation of `backend/`, `frontend/`, `docs/`, and `backend/ml/`.
- [x] **FastAPI Foundation:** Setup root (`/`), health (`/health`), CORS, and Swagger UI (`/docs`).
- [x] **API Route & Schemas:** Defined forecast schemas in Pydantic v2.
- [x] **ML Pipeline Stubs:** Structured stubs in `backend/ml/src/` (`data_loader.py`, `preprocessing.py`, `feature_engineering.py`, `train.py`, `evaluate.py`, `predict.py`).
- [x] **Documentation Modernization:** Complete alignment of documentation with Technical Blueprint v1.0.
- [x] **UCI Dataset Acquisition:** Acquired and verified UCI Online Retail II dataset (`backend/ml/data/raw/online_retail_II.csv`, 541,910 rows).
- [x] **Dataset Ingestion & Exploratory Analysis (EDA):** Implemented in `backend/ml/src/data_loader.py`; generated `backend/ml/data/processed/eda_report.md` profiling missing values, price/quantity distributions, and cancellation vs return cross-tabulation.
- [x] **Data Cleaning & Transaction Isolation:** Implemented in `backend/ml/src/preprocessing.py`; generated `clean_gross_sales.csv` (530,105 rows), `cancellation_transactions.csv` (9,288 rows), `return_transactions.csv` (1,336 rows), and `exceptional_transactions.csv` (1,181 rows) with 100% reconciliation.
- [x] **Daily Product Aggregation:** Implemented in `backend/ml/src/feature_engineering.py`; generated `daily_product_demand.csv` (1,074,653 rows) across 3,922 SKUs with continuous calendar zero-padding within product lifespans and 100% demand preservation (5,588,377 units). Tested via `test_feature_engineering.py`.
- [x] **Leakage-Free Feature Engineering:** Implemented in `backend/ml/src/feature_engineering.py`; generated `ml_feature_dataset.csv` (1,074,653 rows, 18 columns) with calendar features, lags (1, 7, 14, 28), rolling means (7, 28), and multi-horizon forward targets ($D_7, D_{15}, D_{30}, D_{90}$) with 100% temporal isolation and incomplete-target NaN preservation. Tested via `test_ml_features.py`.
- [x] **Model Training & Comparison:** Implemented in `backend/ml/src/train.py`; benchmarked Seasonal Naïve baseline, Linear Regression, and Random Forest pipelines across all 4 planning horizons ($D_7, D_{15}, D_{30}, D_{90}$).
- [x] **Chronological Validation:** Implemented in `backend/ml/src/evaluate.py`; evaluated MAE, RMSE, and WAPE using strict chronological purge/embargo splitting ($t_{\text{train}} + H < \text{val\_start}$) with zero target-window leakage.
- [x] **Model Serialization:** Persisted fitted scikit-learn pipelines (`demand_model_7d.joblib`, `demand_model_15d.joblib`, `demand_model_30d.joblib`, `demand_model_90d.joblib`) and `models_metadata.json` to `backend/ml/models/`. Verified reload numerical equivalence and unseen SKU robustness. Tested via `test_model_training.py` and `test_model_evaluation.py`.
- [x] **Temporal Leakage Audit & Verification (Task 5.1):** Conducted rigorous audit of `TargetEncoder` and chronological holdouts. Discovered and eliminated cross-fitting target leakage by migrating to `OneHotEncoder(max_categories=50)` with Ridge regression and Random Forest. Retrained all 4 horizons, reserialized artifacts, and verified 39 tests.
- [x] **Final Model Training Verification & Artifact Integrity Audit (Task 5.2):** Certified complete elimination of TargetEncoder, verified OneHotEncoder zero-target-leakage behavior, verified purge/embargo mathematical boundaries across all 4 horizons ($D_7, D_{15}, D_{30}, D_{90}$), added adversarial future-spike test, verified all 4 serialized `.joblib` models and metadata manifest, and passed full 44-test suite.
- [x] **FastAPI Inference Wiring (Task 6):** Connected `prediction_service.py` to loaded `.joblib` estimators via lifespan startup loading, non-negativity post-processing, and unseen SKU resilience.
- [x] **Endpoint Verification (Task 6):** Verified multi-horizon forecast endpoints (`POST /api/v1/forecast/`, `POST /api/v1/forecast/predict`, `GET /horizons`, `GET /model-metrics`, `GET /model-info`) via 15 automated integration tests and live TCP HTTP requests. **Phase 1 Milestone Fully Achieved!**

---

### Phase 2: MySQL Database & Operational CRUD (Planned)
*Deliverable: Functioning product catalog and inventory management APIs backed by MySQL.*
- [ ] Configure MySQL 8.x connection, connection pooling, and Alembic migrations.
- [ ] Implement initial relational tables (`products`, `transactions`, `transaction_items`, `inventory`, `inventory_movements`).
- [ ] Build product catalog CRUD endpoints with soft-deletion support.
- [ ] Implement inventory management endpoints, tracking current stock and manual adjustments.
- [ ] Establish transactional inventory movements ledger for stock accountability.

---

### Phase 3: Login, Security & Granular RBAC (Planned)
*Deliverable: Server-enforced authentication and role-based permissions.*
- [ ] Implement `roles`, `permissions`, `role_permissions`, `users`, and `activity_logs` tables.
- [ ] Setup password hashing (bcrypt) and stateless JWT token authentication.
- [ ] Implement dependency injection for role and permission checks on FastAPI routes.
- [ ] Define backend protection across all 6 roles (`Admin`, `Executive`, `Inventory Manager`, `Warehouse Worker`, `Finance Employee`, `Sales Employee`).

---

### Phase 4: Core Application & React Dashboards (Planned)
*Deliverable: Operational React frontend with role-specific home dashboards.*
- [ ] Initialize React + TypeScript application with Tailwind CSS and Vite in `frontend/`.
- [ ] Build role-based home dashboards with dynamic views per authenticated role.
- [ ] Implement Chart.js visualizations for sales trends, volume analysis, and country breakdown.
- [ ] Build Master Stock inventory table and low-stock alert views.
- [ ] Create Predictive Planner page displaying 7, 15, 30, 90-day demand curves alongside current stock levels and risk status (`CRITICAL`, `ELEVATED`, `SAFE`).

---

### Phase 5: Advanced Intelligence & Anomaly Detection (Planned)
*Deliverable: Specialized analytical dashboards and warning systems.*
- [ ] Build Seasonal Demand Calendar displaying day-of-week and monthly sales patterns.
- [ ] Implement Product Lifecycle Intelligence categorizing SKUs into Emerging, Growing, Stable, Declining, or Inactive.
- [ ] Construct Price and Revenue Intelligence dashboard evaluating price distributions and revenue correlations.
- [ ] Implement Product Health & Return Intelligence tracking return rates and credit transactions.
- [ ] Build statistical Anomaly Detection flagging unusual volume spikes, drops, and cancellation surges.
- [ ] Build Purchase Planning Simulator enabling interactive "what-if" lead-time testing.

---

### Phase 6: Operational Modules (Purchasing, Billing, Shipping) (Planned)
*Deliverable: Paper-ready invoice generation, purchase approval workflows, and packing slips.*
- [ ] Implement Purchase Order drafting, supplier catalog management, and executive human approval workflows.
- [ ] Implement Billing module with customer intake forms, automated tax calculation, grand totals, and print-ready invoices.
- [ ] Implement Credit Note issuance linked to invoices.
- [ ] Build Shipping Preparation module generating internal packing slips and package routing labels.

---

### Phase 7: System Finalization & Acceptance Testing (Planned)
*Deliverable: Fully integrated, validated enterprise retail management platform.*
- [ ] End-to-end integration testing across frontend, backend, ML engine, and database.
- [ ] Verify server-side role security (unauthorized API calls rejected regardless of client UI state).
- [ ] Validate financial decimal precision and inventory transactional integrity.
- [ ] Comprehensive documentation review, demonstration walk-through, and defense rehearsal.

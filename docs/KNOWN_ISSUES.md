# KNOWN_ISSUES.md — NEXORA Technical Issue & Bug Registry

This document maintains an active registry of known technical issues, architectural inconsistencies, and bugs across the NEXORA codebase. Issues must never be marked as resolved without empirical verification.

---

## Active Issues

### ISSUE-003: Legacy Documentation Files in docs/
- **Severity:** Low
- **Module Affected:** Documentation
- **Relevant Files:**
  - `docs/PROJECT_SPEC.md`
  - `docs/DATABASE_DESIGN.md`
  - `docs/ML_DESIGN.md`
- **Description:** Three legacy markdown files from the earliest project drafts remain in `docs/`. `docs/DATABASE_DESIGN.md` already carries the Task 10.2 `SUPERSEDED HISTORICAL DRAFT` notice directing readers to `docs/DATABASE_SCHEMA.md` v2.9, while `docs/PROJECT_SPEC.md` and `docs/ML_DESIGN.md` remain untouched historical drafts containing superseded patterns relative to `PROJECT_OVERVIEW.md`, `ML_DOCUMENTATION.md`, `DATABASE_SCHEMA.md` v2.9, and `API_DOCUMENTATION.md` v2.1.
- **Current Status:** Open (Preserved per blueprint instructions: legacy notes must remain untouched unless team explicitly approves archival).
- **Proposed Resolution:** Retain the files for historical reference without modifying their preserved contents. Ensure all agents consult the authoritative v2.x documentation per the Source-of-Truth hierarchy defined in `AGENTS.md`.
- **Target Resolution Phase:** Deferred — post-Phase 6 archival, subject to separate explicit team approval (not a scheduled `DEVELOPMENT_ROADMAP.md` v2.0 deliverable).

---

## Resolved Issues

### ISSUE-017: Absence of Integrated Inventory Replenishment Recommendation Endpoint for Academic Demonstration
- **Severity:** Medium (Academic Demonstration Scope & Decision-Support Feature Completeness)
- **Module Affected:** Inventory Decision Support, API Routing, Postman Demonstration Suite
- **Relevant Files:**
  - `backend/app/schemas/inventory.py`
  - `backend/app/services/inventory_service.py`
  - `backend/app/api/routes/inventory.py`
  - `backend/app/api/routes/__init__.py`
  - `backend/tests/test_inventory_recommend.py`
  - `docs/postman/NEXORA_Complete_Demonstration.postman_collection.json`
  - `docs/postman/NEXORA_Postman_Demonstration_Guide.md`
- **Description:** Prior to Task 28, the NEXORA API offered demand forecasting endpoints (`/api/v1/forecast/predict`) but lacked an integrated endpoint to translate those demand predictions into actionable inventory replenishment recommendations (`POST /api/v1/inventory/recommend`) accounting for current warehouse stock, lead time, review cycle, and safety stock. Evaluators and students demonstrating the platform were forced to manually interpret demand numbers rather than presenting an end-to-end decision-support workflow.
- **Resolution Date:** 2026-11-21 (Task 28).
- **Resolution Details:**
  1. Implemented `backend/app/schemas/inventory.py` defining Pydantic v2 validation models for `InventoryRecommendationRequest` and `InventoryRecommendationResponse`.
  2. Implemented `backend/app/services/inventory_service.py` utilizing piecewise linear interpolation across multi-horizon demand estimators ($D_7, D_{15}, D_{30}, D_{90}$) to calculate demand across arbitrary coverage windows ($T_{\text{cov}} = L + R$).
  3. Implemented transparent, mathematically explainable Phase 1 prototype formulas in `backend/app/services/inventory_service.py`:
     $\text{Daily Rate} = \text{round}(\hat{y}_{\text{cov}} / T_{\text{cov}}, 4)$, $\text{Safety Stock} = \text{round}(\text{Daily Rate} \times S, 2)$, $\text{Target Stock} = \text{round}(\hat{y}_{\text{cov}} + \text{Safety Stock}, 2)$, and `recommended_purchase_quantity` $= \max(0.0, \text{round}(\text{Target Stock} - \text{Current Stock}, 2))$ (the JSON field retains up to two decimal places, whereas the human-readable `recommendation` string formats that quantity with `:.0f`).
     *(Scope Note: This stateless Phase 1 endpoint uses caller-supplied stock and `safety_stock_days` and is strictly distinct from the planned MySQL-backed `M11`/`M14` `DDR-01` replenishment workflow, which resolves supplier/supplier-product `lead_time_days`, applies initial Safety Factor `1.20`, accounts for `Projected Available Stock`, and uses planned $\lceil \dots \rceil$ ceiling rounding in Phase 4.)*
  4. Classifies inventory risk into `CRITICAL`, `ELEVATED`, and `SAFE`.
  5. Implemented `POST /api/v1/inventory/recommend` in `backend/app/api/routes/inventory.py` with 404 for unknown SKUs, 422 for insufficient history, and 422 for negative stock quantities.
  6. Added 13 unit tests in `backend/tests/test_inventory_recommend.py`, bringing total passed tests to 168 / 168 (100% pass rate).
  7. Created 19-request Postman collection `NEXORA_Complete_Demonstration.postman_collection.json` and comprehensive demonstration guide `NEXORA_Postman_Demonstration_Guide.md`. Verified all 19 requests pass.

---

### ISSUE-016: Final Dataset Regeneration & Service Code Elimination from Daily Product Demand (F-01 End-to-End Pipeline)
- **Severity:** Medium (Data Pipeline Consistency & Modeling Data Cleanliness)
- **Module Affected:** ML Data Pipeline, Daily Aggregation, Point-in-Time Price Cache
- **Relevant Files:**
  - `backend/ml/data/processed/daily_product_demand.csv`
  - `backend/ml/data/processed/pit_sku_price_history.json`
- **Description:** While Task 22 successfully partitioned non-merchandise service codes (`POST`, `DOT`, `M`, `BANK CHARGES`, etc.; 4,581 transactions) out of `clean_gross_sales.csv` into `service_transactions.csv`, the downstream daily aggregation dataset `daily_product_demand.csv` still contained 5,092 service-related SKU-day rows from earlier preprocessing runs.
- **Resolution Date:** 2026-11-21 (Task 24).
- **Resolution Details:**
  1. Re-executed `run_daily_aggregation_pipeline()` on `clean_gross_sales.csv` containing exclusively commercial merchandise (1,037,089 transactions).
  2. The newly generated `daily_product_demand.csv` contains exactly 2,287,495 rows, representing an exact reduction of 5,092 service rows from 2,292,587 rows. Total demand volume dropped by exactly 17,563 service units to 11,402,742 units.
  3. Rebuilt point-in-time price cache `pit_sku_price_history.json`, reducing tracked SKUs from 4,916 to exactly 4,905 pure commercial SKUs (0 service codes).
  4. Verified zero presence of service codes in `daily_product_demand.csv` or `pit_sku_price_history.json`.
  5. Verified 100% SKU coverage in zero-imputation audit: all 1,756,250 zero days strictly reside within observed active SKU lifespans `[min_date, max_date]`.
  6. Verified bitwise model immutability across all 8 production and experimental model artifacts.
  7. Re-verified all 12 Postman requests and all 155 pytest tests passed with 0 regressions.

---

### ISSUE-015: Task 22 Defect Remediation & Academic Hardening (Postman Test SKU, Startup Readiness, Service Codes, Leakage Tests, CORS, Model Config)
- **Severity:** Medium (Academic Demonstration Integrity, Test Hardening & Security)
- **Module Affected:** Postman Demonstration, Startup Script, ML Preprocessing, Temporal Leakage Tests, CORS Middleware, Model Configuration
- **Relevant Files:**
  - `docs/postman/NEXORA_Experimental_API.postman_collection.json`
  - `start.ps1`
  - `backend/ml/src/preprocessing.py`
  - `backend/tests/test_leakage_corrections.py`
  - `backend/app/main.py`
  - `backend/app/core/config.py`
  - `backend/app/services/experimental_prediction_service.py`
- **Description:** Multiple audit findings and qualifications were identified during the Task 21 audit and independent reviewer inspection:
  1. DEF-001: Request 11 in the experimental Postman collection tested SKU `21777`, which possessed 371 days of records in the recovered dataset, returning HTTP 200 instead of the expected HTTP 422 error test.
  2. DEF-003: `start.ps1` only polled production `/ready`, lacking diagnostic visibility into `/api/v1/experimental/ready`.
  3. F-01: Non-merchandise service and administrative codes (`POST`, `DOT`, `M`, etc.; 4,581 records) remained in `clean_gross_sales.csv`.
  4. F-03: `backend/tests/test_leakage_corrections.py` tests 6 & 7 relied on skipped metadata checks rather than executing active mathematical transformations.
  5. F-09: CORS middleware included wildcard origin `"*"` while `allow_credentials=True` was active, violating strict CORS security.
  6. F-10: Experimental model directory path was hardcoded to `models_task12` rather than being configurable via settings/environment.
- **Resolution Date:** 2026-11-20 (Task 22).
- **Resolution Details:**
  1. Updated Request 11 test SKU in Postman collection to `20877` (9 calendar days of history), resulting in 12/12 passed requests (100% pass rate).
  2. Added secondary non-blocking diagnostic readiness probe in `start.ps1` for `/api/v1/experimental/ready` without breaking failure isolation.
  3. Updated `backend/ml/src/preprocessing.py` to cleanly partition 4,581 service rows into `service_transactions.csv` while saving pure commercial merchandise (1,037,089 rows) to `clean_gross_sales.csv`.
  4. Upgraded tests 6 & 7 in `backend/tests/test_leakage_corrections.py` to active transformation execution tests on synthetic data with 0 skips.
  5. Removed wildcard origin from CORS middleware, locking down to local development client origins.
  6. Added `EXPERIMENTAL_MODELS_DIR` to `Settings` in `config.py` and read it in `ExperimentalPredictionService`.
  7. Re-verified all 155 pytest tests passed (100% pass rate in 41.08s), all 8 model binary hashes confirmed 100% bitwise immutable, and fresh-clone auto-initialization tested and verified.

---

### ISSUE-014: Fresh-Clone Deployment Reproducibility, Readiness Reporting & Experimental Postman Collection
- **Severity:** Medium (Deployment Automation & Subsystem Failure Isolation)
- **Module Affected:** Deployment Scripts, Application Lifespan Probes, Readiness Health Checks & Postman Demonstration
- **Relevant Files:**
  - `backend/ml/src/point_in_time_price.py`
  - `backend/app/schemas/forecast.py`
  - `backend/app/services/historical_data_service.py`
  - `backend/app/services/experimental_prediction_service.py`
  - `backend/app/api/routes/experimental_forecast.py`
  - `backend/app/main.py`
  - `start.ps1`
  - `docs/postman/NEXORA_Experimental_API.postman_collection.json`
  - `docs/postman/EXPERIMENTAL_DEMONSTRATION_GUIDE.md`
  - `backend/tests/test_experimental_forecast.py`
- **Description:** The Task 19 independent deployment audit identified three qualifications preventing zero-intervention setup on a clean clone:
  1. `clean_gross_sales.csv` and `pit_sku_price_history.json` are git-ignored; on a pristine clone, `PointInTimePriceService.load_index()` failed with `FileNotFoundError` without manual preprocessing.
  2. The application readiness probe lacked distinct visibility into the point-in-time price service, reporting misleading readiness states or risking failure cascading across baseline production services.
  3. No dedicated Postman collection existed for the experimental forecasting endpoints (`/api/v1/experimental/*`).
- **Resolution Date:** 2026-11-20 (Task 20).
- **Resolution Details:**
  1. Implemented fresh-clone self-healing in `PointInTimePriceService.load_index()`: if `clean_gross_sales.csv` is missing, it automatically derives it from `online_retail_II.csv` via `run_preprocessing_pipeline` in ~5s, then builds `pit_sku_price_history.json` atomically in ~1s.
  2. Disentangled historical demand readiness (`is_demand_data_ready()`) from price service readiness (`is_price_service_ready()`). If the price service is down, baseline production (`/ready` and `/api/v1/forecast/predict`) continues to operate flawlessly with HTTP 200 (complete failure isolation), while experimental readiness (`/api/v1/experimental/ready`) accurately returns HTTP 503.
  3. Enhanced `start.ps1` with automated preflight checks for experimental assets, automatic preprocessing invocation on clean clones, and updated access point documentation.
  4. Authoring of `docs/postman/NEXORA_Experimental_API.postman_collection.json` with 12 distinct requests covering lifecycle probes, metadata transparency, multi-horizon predictions, edge-case error validation (404/422), and production baseline comparison, complete with automated Postman test assertion scripts.
  5. Created comprehensive companion guide in `docs/postman/EXPERIMENTAL_DEMONSTRATION_GUIDE.md`.
  6. Added 6 new automated regression tests in Section 9 of `test_experimental_forecast.py`. All 155 repository tests executed and passed (100% pass rate). Recomputed SHA-256 hashes of all 8 model binaries, confirming 100% bitwise immutability.

### ISSUE-013: Historical Feature Extraction Cutoff Propagation & Price Index Cache Invalidation
- **Severity:** Low (Historical Backtesting Precision & Cache Staleness)
- **Module Affected:** Machine Learning Subsystem / Historical Feature Extraction & PIT Price Service
- **Relevant Files:**
  - `backend/app/services/historical_data_service.py`
  - `backend/ml/src/point_in_time_price.py`
  - `backend/tests/test_experimental_forecast.py`
- **Description:** The Task 16 independent audit identified two qualifications in the Task 15 implementation:
  1. In `HistoricalDataService.get_features_for_sku(stock_code, as_of_date=...)`, `as_of_date` was not forwarded to `self.get_unit_price(cleaned_sku)`, causing historical backtesting feature vectors to resolve the latest static price instead of the point-in-time price as of `observation_date`.
  2. The precomputed price index `pit_sku_price_history.json` lacked source dataset fingerprinting (`st_mtime` and `st_size`), which could allow a stale or corrupted cache to persist undetected after modifications to `clean_gross_sales.csv`.
- **Resolution Date:** 2026-11-20 (Task 17).
- **Resolution Details:**
  1. Updated `HistoricalDataService.get_features_for_sku` to explicitly pass `as_of_date=observation_date` into `self.get_unit_price(cleaned_sku, as_of_date=observation_date)`. When `as_of_date=None` (forward-looking operational inference), it continues to resolve the latest expanding price seamlessly.
  2. Enhanced `PointInTimePriceService` with source dataset metadata tracking (`source_file`, `source_size`, `source_mtime`, `source_mtime_iso`, `schema_version = '1.1'`). Implemented automatic invalidation and rebuild on missing, stale, or malformed cache. Implemented atomic file writing via `.tmp.<pid>` and `os.replace` to prevent file corruption.
  3. Added 14 new automated tests in `test_experimental_forecast.py` covering feature extraction cutoff propagation, adversarial perturbation invariance, same-day exclusion, forward inference compatibility, cache rebuild triggers, malformed JSON recovery, and atomic replacement.
  4. Verified all 149 repository tests pass (100% pass rate, 0 regressions) and verified bitwise model artifact immutability.

### ISSUE-012: Historical UnitPrice Future Look-Ahead in Experimental Serving API
- **Severity:** Medium (Temporal Information Leakage in Backtesting)
- **Module Affected:** Machine Learning Subsystem / Experimental Serving & Historical Data Service
- **Relevant Files:**
  - `backend/ml/src/point_in_time_price.py`
  - `backend/app/services/historical_data_service.py`
  - `backend/app/services/experimental_prediction_service.py`
  - `backend/tests/test_experimental_forecast.py`
- **Description:** In Task 13, `pit_sku_prices.json` cached static prices evaluated at the dataset end date (`2011-12-09`). While this was completely valid for live forward-looking operational forecasting, evaluating historical queries at $T < \text{2011-12-09}$ caused `UnitPrice` to read post-$T$ transaction averages, creating an asymmetry with the Task 12 training contract.
- **Resolution Date:** 2026-11-20 (Task 15).
- **Resolution Details:** Implemented cutoff-aware `PointInTimePriceService` with precomputed prefix-sum index `pit_sku_price_history.json`. Lookup uses $O(\log k)$ binary search (`bisect_left(dates, obs_str) - 1`) taking ~1.68 microseconds, guaranteeing that only transactions strictly prior to $T$ (`tx_date < T`) contribute to `UnitPrice`. Same-day transactions (`tx_date == T`) and post-$T$ transactions are strictly excluded. Validated 155/155 exact price matches against training matrices and confirmed 100% invariance ($\Delta = 0.00000000$) under adversarial future perturbations across 16 scenarios. Automated test suite expanded to 135 tests passing with 0 regressions.

### ISSUE-007: Single Chronological Holdout Constraint vs Multi-Fold Rolling Backtesting
- **Severity:** Low (Architectural / Data Constraint)
- **Module Affected:** Machine Learning Subsystem / Evaluation
- **Relevant Files:**
  - `backend/ml/src/time_series_split.py`
  - `backend/ml/experiments/sku_level_optimization.py`
- **Description:** Previous 1-year data limitation restricted $D_{90}$ rolling cross-validation due to narrow date spans (125 dates).
- **Resolution Date:** 2026-11-20 (Task 10).
- **Resolution Details:** Resolved by recovering the full 2-year dataset from `online_retail_II.xlsx` (738 calendar days). Expanded training date span to 500+ dates, allowing 3-fold chronological expanding-window splits with 91-day embargoes and full ~112-day validation spans per fold.

---

### ISSUE-011: Raw Dataset Truncation Omitting Year 2009-2010
- **Severity:** High (Data Loss / Truncation)
- **Module Affected:** Machine Learning Subsystem / Data Loading & Preprocessing
- **Relevant Files:**
  - `backend/ml/data/raw/online_retail_II.csv`
  - `backend/ml/src/convert_xlsx_to_csv.py`
  - `docs/DATASET_CONVERSION_REPORT.md`
- **Description:** The raw CSV previously contained only 541,910 rows covering 2010–2011 because the initial export from `online_retail_II.xlsx` defaulted to reading only the active second worksheet (`Year 2010-2011`). The entire first year (`Year 2009-2010`, 525,461 rows) was omitted.
- **Resolution Date:** 2026-11-20 (Task 10).
- **Resolution Details:** Implemented `convert_xlsx_to_csv.py`, parsing both worksheets, standardizing date timestamps to ISO format, preserving the 1-year backup (`online_retail_II_2010_2011_backup.csv`), and generating unified `online_retail_II.csv` totaling exactly 1,067,371 rows with 100% zero-record-loss reconciliation.

---

### ISSUE-008: Temporal Target Leakage in Shuffled KFold TargetEncoder
- **Severity:** High (Methodological Data Leakage)
- **Module Affected:** Machine Learning Subsystem / Feature Engineering
- **Relevant Files:**
  - `backend/ml/experiments/sku_level_optimization.py`
  - `backend/ml/src/chronological_encoder.py`
- **Description:** Scikit-learn's `TargetEncoder(cv=5)` defaults to `KFold(shuffle=True)`. In cross-validation folds on time-series panels, future observations contaminated earlier training row encodings.
- **Resolution Date:** 2026-11-20 (Task 8).
- **Resolution Details:** Implemented `ChronologicalTargetEncoder` which enforces expanding-window target statistics strictly from historical dates $t \le T - (h + 1)$ with horizon embargo. Verified through unit testing that future target perturbations produce exactly 0.0 difference on earlier encodings.

---

### ISSUE-009: Global Price Signal Leakage in UnitPrice Feature
- **Severity:** Medium (Temporal Information Leakage)
- **Module Affected:** Machine Learning Subsystem / Feature Engineering
- **Relevant Files:**
  - `backend/ml/experiments/sku_level_optimization.py`
  - `backend/ml/src/point_in_time_price.py`
- **Description:** In Task 6, SKU median unit price was computed globally across the entire 2-year dataset without filtering by forecast origin date $T$.
- **Resolution Date:** 2026-11-20 (Task 8).
- **Resolution Details:** Implemented `enrich_daily_with_pit_price`, which computes expanding historical transaction price statistics strictly from dates $\text{tx\_date} < T$, with expanding global fallback for SKUs without prior sales. Verified that future transaction perturbations produce exactly 0.0 difference on earlier price features.

---

### ISSUE-010: Validation Row Dropping on 60-Day Features
- **Severity:** Medium (Validation Coverage Inconsistency)
- **Module Affected:** Machine Learning Subsystem / Evaluation
- **Relevant Files:**
  - `backend/ml/experiments/sku_level_optimization.py`
- **Description:** Adding `Lag60` and `RollingMean60` with a strict `complete_mask` excluded 3,343 rows for $D_{30}$ and 2,329 rows for $D_{90}$ where SKUs had $< 60$ days of history.
- **Resolution Date:** 2026-11-20 (Task 8).
- **Resolution Details:** Imputed missing 60-day features with 28-day equivalents (`Lag28`, `RollingMean28`) and added a missing history indicator `Has60dHistory`. Restored 100% of validation rows matching the exact production baseline (100,262 rows for $D_{30}$, 98,157 rows for $D_{90}$).

---

### ISSUE-001: Prediction API Request Schema Mismatch with Blueprint
- **Severity:** Medium
- **Module Affected:** Legacy Module 7 (Technical Blueprint v1.0) / Backend API *(maps in Technical Blueprint v2.2 & `API_DOCUMENTATION.md` v2.1 to `M12 Demand Forecasting`, distinct from `M14 Predictive Planner`)*
- **Relevant Files:**
  - `backend/app/schemas/forecast.py`
  - `backend/app/api/routes/forecast.py`
  - `backend/app/services/prediction_service.py`
- **Description:** Historically, `ForecastRequest` expected a single integer `horizon_days: int` (e.g., `{"stock_code": "85123A", "horizon_days": 30}`). However, Section 9 of Technical Blueprint v1.0 (whose demand-forecasting API contract now resides under `M12 Demand Forecasting` in Technical Blueprint v2.2 and `API_DOCUMENTATION.md` v2.1, separately from `M14 Predictive Planner`) specified a multi-horizon request body taking a list of horizons: `{"stock_code": "85123A", "horizons": [7, 15, 30, 90]}` and returning predictions for all requested horizons in a single response.
- **Resolution Date:** 2026-11-17 (Task 6).
- **Resolution Details:** Refactored `ForecastRequest` to accept `horizons: List[int]` with validation that elements belong to `{7, 15, 30, 90}`, while preserving `horizon_days: Optional[int]` for backwards compatibility. Extended schemas to support nested historical features (`features: HistoricalFeatures`) alongside flat field access. Verified at Task 6 completion with 15 automated integration tests in `backend/tests/test_forecast_api.py` and live TCP HTTP requests (later expanded to 16 cases in `test_forecast_api.py`).

---

### ISSUE-002: ML Pipeline Script Stubs
- **Severity:** Low (Milestone implementation progression)
- **Module Affected:** Machine Learning Subsystem & API Serving
- **Relevant Files:**
  - `backend/ml/src/data_loader.py`
  - `backend/ml/src/preprocessing.py`
  - `backend/ml/src/feature_engineering.py`
  - `backend/ml/src/train.py`
  - `backend/ml/src/evaluate.py`
  - `backend/app/services/prediction_service.py`
  - `backend/app/api/routes/forecast.py`
- **Description:** Pipeline scripts in `backend/ml/src/` were initially structured stubs.
- **Resolution Date:** 2026-11-17 (Phase 1 completion).
- **Resolution Details:** All Phase 1 ML pipeline scripts and inference serving modules are fully implemented, verified, tested, and documented: Tasks 1–5 completed ML pipelines and serialization, and Task 6 integrated model registry loading at lifespan startup with FastAPI inference routes (`POST /api/v1/forecast/`, `POST /api/v1/forecast/predict`, `GET /horizons`, `GET /model-metrics`, `GET /model-info`). All 60 tests in the backend test suite pass.

---

### ISSUE-004: Raw CSV UnicodeDecodeError on Windows Default Encoding
- **Severity:** Low (Dataset Ingestion)
- **Module Affected:** Data Loading (`data_loader.py`)
- **Relevant Files:**
  - `backend/ml/src/data_loader.py`
  - `backend/ml/data/raw/online_retail_II.csv`
- **Description:** Attempting `pd.read_csv('backend/ml/data/raw/online_retail_II.csv')` without specifying character encoding caused Pandas to raise `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa3`.
- **Resolution Date:** 2026-11-16.
- **Resolution Details:** Configured `encoding="latin1"` (or `"cp1252"`) across all raw ingestion scripts in `data_loader.py` and `preprocessing.py`. Verified clean ingestion of all 541,910 rows.

---

### ISSUE-005: System PATH Python Mismatch Causing ModuleNotFoundError
- **Severity:** Medium (Resolved via backend/.venv)
- **Module Affected:** Local Development Environment
- **Relevant Files:**
  - `backend/.venv/`
  - `README.md`
- **Description:** Executing `python` directly on the machine defaulted to `C:\Python315\python.exe` (a bare development Python 3.15 install) rather than Python 3.11 where dependencies were previously installed. This produced `ModuleNotFoundError: No module named 'pandas'`.
- **Resolution Date:** 2026-11-16.
- **Resolution Details:** Standardized on project-local virtual environment at `backend/.venv` using Python 3.11.9, installed all dependencies, and updated setup instructions in `README.md` and `AGENTS.md`.

---

### ISSUE-006: TargetEncoder Temporal Target Leakage Across K-Fold Partitions
- **Severity:** High
- **Module Affected:** Machine Learning Subsystem / Training Pipeline
- **Relevant Files:**
  - `backend/ml/src/train.py`
  - `backend/tests/test_model_training.py`
- **Description:** Scikit-learn's `TargetEncoder(cv=KFold(5, shuffle=False))` partition logic on ordered retail time-series allows target values from later folds to influence SKU target encodings for observations in earlier training folds. This introduced subtle temporal target leakage in the training set.
- **Resolution Date:** 2026-11-17.
- **Resolution Details:** Replaced `TargetEncoder` with `OneHotEncoder(max_categories=50, handle_unknown="infrequent_if_exist", sparse_output=False)` coupled with Ridge linear regression and Random Forest. Categorical encoding is now purely unsupervised, eliminating all target leakage while bounding dimensionality and handling unseen SKUs natively. Confirmed by unit test `test_03b_zero_temporal_target_leakage` and full model retraining across all 4 horizons.

---

### ISSUE-018: Pytest Indefinite Hang on Windows Loopback socketpair in Sandboxed Environments
- **Severity:** Medium
- **Module Affected:** Test Infrastructure / TestClient Asyncio Portal
- **Relevant Files:**
  - `backend/tests/test_forecast_api.py`
  - `backend/requirements.txt`
  - `pytest.ini`
- **Description:** Running `pytest` in sandboxed or network-isolated Windows environments caused the test suite to hang indefinitely at `TestForecastAPI::test_01_supported_horizons_endpoint`. Starlette's `TestClient` initializes `anyio.from_thread.start_blocking_portal()`, which runs Python's Windows `ProactorEventLoop`. The proactor calls `_make_self_pipe()` -> `socket.socketpair()`, which attempts a TCP loopback connect to `127.0.0.1`. When sandbox policies drop local loopback packets, non-blocking `connect()` returns `WSAEWOULDBLOCK` (caught as `BlockingIOError`), and subsequent `lsock.accept()` blocks indefinitely in kernel space.
- **Resolution Date:** 2026-11-17.
- **Resolution Details:** Installed `pytest-timeout==2.4.0` in `backend/.venv/`, declared `pytest-timeout>=2.3.0,<3.0.0` in `backend/requirements.txt`, created a root `pytest.ini` with global `timeout = 30`, and added explicit `tearDownClass` in `test_forecast_api.py` for client lifecycle cleanup. Verified at that milestone (2026-11-17) that all 59 backend tests then in the repository passed in 8.77 seconds.
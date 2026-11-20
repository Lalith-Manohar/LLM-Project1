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
- **Description:** Three legacy markdown files from the earliest project drafts remain in `docs/`. While they do not break application logic, they contain partial schemas and draft notes that have been superseded by `PROJECT_OVERVIEW.md`, `ML_DOCUMENTATION.md`, `DATABASE_SCHEMA.md`, and `API_DOCUMENTATION.md`.
- **Current Status:** Open (Preserved per blueprint instructions: legacy notes must remain untouched unless team explicitly approves archival).
- **Proposed Resolution:** Retain the files untouched for historical reference. Ensure all agents consult the modern core documentation per the Source-of-Truth hierarchy defined in `AGENTS.md`.
- **Target Resolution Phase:** Phase 7 (Final cleanup).

---

## Resolved Issues

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
- **Module Affected:** Module 7 (Predictive Planner) / Backend API
- **Relevant Files:**
  - `backend/app/schemas/forecast.py`
  - `backend/app/api/routes/forecast.py`
  - `backend/app/services/prediction_service.py`
- **Description:** Currently, `ForecastRequest` expected a single integer `horizon_days: int` (e.g., `{"stock_code": "85123A", "horizon_days": 30}`). However, Section 9 of the Technical Blueprint v1.0 specifies a multi-horizon request body taking a list of horizons: `{"stock_code": "85123A", "horizons": [7, 15, 30, 90]}` and returning predictions for all requested horizons in a single response.
- **Resolution Date:** 2026-11-17 (Task 6).
- **Resolution Details:** Refactored `ForecastRequest` to accept `horizons: List[int]` with validation that elements belong to `{7, 15, 30, 90}`, while preserving `horizon_days: Optional[int]` for backwards compatibility. Extended schemas to support nested historical features (`features: HistoricalFeatures`) alongside flat field access. Verified with 15 automated integration tests in `backend/tests/test_forecast_api.py` and live TCP HTTP requests.

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

### ISSUE-008: Pytest Indefinite Hang on Windows Loopback socketpair in Sandboxed Environments
- **Severity:** Medium
- **Module Affected:** Test Infrastructure / TestClient Asyncio Portal
- **Relevant Files:**
  - `backend/tests/test_forecast_api.py`
  - `backend/requirements.txt`
  - `pytest.ini`
  - `docs/TEST_SUITE_VERIFICATION_REPORT.md`
- **Description:** Running `pytest` in sandboxed or network-isolated Windows environments caused the test suite to hang indefinitely at `TestForecastAPI::test_01_supported_horizons_endpoint`. Starlette's `TestClient` initializes `anyio.from_thread.start_blocking_portal()`, which runs Python's Windows `ProactorEventLoop`. The proactor calls `_make_self_pipe()` -> `socket.socketpair()`, which attempts a TCP loopback connect to `127.0.0.1`. When sandbox policies drop local loopback packets, non-blocking `connect()` returns `WSAEWOULDBLOCK` (caught as `BlockingIOError`), and subsequent `lsock.accept()` blocks indefinitely in kernel space.
- **Resolution Date:** 2026-11-17.
- **Resolution Details:** Installed `pytest-timeout==2.4.0` in `backend/.venv/`, declared `pytest-timeout>=2.3.0,<3.0.0` in `backend/requirements.txt`, created a root `pytest.ini` with global `timeout = 30`, and added explicit `tearDownClass` in `test_forecast_api.py` for client lifecycle cleanup. Verified that all 59 backend tests pass in 8.77 seconds.

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

### ISSUE-007: Single Chronological Holdout Constraint vs Multi-Fold Rolling Backtesting
- **Severity:** Low (Architectural / Data Constraint)
- **Module Affected:** Machine Learning Subsystem / Evaluation
- **Relevant Files:**
  - `backend/ml/src/evaluate.py`
  - `backend/ml/src/train.py`
- **Description:** The project documentation describes rolling-origin backtesting. However, the UCI Online Retail II dataset contains only 12 continuous calendar months (December 2010 to December 2011). For a 90-day horizon ($D_{90}$), enforcing the required 90-day purge/embargo gap ($t_{\text{train}} + 90 < \text{val\_start}$) and reserving 40+ days for evaluation leaves only 5 months of training data. Rolling-origin evaluation across 3+ folds with expanding windows is physically impossible for $D_{90}$ without severely compromising training size or violating temporal boundaries.
- **Current Status:** Open (Accepted operational limitation).
- **Proposed Resolution:** Documented accurately that Phase 1 uses a single out-of-time chronological holdout per horizon with strict purge/embargo gaps. In future expansions with multi-year datasets, multi-fold rolling backtesting can be implemented.
- **Target Resolution Phase:** Post-Phase 1 / Future Enhancement.

---

## Resolved Issues

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
- **Description:** Pipeline scripts in `backend/ml/src/` were structured stubs.
- **Resolution Date:** 2026-11-17 (Phase 1 completion).
- **Resolution Details:** All Phase 1 ML pipeline scripts and inference serving modules are fully implemented, verified, tested, and documented: Tasks 1–5 completed ML pipelines and serialization, and Task 6 integrated model registry loading at lifespan startup with FastAPI inference routes (`POST /api/v1/forecast/`, `POST /api/v1/forecast/predict`, `GET /horizons`, `GET /model-metrics`, `GET /model-info`). All 59 tests in the backend test suite pass.**
  1. Attempt `pd.read_csv('backend/ml/data/raw/online_retail_II.csv')` without specifying encoding.
  2. Pandas raises `UnicodeDecodeError`.
- **Current Status:** Resolved in `data_loader.py`.
- **Proposed Resolution:** Always specify `encoding="latin1"` (or `"cp1252"`) when reading `online_retail_II.csv`.
- **Resolution Date:** 2026-11-16. Verified by successful run of `data_loader.py`.

---

### ISSUE-005: System PATH Python Mismatch Causing ModuleNotFoundError
- **Severity:** Medium (Resolved via backend/.venv)
- **Module Affected:** Local Development Environment
- **Relevant Files:**
  - `backend/.venv/`
  - `README.md`
- **Description:** Executing `python` directly on the machine defaulted to `C:\Python315\python.exe` (a bare development Python 3.15 install) rather than Python 3.11 where dependencies were previously installed. This produced `ModuleNotFoundError: No module named 'pandas'`.
- **Reproduction Steps:**
  1. Open terminal where `python` points to `C:\Python315\python.exe`.
  2. Run `python -c "import pandas"`.
- **Current Status:** Resolved via `TD-008` and `backend/.venv`.
- **Proposed Resolution:** Created local virtual environment at `backend/.venv` using Python 3.11.9, installed all dependencies, and updated setup instructions in `README.md`.
- **Resolution Date:** 2026-11-16. Verified by successful execution of `data_loader.py`, `preprocessing.py`, and test suites.

---

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

### ISSUE-007: Single Chronological Holdout Constraint vs Multi-Fold Rolling Backtesting
- **Severity:** Low (Architectural / Data Constraint)
- **Module Affected:** Machine Learning Subsystem / Evaluation
- **Relevant Files:**
  - `backend/ml/src/evaluate.py`
  - `backend/ml/src/train.py`
- **Description:** The project documentation describes rolling-origin backtesting. However, the UCI Online Retail II dataset contains only 12 continuous calendar months (December 2010 to December 2011). For a 90-day horizon ($D_{90}$), enforcing the required 90-day purge/embargo gap ($t_{\text{train}} + 90 < \text{val\_start}$) and reserving 40+ days for evaluation leaves only 5 months of training data. Rolling-origin evaluation across 3+ folds with expanding windows is physically impossible for $D_{90}$ without severely compromising training size or violating temporal boundaries.
- **Current Status:** Open (Accepted operational limitation).
- **Proposed Resolution:** Documented accurately that Phase 1 uses a single out-of-time chronological holdout per horizon with strict purge/embargo gaps. In future expansions with multi-year datasets, multi-fold rolling backtesting can be implemented.
- **Target Resolution Phase:** Post-Phase 1 / Future Enhancement.

---

## Resolved Issues

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

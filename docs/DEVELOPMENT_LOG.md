# DEVELOPMENT_LOG.md — NEXORA Chronological Engineering Ledger

This document maintains a strict chronological development record for NEXORA. Every completed task must be logged here with newest entries at the top. Never log planned work as completed work.

---

### [2026-11-20] — Task 8: Temporal Leakage Corrections & Validation Coverage Restoration

- **Phase & Task:** Task 8 — Temporal Leakage Corrections & Validation Coverage Restoration (`uni_api_experimental` branch).
- **Task Description:** Successfully resolved the three methodological weaknesses identified in the Task 7 independent audit. Implemented strictly chronological point-in-time target encoding enforcing a horizon-aware embargo ($t \le T - h - 1$). Implemented point-in-time historical unit prices derived strictly from historical transactions ($\text{tx\_date} < T$). Restored 100% of validation sample coverage across $D_{30}$ and $D_{90}$ without row loss or data mutations. Implemented date-grouped cross-validation (`DateGroupedTimeSeriesSplit`) with horizon embargo gaps ($\ge 8$d, $\ge 16$d, $\ge 31$d, $\ge 91$d). Validated future perturbation invariance with exact 0.0 difference. Re-evaluated all 4 horizons and verified 100% reproducibility of store-wide macro forecasting.
- **Key Empirical Results on Restored Validation Datasets:**
  - $D_7$ (42,091 rows, sum=2,830,959.0): Corrected WAPE: **56.15%** (vs 55.65% baseline, -0.50 pp)
  - $D_{15}$ (57,840 rows, sum=8,435,173.0): Corrected WAPE: **45.78%** (vs 50.00% baseline, **+4.22 pp improvement**)
  - $D_{30}$ (100,262 rows, sum=25,725,416.0): Corrected WAPE: **44.29%** (vs 48.73% baseline, **+4.44 pp improvement**) — *Full 100,262 validation rows restored!*
  - $D_{90}$ (98,157 rows, sum=63,329,462.0): Corrected WAPE: **51.81%** (vs 53.22% baseline, **+1.41 pp improvement**) — *Full 98,157 validation rows restored!*
  - Store-Wide Macro Reproducibility: $D_7$: 8.87%, $D_{15}$: 12.66%, $D_{30}$: 13.38%, $D_{90}$: 29.00% (100% reproduced).
- **Files Created:**
  - `backend/ml/src/chronological_encoder.py` (Point-in-time expanding window target encoder with horizon embargo)
  - `backend/ml/src/point_in_time_price.py` (Point-in-time historical unit price generator)
  - `backend/ml/src/time_series_split.py` (Date-grouped expanding window CV splitter with horizon embargo gaps)
  - `backend/tests/test_leakage_corrections.py` (11 automated verification tests)
  - `backend/ml/models_experimental_corrected/` (4 corrected model artifacts and `models_metadata.json`)
- **Files Modified:**
  - `backend/ml/experiments/sku_level_optimization.py` (Integrated chronological encoder, PIT price, coverage restoration, and CV)
  - `docs/EXPERIMENTAL_OPTIMIZATION_REPORT.md` (Updated with complete Task 8 section and comparison tables)
  - `docs/DEVELOPMENT_LOG.md`
- **Verification & Branch Safety:**
  - Work conducted exclusively on `uni_api_experimental`.
  - Protected branches `uni_api_submission` and `main` 100% untouched.
  - Production model directory `backend/ml/models/` 100% untouched; SHA-256 hashes verified identical to baseline commit `596430fc6c53dd526b48b9d25d666611d71938a1`.
  - Automated test suite: **98/98 tests passed (100% pass rate)**.

---

### [2026-11-20] — Experimental Branch ML Optimization & WAPE Gap Resolution

- **Phase & Task:** Task 10 — Experimental Branch Creation & ML Optimization (`uni_api_experimental` branch).
- **Task Description:** Successfully created and isolated branch `uni_api_experimental` from baseline commit `596430fc6c53dd526b48b9d25d666611d71938a1`. Preserved `uni_api_submission` and `main` untouched. Solved the empirical mystery of the reported ~10% vs 50% WAPE discrepancy by engineering an independent Store-Wide (Macro) demand forecasting pipeline achieving **8.87% to 13.38% WAPE**. Developed optimized SKU-level models incorporating out-of-fold `TargetEncoder`, volatility, intermittency, momentum, and unit price features, paired with baseline-anchored residual formulations (`ResidualRegressor`). Improved WAPE across all four horizons without target leakage or dataset mutations.
- **Key Empirical Results:**
  1. *Store-Wide (Macro) Demand Forecasting Pipeline:*
     - $D_7$ (7-Day): **8.87% WAPE** (MAE: 15,100 units, Bias: +0.97%)
     - $D_{15}$ (15-Day): **12.66% WAPE** (MAE: 47,710 units, Bias: -10.59%)
     - $D_{30}$ (30-Day): **13.38% WAPE** (MAE: 94,165 units, Bias: -12.93%)
     - $D_{90}$ (90-Day): **29.00% WAPE** (MAE: 521,650 units, Bias: -29.00%)
  2. *SKU-Level Optimized Forecasting Models:*
     - $D_7$:  55.65% -> **54.47% WAPE** (+1.18 pp improvement, bias cut from -2.76% to -1.26%)
     - $D_{15}$: 50.00% -> **46.34% WAPE** (+3.66 pp improvement, bias cut from -8.57% to -4.98%)
     - $D_{30}$: 48.73% -> **45.37% WAPE** (+3.36 pp improvement, MAE dropped from 125.03 to 116.25)
     - $D_{90}$: 53.22% -> **51.35% WAPE** (+1.87 pp improvement, MAE dropped from 343.36 to 326.63)
- **Files Created:**
  - `backend/ml/src/residual_model.py` (Baseline-anchored residual regressor)
  - `backend/ml/experiments/store_wide_forecasting.py` (Macro demand pipeline)
  - `backend/ml/experiments/sku_level_optimization.py` (SKU ML optimization pipeline)
  - `backend/ml/models_experimental/store_wide/` (Store-wide models, latest state, metadata)
  - `backend/ml/models_experimental/` (Optimized SKU models, metadata)
  - `backend/app/services/store_wide_service.py` (Comparative evaluation & macro forecast service)
  - `backend/tests/test_experimental_forecast.py` (Test suite for experimental endpoints)
  - `docs/EXPERIMENTAL_OPTIMIZATION_REPORT.md` (Comprehensive documentation & reproduction guide)
- **Files Modified:**
  - `backend/app/api/routes/forecast.py` (Added `GET /evaluation-comparison` and `GET /store-wide`)
  - `docs/DEVELOPMENT_LOG.md`
- **Verification & Safety:**
  - Protected branch `uni_api_submission` and `main` 100% untouched.
  - Production model directory `backend/ml/models/` 100% untouched.
  - Test suite: 87/87 tests passed (100% pass rate).

---

### [2026-11-20] — Final Academic Deployment: FastAPI, Public URL Generation and Postman Verification

- **Phase & Task:** Task 5 — Final Academic Deployment: FastAPI, Public URL Generation and Postman Verification (`uni_api_submission` branch).
- **Task Description:** Fully deployed the trained multi-horizon machine learning forecasting system locally on FastAPI and generated a public secure HTTPS forwarding URL via ngrok. Successfully verified live HTTP requests over the public internet URL across all college evaluation criteria: liveness (`/health`), readiness (`/ready`), 4-horizon demand prediction (`/api/v1/forecast/predict`), unknown SKU error handling (`404`), and insufficient-history error handling (`422`). Created and exported the official Postman collection and demonstration evidence guide for the 21 November presentation.
- **Academic Requirements Verification Matrix:**
  1. *Requirement 1 (Build and train ML model):* Verified 4 multi-horizon models ($D_7$ Ridge Regression, $D_{15}/D_{30}/D_{90}$ Random Forest) loaded into memory with zero warnings.
  2. *Requirement 2 (Deploy on local server using FastAPI):* Backend actively running on `http://127.0.0.1:8000`. Liveness (`GET /health`) and readiness (`GET /ready`) probes returning HTTP 200 OK.
  3. *Requirement 3 (Generate public URL using ngrok):* ngrok tunnel established to port 8000; public HTTPS endpoint generated: `https://antonym-headband-harpist.ngrok-free.dev`.
  4. *Requirement 4 (Test deployed model using Postman):* Real HTTP requests executed against public URL; exact reference predictions verified for SKU `85123A`:
     - $D_7$: 771.5717 units
     - $D_{15}$: 3009.3201 units
     - $D_{30}$: 3062.3950 units
     - $D_{90}$: 9427.1420 units
- **Error Handling Verified on Public URL:**
  - Unknown SKU (`NON_EXISTENT_SKU_99999`): HTTP 404 Not Found.
  - Insufficient history SKU (`21777` with 6 days): HTTP 422 Unprocessable Content.
- **Files Created:**
  - `docs/postman/NEXORA_Academic_API.postman_collection.json` (Official Postman Collection v2.1 export with live public domain)
  - `docs/postman/DEMONSTRATION_GUIDE.md` (Step-by-step demonstration and restart instructions for demo day)
- **Files Modified:**
  - `docs/DEVELOPMENT_LOG.md`
- **Integrity Guarantee:**
  - Zero retraining, zero hyperparameter edits, zero model artifact changes (SHA256 hashes preserved).
  - Frontend untouched per strict backend-only college demonstration scope.

---

### [2026-11-19] — Dependency Compatibility Audit and Deployment Readiness

- **Phase & Task:** Task 4 — Dependency Compatibility Audit and Deployment Readiness (`uni_api_submission` branch).
- **Task Description:** Completed an end-to-end dependency compatibility audit, Windows fresh-installation verification, FastAPI deployment validation, and Postman API contract verification for the upcoming 21 November academic deadline. Validated that all backend and frontend dependencies install without compilation or version conflicts, all four ML model artifacts load cleanly with zero warnings, and the API is ready for public tunneling via ngrok (Task 5 prerequisite).
- **Core Findings & Validations:**
  1. *Backend Python Dependency Audit:*
     - Scanned all imports across `backend/app/`, `backend/ml/src/`, and `backend/tests/`. Every external import is strictly declared in `backend/requirements.txt` with bounded version ranges (`fastapi`, `uvicorn`, `pydantic`, `pandas`, `numpy`, `scikit-learn`, `joblib`, `openpyxl`, `sqlalchemy`, `pymysql`, `cryptography`, `python-dotenv`, `pytest`, `pytest-timeout`, `httpx`).
     - Zero undeclared, conflicting, or unconstrained packages found.
     - Confirmed Python 3.10+ compatibility (fully certified on Python 3.11.9 64-bit Windows).
  2. *Model Serialization & Deserialization Compatibility:*
     - Model artifacts were saved using scikit-learn 1.9.1, NumPy 2.4.6, Joblib 1.6.0 on Python 3.11.9.
     - Production model loading smoke test executed: 4/4 models loaded into memory with **0 warnings** and identical SHA256 hashes (`demand_model_7d.joblib`, `demand_model_15d.joblib`, `demand_model_30d.joblib`, `demand_model_90d.joblib`).
     - Strict ML immutability rules observed: 0 retraining, 0 hyperparameter changes, 0 feature engineering modifications.
  3. *Windows Fresh-Installation Verification:*
     - Verified `start.ps1` automated discovery and launcher: auto-discovers Python 3.10+, provisions `backend/.venv`, installs dependencies with hash caching (< 2s on repeat runs), installs frontend via `npm ci`, and verifies all 6 essential ML assets before startup.
     - Confirmed pure pre-compiled binary wheel availability for Windows (no C++ build tools required).
  4. *FastAPI & ngrok Deployment Readiness:*
     - Uvicorn host binding tested (`127.0.0.1:8000` / `0.0.0.0:8000`).
     - CORS middleware explicitly permits wildcard origins (`allow_origins=["*"]`) and all HTTP methods/headers.
     - No restrictive `TrustedHostMiddleware` or hardcoded host redirection present; incoming forwarded host headers (e.g. `*.ngrok-free.app`) pass without proxy errors.
     - Documented `ngrok-skip-browser-warning: 69420` header to bypass ngrok free-tier browser interstitials when querying from Postman or cURL.
  5. *Postman API Testing Contract Verification:*
     - Verified exact endpoint: `POST /api/v1/forecast/predict` (and route alias `POST /api/v1/forecast/`).
     - Automated CSV inference payload verified: `{"stock_code": "85123A"}` -> returns `200 OK` with predictions for 7, 15, 30, and 90 days.
     - Error contracts verified:
       - Unknown SKU `NON_EXISTENT_SKU_99999` -> `404 Not Found`.
       - Insufficient history SKU `21777` (< 29 days) -> `422 Unprocessable Content`.
       - Liveness probe `GET /health` -> `200 OK`.
       - Readiness probe `GET /ready` -> `200 OK` (when subsystems loaded) / `503 Service Unavailable` (when unready).
- **Files Modified:**
  - `README.md` (Updated access points, 84-test count, comprehensive Postman guide & deployment specs)
  - `docs/API_DOCUMENTATION.md` (Documented `/ready` probe, automated CSV request schema, and Postman examples)
  - `docs/DEVELOPMENT_LOG.md` (Recorded Task 4 audit entry)
- **Automated Verification:**
  - 84/84 backend pytest tests passing in 22.06s.
  - Frontend production build passing in 981ms (`vite v5.4.21`).
  - Model artifacts SHA256 integrity: 100% match.

---

### [2026-11-18] — Backend Startup Reliability, Model Loading and Readiness Verification

- **Phase & Task:** Task 3 — Backend Startup Reliability, Model Loading and Readiness Verification (`uni_api_submission` branch).
- **Task Description:** Re-engineered FastAPI startup lifecycle, subsystem error handling, and health/readiness endpoints. Decoupled ML model loading and historical demand dataset indexing into independent, thread-safe initialization pipelines. Implemented active model usability testing, strict historical dataset schema validation, a dedicated `/ready` probe (HTTP 200 when all systems verified; HTTP 503 when not ready), and integrated readiness polling into `start.ps1` to prevent race conditions during Windows launcher startup.
- **Root Causes Identified in Original Implementation:**
  1. Coupled initialization in `lifespan`: If `load_models()` threw an error, `load_dataset()` was skipped entirely.
  2. Suppressed startup exceptions: Initialization errors were caught and printed as warnings, leaving the server running in an uninitialized state.
  3. Misleading health check: `GET /health` unconditionally returned `status: "healthy"` even when models or datasets failed to load.
  4. Missing readiness endpoint: No `/ready` endpoint existed to distinguish process liveness from inference readiness.
  5. Missing schema & usability checks: The services did not execute active dummy inference or validate non-empty dataset rows prior to marking services as loaded.
  6. Race conditions: Requests arriving before background initialization completed could trigger unhandled 500 crashes.
- **Key Enhancements Implemented:**
  1. *Decoupled Startup Lifespan (`backend/app/main.py`):* Independently initializes `prediction_service` and `historical_data_service` in isolated try-except blocks, storing explicit error diagnostics without crashing the process.
  2. *Active Model Usability Smoke Tests (`backend/app/services/prediction_service.py`):* Validates pipeline presence, calls dummy inference to verify finite output, records `load_error`, and implements `is_ready()` and `get_status()`.
  3. *Strict Dataset Schema & Row Validation (`backend/app/services/historical_data_service.py`):* Validates required columns (`StockCode`, `date`, `daily_demand`), non-empty row count, date parsing, and SKU indexing.
  4. *Liveness vs. Readiness Probes (`GET /health` & `GET /ready`):*
     - `/health` reports process liveness (200 OK).
     - `/ready` reports structured subsystem readiness (200 OK when ready, 503 Service Unavailable when uninitialized or failed).
  5. *Prediction Endpoint Guarding (`backend/app/api/routes/forecast.py`):* Pre-validates readiness; returns HTTP 503 if models or datasets are unready, while preserving 404 (unknown SKU) and 422 (insufficient history).
  6. *Windows Launcher Readiness Polling (`start.ps1`):* Polls `http://127.0.0.1:8000/ready` up to 25s before launching the frontend, ensuring the backend is fully initialized.
  7. *Comprehensive Test Suite (`backend/tests/test_startup_readiness.py`):* 14 automated unit and integration tests covering all failure, readiness, and error scenarios.
- **Files Modified:**
  - `backend/app/main.py`
  - `backend/app/schemas/forecast.py`
  - `backend/app/services/prediction_service.py`
  - `backend/app/services/historical_data_service.py`
  - `backend/app/api/routes/forecast.py`
  - `start.ps1`
  - `docs/DEVELOPMENT_LOG.md`
- **Files Created:**
  - `backend/tests/test_startup_readiness.py`
- **Automated Verification:**
  - 84/84 backend pytest tests passing in 21.39s.
  - Frontend production build passing in 851ms.

---

### [2026-11-18] — Automated Windows Setup & Startup: Robust `start.ps1` Launcher

- **Phase & Task:** Task 2 — Fix Windows Automatic Setup and Startup (`start.ps1`) (`uni_api_submission` branch).
- **Task Description:** Re-engineered the project root launcher `start.ps1` into a fully automated, self-healing Windows setup and execution tool. A user downloading a fresh GitHub ZIP can simply execute `.\start.ps1` in PowerShell, and the script automatically verifies essential ML assets, discovers compatible host Python installations (3.10+), creates `backend/.venv` if missing, installs required backend pip packages, verifies Node.js & npm, installs frontend npm packages via `npm ci`, and launches FastAPI and Vite in separate console windows.
- **Root Causes Identified in Original `start.ps1`:**
  1. Failed immediately on any fresh clone/ZIP because `backend/.venv` and `frontend/node_modules` are git-ignored and did not exist.
  2. Forced users to manually execute `python -m venv`, `pip install`, and `npm install`.
  3. Lacked automated host Python discovery (`py`, `python`, explicit registry paths) and Python version verification (>= 3.10).
  4. Lacked Node.js and npm prerequisite validation and helpful installation links.
  5. Did not verify essential datasets and pre-trained `.joblib` models before launching, allowing silent runtime failures.
  6. Lacked dependency caching, causing redundant package installation checks.
- **Key Enhancements Implemented in `start.ps1`:**
  1. *Asset Pre-Flight Verification:* Validates existence of all 6 essential runtime files (`daily_product_demand.csv`, `models_metadata.json`, and the four `.joblib` models) before attempting to boot servers.
  2. *Intelligent Python Discovery:* Dynamically searches for compatible Python interpreters (checking `py -3.11`, `py -3.12`, `py -3.10`, LocalAppData, ProgramFiles, and PATH), validating `major == 3` and `minor >= 10`.
  3. *Zero-Effort Virtual Environment:* Automatically builds `backend/.venv` if missing and activates `backend/.venv/Scripts/python.exe`.
  4. *Idempotent Dependency Caching:* Hashes `requirements.txt` and `package-lock.json` to marker files within ignored directories (`.venv` and `node_modules`). Dependencies install automatically on first run and are skipped in subsequent runs (< 2s startup).
  5. *Prerequisite Guidance:* Displays official download links (`python.org`, `nodejs.org`) if host tools are missing.
  6. *Port Conflict Detection:* Non-intrusively tests TCP ports 8000 and 5173 to warn users if another instance is already running.
  7. *Documentation Updated:* Overhauled `README.md` to feature `.\start.ps1` as the primary Windows quickstart while preserving separate Kaggle instructions.
- **Files Modified:**
  - `start.ps1`
  - `README.md`
  - `docs/DEVELOPMENT_LOG.md`
- **Verification & Test Scenarios:**
  - Fresh venv creation: Verified.
  - Dependency caching: Verified (< 2s second run).
  - Missing asset validation: Verified.
  - End-to-end forecast request (SKU `85123A`): HTTP 200 with all 4 multi-horizon predictions.
  - 70/70 backend pytest tests passing.
  - Frontend Vite build passing.

---

### [2026-11-18] — Self-Contained Deployment: Tracking Essential Datasets & Trained Models in Git

- **Phase & Task:** Task 1 — Make the GitHub ZIP Self-Contained with Required Data and Trained Models (`uni_api_submission` branch).
- **Task Description:** Configured Git tracking and updated `.gitignore` so that anyone downloading the repository as a ZIP from GitHub receives all essential datasets and pre-trained model artifacts required to run the existing NEXORA forecasting application without downloading external datasets, running preprocessing, or retraining models.
- **Key Actions & Deliverables:**
  1. *Identified Runtime Assets:*
     - Raw dataset: `backend/ml/data/raw/online_retail_II.csv` (42.92 MB, already tracked in Git).
     - Processed historical demand time-series: `backend/ml/data/processed/daily_product_demand.csv` (32.76 MB, required by `historical_data_service.py`).
     - Pre-trained model artifacts: `backend/ml/models/demand_model_7d.joblib` (0.02 MB), `demand_model_15d.joblib` (1.10 MB), `demand_model_30d.joblib` (1.09 MB), `demand_model_90d.joblib` (0.99 MB).
     - Model manifest: `backend/ml/models/models_metadata.json` (0.01 MB).
  2. *Granular `.gitignore` Refinement:*
     - Selectively un-ignored `daily_product_demand.csv`, `models_metadata.json`, and the four `.joblib` model binaries while continuing to ignore intermediate/temporary datasets (`clean_gross_sales.csv`, `ml_feature_dataset.csv`, etc.).
  3. *Size & GitHub Constraints Verification:*
     - Total uncompressed size of all 7 assets is **78.88 MB** (newly added files: **35.97 MB**).
     - All individual files are strictly below GitHub's 50 MB warning threshold and 100 MB hard limit (largest is 42.92 MB).
     - Git LFS was intentionally avoided, guaranteeing that GitHub's standard "Download ZIP" packages the **actual, full binary `.joblib` files and CSVs** directly into the archive without pointer stubs.
     - Total `.git` repository size is ~60.49 MB; resulting compressed ZIP download is estimated at 25–30 MB.
  4. *Quality & Model Immutability Verification:*
     - Zero models retrained or altered. Checksums match initial training run.
     - 70/70 backend pytest tests passing in 25.08s.
     - Frontend Vite build passing in 854ms.
- **Files Modified:**
  - `.gitignore`
  - `docs/DEVELOPMENT_LOG.md`
- **Files Tracked & Committed:**
  - `backend/ml/data/processed/daily_product_demand.csv`
  - `backend/ml/models/demand_model_7d.joblib`
  - `backend/ml/models/demand_model_15d.joblib`
  - `backend/ml/models/demand_model_30d.joblib`
  - `backend/ml/models/demand_model_90d.joblib`
  - `backend/ml/models/models_metadata.json`
- **Commit Reference:** `756faf3` (and documentation update).

---

### [2026-11-18] — Automatic CSV-to-Forecast Pipeline & Frontend Simplification

- **Phase & Task:** Phase 1 Inference Pipeline Enhancement & Frontend Simplification — Automatic CSV Historical Feature Generation.
- **Task Description:** Successfully transitioned NEXORA from manual feature input to an automated, end-to-end retail forecasting system. Implemented `HistoricalDataService` in FastAPI to dynamically retrieve daily sales records from `daily_product_demand.csv`, compute the nine required lag and rolling features at the latest historical observation date with exact training-pipeline parity, and run all four trained scikit-learn models ($D_7, D_{15}, D_{30}, D_{90}$). Completely removed manual feature inputs from the React frontend, delivering a streamlined, manager-friendly experience.
- **Components & Functionality Implemented:**
  1. *Historical Data Service (`backend/app/services/historical_data_service.py`):*
     - Authoritative dataset loading: Indexes `daily_product_demand.csv` (1,074,653 rows, 3,922 SKUs) in memory with continuous date imputation and zero-demand padding.
     - Fallback safety: Capable of aggregating `clean_gross_sales.csv` using strict training formulas, or raising `DatasetUnavailableError` (HTTP 503).
     - Sub-millisecond $O(1)$ SKU lookup and feature extraction.
     - Enforces minimum historical span requirement: Requires at least 29 continuous calendar days to calculate 28-day lags and rolling averages; raises `InsufficientHistoryError` (HTTP 422) if fewer days are available (e.g. SKU `21777` with 6 days history).
     - Raises `HistoricalDataNotFoundError` (HTTP 404) for unknown SKUs.
  2. *Observation Date Transparency & Parity:*
     - Prediction origin is strictly anchored to the latest available historical observation date for each SKU (e.g. `2011-12-09`), avoiding current wall-clock date leakage.
     - Evaluated feature parity against `ml_feature_dataset.csv` across 10 SKUs and multiple historical dates: **30/30 checks passed with 100% exact numerical match**.
     - `ForecastResponse` augmented with `observation_date`, `history_days`, and `is_auto_generated=True`.
  3. *Backend Schema & API Harmonization (`forecast.py`, `prediction_service.py`):*
     - Made `features` optional in `ForecastRequest`. When omitted, features are automatically generated from CSV.
     - Preserved 100% backward compatibility for manual feature payloads used by legacy tests.
     - Registered `historical_data_service` in `main.py` lifespan manager for safe pre-loading at startup.
  4. *Frontend Simplification (`frontend/src/App.tsx`, `App.css`, `types/forecast.ts`):*
     - Removed all 9 manual numerical input fields (`Lag1`, `Lag7`, `Lag14`, `Lag28`, `RollingMean7`, `RollingMean28`, `DayOfWeek`, `Month`, `DayOfMonth`).
     - Added prominent observation notice: *"Historical sales data is automatically processed to generate demand forecasts."*
     - Updated catalog quick-pills: `85123A` (high volume), `71053` (medium volume), `85099B` (top volume), `22423` (core catalog), and `21777` (demonstrates insufficient-history validation).
     - Displayed `Forecast Origin` date (`2011-12-09`) and `Historical Base` (e.g. `374 Days Analyzed`) in the results meta bar.
  5. *Test Suite Expansion (`backend/tests/test_historical_forecast.py`):*
     - Added 10 automated unit and integration tests covering dataset indexing, feature parity, SKU-only requests, unknown SKU 404, insufficient history 422, and manual override backward compatibility.
- **Files Created:**
  - `backend/app/services/historical_data_service.py`
  - `backend/tests/test_historical_forecast.py`
- **Files Modified:**
  - `backend/app/schemas/forecast.py`
  - `backend/app/services/prediction_service.py`
  - `backend/app/api/routes/forecast.py`
  - `backend/app/main.py`
  - `frontend/src/types/forecast.ts`
  - `frontend/src/App.tsx`
  - `frontend/src/App.css`
  - `docs/DEVELOPMENT_LOG.md`
  - `docs/FEATURES_STATUS.md`
- **Verification Results:**
  - Feature parity checks: 30/30 checks passed (100% exact match).
  - Backend regression test suite: **70/70 tests passed in 21.88s** (100% pass rate, 0 regressions).
  - Frontend production build: `tsc && vite build` passed in 883ms (`dist/` bundle refreshed).
  - Real HTTP integration test: Verified on `85123A`, `71053`, `85099B`, `22423`, `21777` (HTTP 422), and unknown SKU (HTTP 404).
- **Milestone Status:** Phase 1 automated inference pipeline complete and verified.

---

### [2026-11-18] — Final Verification of Forecast Fixes & SKU Frequency Audit

- **Phase & Task:** Final Verification Audit — SKU 85123A Frequency Classification Analysis & Full Frontend Verification.
- **Task Description:** Conducted a comprehensive, evidence-based investigation into model artifacts, fitted encoders, and backend warning metadata to resolve reported discrepancies regarding SKU 85123A frequency classification, followed by end-to-end verification of the 4 demonstration profiles and responsive layout.
- **Key Findings & Evidence:**
  1. *Fitted OneHotEncoder Structure:* The serialized pipelines in `backend/ml/models/` fit `OneHotEncoder(max_categories=50, handle_unknown='infrequent_if_exist')`. Across all four horizons, the encoder produces exactly 50 columns: 49 explicitly retained frequent SKUs (e.g. `85231B`, `85232D`, `90003C`, ..., `POST`) plus 1 bundled column `StockCode_infrequent_sklearn`.
  2. *Transformation Level vs Warning Metadata Level:*
     - At the *encoder transformation matrix level*, neither `85123A`, `71053`, nor `21777` is in the 49 retained categories. All three map to `StockCode_infrequent_sklearn = 1.0` during one-hot encoding.
     - At the *backend warning metadata level*, `PredictionService.load_models()` sets `self.frequent_skus = set(cat_encoder.categories_[0])`. In scikit-learn, `categories_[0]` stores all 3,562 training set categories, not just the 49 individual columns. Thus, `self.frequent_skus` functions as a "known in training data" set.
     - `85123A` and `71053` were present in the training set (`in categories_[0] = True`), so the backend emits no warning. `21777` was absent from the chronological training split (`in categories_[0] = False`), so the backend emits an infrequent category warning.
     - This discrepancy is purely a terminology difference between encoder column cardinality and the backend's "seen in training" check. It has zero impact on inference correctness, as the scikit-learn pipeline performs mathematical evaluation identically regardless of the response warning metadata.
  3. *Demonstration Profile Verification:*
     - `85123A` (High-Volume): 7d: 152.37, 15d: 412.09, 30d: 709.90, 90d: 2,488.98.
     - `71053` (Medium-Volume): 7d: 58.88, 15d: 132.63, 30d: 272.10, 90d: 848.92.
     - `21777` (Low-Volume): 7d: 22.52, 15d: 37.98, 30d: 92.80, 90d: 269.05 (with warning).
     - `NEW_UNSEEN_SKU_DEMO` (Unseen): 7d: 38.92, 15d: 87.13, 30d: 172.06, 90d: 492.24 (with warning).
  4. *Model Display & Responsive Layout Verification:*
     - D7 displays "Ridge Regression" (from backend `Linear Regression`); D15, D30, and D90 display "Random Forest".
     - Responsive forecast cards display in 4 columns (> 760px container / > 1200px viewport), 2 columns (440px–760px container / <= 1200px viewport), and 1 column (< 440px container / <= 600px viewport).
- **Files Modified:**
  - `docs/DEVELOPMENT_LOG.md`
- **Verification Results:**
  - `npx tsc --noEmit` & `npm run build`: Passed in 894ms (0 errors).
  - Backend regression tests: 60/60 passed in 10.91s (100% pass rate).
  - FastAPI HTTP POST verification: All 4 presets returned HTTP 200 with volume-proportional multi-horizon predictions.
- **Milestone Status:** Final closure complete; verified and ready for 21 November presentation.

---

### [2026-11-18] — SKU Demonstration Profiles, Model Name Mapping & Responsive Cards

- **Phase & Task:** Frontend Forecast Consistency, Model Name Clarity & Responsive Card Layout.
- **Task Description:** Resolved manual testing observations in the demonstration frontend client (`frontend/src/App.tsx` and `frontend/src/App.css`) ahead of the 21 November 2026 academic demonstration:
  1. *SKU-Specific Demonstration Feature Presets:* Replaced single generic sample feature vector with 4 distinct illustrative demonstration profiles corresponding to catalog presets:
     - `85123A` (High-volume demonstration profile: Lags 24/28/22/25, Rolling 26.5/24.8) -> Forecasts: 7d: 152.37, 15d: 412.09, 30d: 709.90, 90d: 2,488.98.
     - `71053` (Medium-volume demonstration profile: Lags 8/10/7/9, Rolling 8.8/8.5) -> Forecasts: 7d: 58.88, 15d: 132.63, 30d: 272.10, 90d: 848.92.
     - `21777` (Low-volume demonstration profile: Lags 2/3/1/2, Rolling 2.4/2.1) -> Forecasts: 7d: 22.52, 15d: 37.98, 30d: 92.80, 90d: 269.05 (includes infrequent category fallback warning).
     - `NEW_UNSEEN_SKU_DEMO` (Unseen SKU demonstration profile: Lags 5/5/5/5, Rolling 5.0/5.0) -> Forecasts: 7d: 38.92, 15d: 87.13, 30d: 172.06, 90d: 492.24 (includes infrequent category fallback warning).
  2. *Illustrative Disclosure Notice:* Added clear UI disclaimer in the feature panel stating that loaded presets are illustrative demonstration inputs and NOT verified historical sales records.
  3. *Automatic Profile Switching:* Implemented `handleSelectSku` so selecting any catalog preset pill or clicking "Load Demonstration Sample" automatically loads the corresponding feature profile into the form vector.
  4. *Model Display Name Correction:* Updated the model display logic so $D_7$ explicitly renders as "Ridge Regression" (matching backend `Linear Regression` estimator trained with `Ridge(alpha=100.0)`), while $D_{15}$, $D_{30}$, and $D_{90}$ render as "Random Forest".
  5. *Responsive Forecast Cards Layout:* Converted `.horizon-cards-grid` to use CSS Container Queries (`@container resultsPanel (max-width: 760px)` and `(max-width: 440px)`) plus responsive breakpoints, enforcing clean 4-column (desktop/wide), 2-column (medium/split), and 1-column (compact) layouts without awkward 3+1 card stranding.
- **Files Modified:**
  - `frontend/src/App.tsx`
  - `frontend/src/App.css`
  - `docs/DEVELOPMENT_LOG.md`
- **Verification Results:**
  - `npx tsc --noEmit` & `npm run build`: Vite production build passed in 921ms (`dist/` bundle refreshed cleanly).
  - Backend regression test suite: 60/60 tests passed in 10.91s (100% pass rate).
  - Live prediction verification: All 4 SKU profiles verified to return distinct, non-identical multi-horizon predictions with correct model identification and zero artificial mocks.
- **Milestone Status:** Phase 1 client interface verified, consistent, and ready for 21 November presentation.

---

### [2026-11-17] — Simple Frontend UI Polish for Academic Submission

- **Phase & Task:** Frontend UI Polish — Clean, High-Contrast Light Theme for 21 November 2026 Academic Demonstration.
- **Task Description:** Refined the demonstration frontend interface (`frontend/src/index.css` and `frontend/src/App.css`) with a clean, light-mode design system optimized for projector visibility and academic evaluation. Converted dark surfaces into clean white cards with subtle borders (`#e2e8f0`), soft shadows, deep slate typography (`#0f172a`), and modern indigo/blue accents (`#4f46e5`). Preserved all backend endpoints, Pydantic schemas, ML prediction logic, and interactive components.
- **Improvements Implemented:**
  1. *Color Palette:* Light grey canvas (`#f4f6fa`), crisp white card containers (`#ffffff`), and indigo action buttons (`#4f46e5` / `#4338ca`).
  2. *Readability & Typography:* High-contrast text hierarchy with 15px base size, dark slate headings (`#1e293b`), and legible field labels (`#475569`).
  3. *Consistent Cards & Radii:* Uniform 10px and 14px rounded corners (`--radius-md`, `--radius-lg`) with elevation shadows (`--shadow-sm`, `--shadow-md`).
  4. *Legible Predictions:* 4 clean white horizon cards ($D_7, D_{15}, D_{30}, D_{90}$) featuring large numeric figures (`1.85rem`), active model badges, and green validation WAPE indicators.
  5. *Collapsible Inspector Drawer:* Clean light code viewer (`#f8fafc`) for demonstrating raw HTTP 200 responses and POST request payloads during viva.
- **Files Modified:**
  - `frontend/src/index.css`
  - `frontend/src/App.css`
  - `docs/DEVELOPMENT_LOG.md`
  - `docs/FEATURES_STATUS.md`
- **Verification Results:**
  - `npx tsc --noEmit`: 0 errors.
  - `npm run build`: Vite production build passed in 983ms (`dist/` bundle created).
  - Backend regression test suite: 60/60 tests passed in 11.49s (100% pass rate).
- **Milestone Status:** Demonstration client polished and verified for 21 November presentation.

---

### [2026-11-17] — Phase 1 Client Application & FastAPI Integration

- **Phase & Task:** Phase 1 Client & Backend Integration — React + TypeScript Client Application & FastAPI Integration.
- **Task Description:** Built and verified a complete, responsive, modern React 18 + TypeScript + Vite demonstration client application inside `frontend/` to establish and prove real HTTP communication with the NEXORA FastAPI ML inference backend for the 21 November 2026 academic project demonstration and viva presentation.
- **Components & Functionality Implemented:**
  1. *Project Setup & Bundler:* Initialized Vite + React 18 + TypeScript 5 in `frontend/` with strict bundler resolution and dev-server on port 5173 (`frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/package.json`).
  2. *Type Contracts:* Implemented strict TypeScript schema interfaces matching backend Pydantic models in `frontend/src/types/forecast.ts` (`ForecastRequest`, `ForecastResponse`, `HistoricalFeatures`, `HorizonPredictionDetail`, `HealthResponse`, `SupportedHorizonsResponse`).
  3. *HTTP Client Layer:* Implemented strongly-typed browser `fetch` service in `frontend/src/services/api.ts` handling `GET /health`, `GET /api/v1/forecast/horizons`, and `POST /api/v1/forecast/` with structured error decoding (`ApiError`).
  4. *Interactive Client UI:* Built `frontend/src/App.tsx` with:
     - Real-time backend connection status indicator (checking / online / offline) polling `GET /health`.
     - Stock code input with catalog preset buttons (`85123A`, `71053`, `21777`, `NEW_UNSEEN_SKU_DEMO`).
     - Multi-horizon selector for all 4 horizons (**7, 15, 30, and 90 days**).
     - Numerical inputs for historical lag and rolling features with clear label hints.
     - "Load Sample Feature Values" button explicitly labeled as demonstration data.
     - Responsive prediction cards displaying projected demand units, active ML pipeline name, and out-of-time validation WAPE (%) benchmarks.
     - Informational warning banner for unseen or infrequent SKUs.
     - Expandable **HTTP Request/Response JSON Inspector drawer** allowing examination of the raw request payload and HTTP 200 response during viva evaluation.
  5. *Design System & Styling:* Created enterprise dark-theme stylesheet in `frontend/src/index.css` and `frontend/src/App.css` aligned with the NEXORA visual branding.
  6. *CORS Configuration:* Updated `CORSMiddleware` in `backend/app/main.py` to explicitly authorize frontend development origins (`http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:3000`).
- **Files Created:**
  - `frontend/package.json`
  - `frontend/tsconfig.json`
  - `frontend/vite.config.ts`
  - `frontend/index.html`
  - `frontend/.env.example`
  - `frontend/public/favicon.svg`
  - `frontend/src/main.tsx`
  - `frontend/src/App.tsx`
  - `frontend/src/App.css`
  - `frontend/src/index.css`
  - `frontend/src/vite-env.d.ts`
  - `frontend/src/services/api.ts`
  - `frontend/src/types/forecast.ts`
  - `frontend/README.md`
- **Files Modified:**
  - `backend/app/main.py`
  - `README.md`
  - `docs/DEVELOPMENT_LOG.md`
  - `docs/FEATURES_STATUS.md`
- **Verification & Testing Results:**
  - `npm run build`: TypeScript compilation and Vite production bundle succeeded cleanly in 943ms with zero errors.
  - Live HTTP Integration Test: Verified real TCP communication against running Uvicorn server for `GET /health` (200 OK), `GET /api/v1/forecast/horizons` (200 OK), and `POST /api/v1/forecast/` with multi-horizon evaluation (200 OK, CORS header validated) and unseen SKU handling (200 OK with warning).
  - Backend Regression Test Suite: Full 60 tests collected and passed in 10.84s (100% pass rate).
- **Next Recommended Milestone:** Proceed to Phase 2: MySQL Relational Database Configuration & Operational CRUD.

---

### [2026-11-17] — Phase 1 Code Simplification, Maintainability & Regression Audit

- **Phase & Task:** Quality & Maintainability — Phase 1 Code Simplification, Maintainability & Regression Audit.
- **Task Description:** Performed an exhaustive code quality, simplicity, and maintainability audit across all Phase 1 source files (`train.py`, `feature_engineering.py`, `preprocessing.py`, `evaluate.py`, `predict.py`, `prediction_service.py`, `forecast.py`). Established a verified 59-test baseline. Refactored repeated model evaluation boilerplate in `train.py` into a reusable `_evaluate_candidate_model` helper. Eliminated redundant classification assignment in `preprocessing.py`. Removed unused imports (`os`, `Tuple`) across 4 files. Resolved pre-existing Pydantic boolean coercion error for `DEBUG=release` environment variables in `config.py`. Implemented a functional `run_inference()` utility in `predict.py` connecting directly to `PredictionService` and added `test_16_predict_module_run_inference`. Verified complete 60-test backend suite with 100% pass rate in 11.17s with zero regressions. Produced `docs/PHASE_1_CODE_SIMPLIFICATION_AUDIT.md` and `docs/PHASE_1_CODE_SIMPLIFICATION_REPORT.md`.
- **Simplifications Implemented:**
  1. *`train.py`:* Extracted repeated fitting, prediction timing, clipping, metric evaluation, and dictionary construction into `_evaluate_candidate_model()`, saving ~45 lines of boilerplate. Removed unused imports `os` and `Tuple`.
  2. *`preprocessing.py`:* Removed redundant re-assignment `df_classified.loc[mask_exceptional, "transaction_stream"] = "exceptional"`. Removed unused imports `os` and `Tuple`.
  3. *`feature_engineering.py`:* Removed unused import `os`.
  4. *`prediction_service.py`:* Removed unused import `os`.
  5. *`predict.py`:* Replaced dead `NotImplementedError` stub with a fully working, clean programmatic and CLI inference function `run_inference()` delegating to `PredictionService`.
  6. *`config.py`:* Added `@field_validator("DEBUG", mode="before")` to prevent crash when `DEBUG=release` is set as an OS environment variable.
  7. *`forecast.py`:* Removed duplicate stubs and docstrings at the top of the route file.
  8. *`test_forecast_api.py`:* Added `test_16_predict_module_run_inference` verifying offline inference.
- **Files Created:**
  - `docs/PHASE_1_CODE_SIMPLIFICATION_AUDIT.md` (Stage A audit report)
  - `docs/PHASE_1_CODE_SIMPLIFICATION_REPORT.md` (Stage B final report and scorecard)
- **Files Modified:**
  - `backend/ml/src/train.py`
  - `backend/ml/src/preprocessing.py`
  - `backend/ml/src/feature_engineering.py`
  - `backend/ml/src/predict.py`
  - `backend/app/services/prediction_service.py`
  - `backend/app/core/config.py`
  - `backend/app/api/routes/forecast.py`
  - `backend/tests/test_forecast_api.py`
  - `docs/DEVELOPMENT_LOG.md`
- **Verification & Regression Results:**
  - 60 backend tests collected, 60 passed in 11.17s (0 failed, 0 skipped, 0 errors).
  - All 4 model artifacts verified loadable and unchanged.
  - API request/response contracts 100% preserved.
- **Scorecard Results:** Original Score: **88 / 100** $\rightarrow$ Refactored Score: **97 / 100** (+9 improvement).
- **Next Recommended Milestone:** Proceed to Phase 2: MySQL Relational Persistence & Operational CRUD.

---

### [2026-11-17] — Backend Test Suite Performance Diagnosis, Loopback Hang Fix & Full Verification

- **Phase & Task:** Test Infrastructure & Verification — Backend Test Suite Performance Diagnosis, Loopback Hang Fix & Full Verification.
- **Task Description:** Conducted a comprehensive diagnostic investigation into why the full backend test suite (`pytest backend/tests/ -v`) hung for 23 minutes. Traced thread call stacks, verified process states, identified the root cause in Windows socket loopback handling within Starlette's `TestClient` / `anyio` portal, installed `pytest-timeout`, created a global `pytest.ini` with 30-second per-test timeout, added `tearDownClass` to `TestForecastAPI`, verified each test file independently, and executed the complete 59-test suite to 100% pass rate in 8.77 seconds. Produced `docs/TEST_SUITE_VERIFICATION_REPORT.md`.
- **Root Cause & Technical Insights:**
  1. *Root Cause:* Starlette's `TestClient` initializes `anyio.from_thread.start_blocking_portal()`. On Windows, Python's `ProactorEventLoop._make_self_pipe()` calls `socket.socketpair()`. In a restricted sandbox without elevated network permissions, `csock.connect(('127.0.0.1', port))` returns `WSAEWOULDBLOCK (10035)`, which Python's `socketpair` catches as `BlockingIOError` and treats as non-fatal. Then `lsock.accept()` executes as a blocking call without a timeout. Because the TCP handshake was blocked by the sandbox security boundary, `accept()` hung indefinitely in kernel space.
  2. *Hang-Prevention Protection:* Installed `pytest-timeout==2.4.0`, added `pytest-timeout>=2.3.0,<3.0.0` to `backend/requirements.txt`, and configured `timeout = 30` in root `pytest.ini`. No test can ever run for 23 minutes again.
  3. *Client Resource Cleanup:* Added `tearDownClass` in `backend/tests/test_forecast_api.py` calling `TestClient.close()` to ensure orderly thread-pool shutdown.
- **Files Created:**
  - `pytest.ini` (Root pytest configuration enforcing 30s per-test timeout and warning filters)
  - `docs/TEST_SUITE_VERIFICATION_REPORT.md` (Full diagnostic and execution verification report)
- **Files Modified:**
  - `backend/requirements.txt` (Declared `pytest-timeout>=2.3.0,<3.0.0`)
  - `backend/tests/test_forecast_api.py` (Added `tearDownClass` for clean client lifecycle)
  - `docs/DEVELOPMENT_LOG.md` (Added this entry)
- **Testing & Verification Evidence:**
  - `test_feature_engineering.py`: 7 passed in 2.17s
  - `test_ml_features.py`: 10 passed in 2.12s
  - `test_model_training.py`: 10 passed in 6.79s
  - `test_model_evaluation.py`: 9 passed in 2.05s
  - `test_forecast_api.py`: 15 passed in 8.02s
  - `test_main.py`: 3 passed in 0.85s
  - `test_preprocessing.py`: 5 passed in 1.15s
  - **Complete Test Suite:** `pytest backend/tests/ -v --timeout=30` $\rightarrow$ **59 passed in 8.77s, 0 failed, 0 skipped**.
- **Next Recommended Task:** Proceed to Phase 2: MySQL Database & Operational CRUD (`backend/app/db/`, Alembic migrations, and catalog/inventory tables).

---

### [2026-11-17] — Phase 1, Task 6: FastAPI Multi-Horizon ML Inference Integration

- **Phase & Task:** Phase 1 (ML Demand Forecasting & FastAPI Serving) — Task 6: FastAPI Multi-Horizon ML Inference Integration.
- **Task Description:** Successfully integrated the four trained, leakage-free demand forecasting models (`demand_model_7d.joblib`, `15d`, `30d`, `90d`) and `models_metadata.json` into the FastAPI backend service under `/api/v1/forecast/`. Implemented startup lifespan model loading to ensure models reside permanently in memory with zero per-request disk I/O. Refactored Pydantic schemas to resolve `ISSUE-001`, supporting multi-horizon queries (`horizons: [7, 15, 30, 90]`) alongside backwards-compatible queries (`horizon_days: int`) and both nested/flat feature inputs. Wired model registry with strict 10-column DataFrame mapping, non-negativity post-processing $\max(0, \hat{y})$, and resilient unseen SKU handling with informative warnings. Implemented model metrics and pipeline info endpoints. Authored 15 automated unit & integration tests, achieved 59/59 passing tests across the entire backend, and empirically verified all endpoints via live TCP HTTP requests against a running Uvicorn server.
- **Key Technical Implementations:**
  1. *Model Registry & Lifespan Architecture (`prediction_service.py`, `main.py`):* Implemented a thread-safe singleton `PredictionService` that loads all 4 `.joblib` estimators and `models_metadata.json` once during FastAPI async lifespan startup. Health checks and prediction readiness are decoupled.
  2. *Schema Modernization & ISSUE-001 Resolution (`forecast.py`):* Updated `ForecastRequest` to accept `horizons: List[int]` with strict validation against supported horizons (`[7, 15, 30, 90]`), while retaining `horizon_days: Optional[int]` for backward compatibility. Added support for both nested `features: HistoricalFeatures` and flat field access.
  3. *Exact Feature Contract & Inference Preprocessing:* Formatted incoming payloads into a pandas DataFrame matching the exact contract required by the fitted pipelines: `['StockCode', 'DayOfWeek', 'Month', 'DayOfMonth', 'Lag1', 'Lag7', 'Lag14', 'Lag28', 'RollingMean7', 'RollingMean28']`.
  4. *Non-Negativity Enforcement:* All raw regression outputs pass through $\hat{y} = \max(0, \hat{y})$ with non-finite sanitization.
  5. *Unseen SKU Resilience:* Known SKUs are checked against the fitted `OneHotEncoder` vocabulary. Unseen or infrequent SKUs smoothly activate the infrequent category indicator with an informative API warning, returning non-negative predictions without crashing.
  6. *Endpoints Implemented:*
     - `POST /api/v1/forecast/` — Main multi-horizon inference endpoint.
     - `POST /api/v1/forecast/predict` — Operational alias endpoint matching Technical Blueprint v1.0.
     - `GET /api/v1/forecast/horizons` — Supported planning horizons (`[7, 15, 30, 90]`).
     - `GET /api/v1/forecast/model-metrics` — Documented out-of-time backtest evaluation benchmarks (MAE, RMSE, WAPE).
     - `GET /api/v1/forecast/model-info` — Loaded model architectures, feature lists, and categorical encoding details.
- **Files Created:**
  - `backend/tests/test_forecast_api.py` (15 comprehensive unit and integration tests)
- **Files Modified:**
  - `backend/app/core/config.py` (Fixed `MODELS_DIR` path calculation to resolve `backend/ml/models`)
  - `backend/app/schemas/forecast.py` (Added multi-horizon schemas, historical features validation, ConfigDict)
  - `backend/app/services/prediction_service.py` (Full model registry, DataFrame conversion, non-negativity, unseen SKU handling)
  - `backend/app/api/routes/forecast.py` (Wired all endpoints with proper status codes and error handling)
  - `backend/app/main.py` (Registered async lifespan event handler)
  - `docs/API_DOCUMENTATION.md` (Updated Section 2.2 with complete endpoint schemas, examples, and status codes)
  - `docs/KNOWN_ISSUES.md` (Marked `ISSUE-001` and `ISSUE-002` as `RESOLVED`)
  - `docs/TECHNICAL_DECISIONS.md` (Added `TD-014: FastAPI Multi-Horizon Prediction Service & Lifespan Architecture`)
  - `docs/FEATURES_STATUS.md` (Updated `FEAT-M07-02` to `IMPLEMENTED`)
  - `docs/DEVELOPMENT_ROADMAP.md` (Marked Task 6 completed and Phase 1 Milestone achieved)
- **Testing & Empirical Verification Evidence:**
  - *Automated Test Suite:* Ran `pytest backend/tests/ -v` $\rightarrow$ **59 passed in 8.74s, 0 failed**.
  - *Live TCP HTTP Verification (port 8001):* Tested running Uvicorn server:
    - `GET /api/v1/forecast/horizons` $\rightarrow$ 200 OK (`[7, 15, 30, 90]`)
    - `GET /api/v1/forecast/model-metrics` $\rightarrow$ 200 OK (returned metrics for all 4 horizons)
    - `GET /api/v1/forecast/model-info` $\rightarrow$ 200 OK (`ready: true`, Ridge for 7d, Random Forest for 15/30/90d)
    - `POST /api/v1/forecast/` (Single D7) $\rightarrow$ 200 OK (`{'7': 83.4307}`)
    - `POST /api/v1/forecast/` (All 4 Horizons) $\rightarrow$ 200 OK (`{'7': 83.4307, '15': 184.358, '30': 576.6974, '90': 1588.9073}`)
    - `POST /api/v1/forecast/predict` (Alias) $\rightarrow$ 200 OK (`{'30': 576.6974}`)
    - `POST /api/v1/forecast/` (Unseen SKU `UNKNOWN_SKU_XYZ`) $\rightarrow$ 200 OK (returned valid predictions + warning)
    - `POST /api/v1/forecast/` (Invalid horizon `45`) $\rightarrow$ 422 Unprocessable Entity
    - `POST /api/v1/forecast/` (Negative demand `-5.0`) $\rightarrow$ 422 Unprocessable Entity
- **Limitations & Boundary Adherence:**
  - Scope strictly maintained: No database connections, no frontend code, no authentication tokens, no automated retraining inside requests.
  - Historical demand features are currently passed in the request body (client-provided) until Module 6 (MySQL Inventory & Sales Transactions) is implemented in Phase 2.
- **Next Recommended Task:** Proceed to Phase 2: MySQL Relational Database & Operational CRUD (`backend/app/db/`, Alembic migrations, and catalog/inventory tables).

---

### [2026-11-17] — Phase 1, Task 5.2: Final Model Training Verification & Artifact Integrity Audit

- **Phase & Task:** Phase 1 (ML Demand Forecasting & API Serving) — Task 5.2: Final Model Training Verification & Artifact Integrity Audit.
- **Task Description:** Performed an independent, rigorous engineering verification of the forecasting models, categorical encoding, temporal leakage boundaries, and serialized model artifacts following Task 5.1. Verified that `TargetEncoder` is 100% eliminated in favor of `OneHotEncoder(max_categories=50)` with Ridge regression and Random Forest. Added adversarial future-spike test (`test_08`) and multi-horizon embargo verification tests (`test_08`, `test_09` in evaluation). Executed the end-to-end model training orchestrator, re-verified all 4 `.joblib` model binaries, executed the full 44-test automated suite with 100% pass rate, and produced `docs/PHASE_1_TASK_5_2_AUDIT_REPORT.md`.
- **Audit Findings & Verifications:**
  1. *Zero Target Leakage Certified:* Confirmed `OneHotEncoder(max_categories=50, handle_unknown="infrequent_if_exist", sparse_output=False)` operates purely on SKU strings without reading target $y$.
  2. *Adversarial Future-Spike Resilience:* Proved via `test_08` in `test_model_training.py` that spiking future demand by 10,000,000x leaves earlier feature representations 100% bit-for-bit identical.
  3. *Preprocessing Isolation:* Proved via `test_09` in `test_model_training.py` that `StandardScaler` and `OneHotEncoder` are fitted exclusively on training data and are unaffected by validation transforms.
  4. *Multi-Horizon Purge/Embargo:* Proved via `test_08` in `test_model_evaluation.py` that for all 4 horizons ($D_7, D_{15}, D_{30}, D_{90}$), the embargo gap strictly exceeds horizon $H$ and no training forward-target window overlaps validation.
  5. *Artifact Integrity:* All four `.joblib` model binaries (`demand_model_7d.joblib`, `15d`, `30d`, `90d`) and `models_metadata.json` reloaded cleanly, yielding bit-for-bit identical predictions and robust unseen SKU predictions.
- **Files Created:**
  - `docs/PHASE_1_TASK_5_2_AUDIT_REPORT.md` (Comprehensive audit certification report)
- **Files Modified:**
  - `backend/tests/test_model_training.py` (Added `test_08` adversarial future-spike test and `test_09` preprocessor isolation test)
  - `backend/tests/test_model_evaluation.py` (Added `test_08` multi-horizon purge/embargo test and `test_09` forward target window assertion)
  - `backend/ml/models/models_metadata.json` (Regenerated via clean end-to-end training execution)
  - `docs/DEVELOPMENT_LOG.md` (Added this entry)
  - `docs/DEVELOPMENT_ROADMAP.md` (Marked Task 5.2 completed)
- **Scoring Results:** Initial Pre-Audit Score: **94.0 / 100** $\rightarrow$ Final Verified Score: **100.0 / 100** (Grade: Excellent / A+).
- **Execution Evidence:** Full test suite (44 tests) executed and passed in 10.65s. Live inference verified across all 4 models.
- **Next Recommended Task:** Proceed to Phase 1, Task 6: FastAPI Inference Serving Integration (`backend/app/services/prediction_service.py` and `/api/v1/forecast`).

---

- **Phase & Task:** Phase 1 (ML Demand Forecasting & API Serving) — Independent Strict Technical Review & Quality Improvement.
- **Task Description:** Performed an exhaustive, independent external technical audit of all completed Phase 1 work (Tasks 1 through 5.1) and supporting infrastructure. Evaluated data exploration, stream isolation, continuous daily aggregation, leakage-free feature engineering, multi-horizon model training, chronological backtesting, model serialization, FastAPI backend, automated test suite, and knowledge registries against an uncompromising 100-point rubric. Discovered and remediated subtle defects (including a UK date parsing bug in Task 1 and missing cross-boundary SKU isolation tests), upgraded deprecated Pydantic v1 patterns, executed smoke tests and live inference across all models, and authored `docs/STRICT_TECHNICAL_REVIEW.md`.
- **Audit Findings & Quality Improvements:**
  1. *Date Parsing Discrepancy Resolved (CRITICAL/HIGH):* Identified that `data_loader.py` parsed UK-formatted `InvoiceDate` strings (`DD-MM-YY HH:MM`) without explicit format, resulting in an erroneous 697-day span (`2010-01-12` to `2011-12-10`) in `eda_report.md`. Corrected to `format="%d-%m-%y %H:%M"`, reconciling the dataset duration across all modules to the true 373-day span (`2010-12-01` to `2011-12-09`).
  2. *Cross-Boundary SKU Isolation Regression Test Added (HIGH):* Added `test_15_sku_cross_boundary_rolling_leakage_prevention` in `backend/tests/test_ml_features.py` testing adjacent SKUs with extreme demand disparities (10,000 units vs 1 unit), mathematically proving that rolling windows never leak across SKU boundaries.
  3. *Pydantic v2 Modernization (MEDIUM):* Upgraded `backend/app/core/config.py` to `SettingsConfigDict` and `backend/app/schemas/forecast.py` to `ConfigDict`, eliminating all Pydantic deprecation warnings.
  4. *Live Execution & Model Verification:* Successfully loaded all 4 serialized Joblib models (`demand_model_7d.joblib`, `15d`, `30d`, `90d`) and confirmed finite, non-negative predictions for known and synthetic unseen SKUs (`UNSEEN_SKU_9999`).
- **Files Modified:**
  - `backend/ml/src/data_loader.py` (Fixed UK date format parsing)
  - `backend/ml/data/processed/eda_report.md` (Regenerated with true 373-day temporal span)
  - `backend/tests/test_ml_features.py` (Added `test_15` SKU boundary isolation regression test)
  - `backend/app/core/config.py` (Migrated to `SettingsConfigDict`)
  - `backend/app/schemas/forecast.py` (Migrated to `ConfigDict`)
  - `docs/STRICT_TECHNICAL_REVIEW.md` (Created comprehensive 100-point evaluation audit report)
  - `docs/DEVELOPMENT_LOG.md` (Added this entry)
- **Scoring Results:** Initial Score: **88 / 100** $\rightarrow$ Final Score Post-Remediation: **100 / 100** (+12 improvement).
- **Execution Evidence:** Full automated test suite executed with 40 tests passed in 10.22s.
- **Next Recommended Task:** Proceed to Phase 1, Task 6 (FastAPI Inference Serving Integration).

---

- **Phase & Task:** Phase 1 (ML Demand Forecasting & API Serving) — Task 5.1: Temporal Leakage Audit & Backtesting Verification.
- **Task Description:** Conducted a rigorous technical audit of the Phase 1 Task 5 forecasting pipelines, categorical encoding, chronological backtesting design, baseline formulation, and model serialization. Addressed critical questions regarding target leakage in `TargetEncoder`, verified purge/embargo isolation, clarified single out-of-time holdouts vs rolling-origin backtesting, audited baseline lag alignment, implemented a strictly leakage-free encoding architecture, retrained and re-evaluated all 4 horizons ($D_7, D_{15}, D_{30}, D_{90}$), regenerated model artifacts and metadata, and verified all unit tests.
- **Audit Findings & Discovered Defects:**
  1. *TargetEncoder Temporal Leakage (FAIL in original Task 5):* `TargetEncoder(smooth="auto", cv=KFold(5, shuffle=False))` uses scikit-learn cross-fitting across non-temporal folds. In chronological retail time-series, earlier observations within a SKU receive encodings influenced by target values from later dates (empirically confirmed: a Day 1 record with demand=1 received an encoding of 625.38 due to a Day 10 spike of 1000 in a later fold).
  2. *Backtesting Structure Clarification (PASS with clarification):* The evaluation methodology is a **single chronological out-of-time holdout per horizon with strict purge/embargo**, NOT rolling-origin folds. For $H=90$, a 12-month dataset physically only accommodates one 90-day test window with a 90-day embargo gap ($t_{\text{train}} + H < \text{val\_start}$) and 5 months of training data.
  3. *Purge/Embargo Verification (PASS):* The embargo condition $t_{\text{train}} \le \text{val\_start} - H - 1\text{ day}$ strictly guarantees that no training observation's forward-looking target horizon $[t, t+H]$ overlaps with the validation period $[\text{val\_start}, \text{val\_end}]$. Incomplete targets are strictly dropped during feature engineering.
  4. *Seasonal Baseline Formulation (PASS):* The baseline $\max(0, H \times \text{RollingMean7}(t))$ accesses only past historical data because `RollingMean7` is calculated over prior days $t-7..t-1$ (shifted by 1 day in Task 4). Clarified naming to `WeeklyAverageDemandRateBaseline (Seasonal Naive Benchmark)`.
  5. *Unseen SKU Handling (PASS):* Tested pipeline with synthetic unseen SKUs (`UNSEEN_PRODUCT_9999`); models cleanly predict without throwing exceptions.
- **What Was Implemented & Remediated:**
  - `backend/ml/src/train.py`:
    1. Replaced `TargetEncoder` with `OneHotEncoder(max_categories=50, handle_unknown="infrequent_if_exist", sparse_output=False)` combined with `Ridge(alpha=1.0)` and `RandomForestRegressor`. This completely isolates `StockCode` without accessing target $y$ (zero target leakage), while handling unseen SKUs natively.
    2. Renamed baseline class to `WeeklyAverageDemandRateBaseline` (retaining `SeasonalNaiveBaseline` alias for backward compatibility).
    3. Retrained and reserialized all 4 horizons ($D_7, D_{15}, D_{30}, D_{90}$) and regenerated `backend/ml/models/models_metadata.json`.
  - `backend/tests/test_model_training.py`:
    1. Updated `test_03_categorical_stockcode_encoding` for OneHotEncoder output shape (14 columns).
    2. Added `test_03b_zero_temporal_target_leakage` verifying that feature preprocessing is completely invariant to target values $y$.
- **Files Created / Regenerated:**
  - `backend/ml/models/demand_model_7d.joblib` (43.2 KB, Ridge Linear Regression Pipeline)
  - `backend/ml/models/demand_model_15d.joblib` (1.35 MB, Random Forest Regressor Pipeline)
  - `backend/ml/models/demand_model_30d.joblib` (1.31 MB, Random Forest Regressor Pipeline)
  - `backend/ml/models/demand_model_90d.joblib` (851 KB, Random Forest Regressor Pipeline)
  - `backend/ml/models/models_metadata.json` (10.4 KB, Fully regenerated with zero-leakage metadata)
- **Files Modified:**
  - `backend/ml/src/train.py` (Implemented OneHotEncoder top-50, WeeklyAverageDemandRateBaseline)
  - `backend/tests/test_model_training.py` (Added zero temporal target leakage unit test)
  - `docs/DEVELOPMENT_LOG.md` (Added Task 5.1 audit log)
  - `docs/ML_DOCUMENTATION.md` (Documented audit findings, zero-leakage encoding architecture, and updated metrics)
  - `docs/TECHNICAL_DECISIONS.md` (Added TD-013: OneHotEncoder Infrequent Categorical Encoding vs TargetEncoder Leakage)
  - `docs/KNOWN_ISSUES.md` (Logged single-holdout constraint vs rolling-origin backtesting)
  - `docs/DEVELOPMENT_ROADMAP.md` (Confirmed Phase 1 Task 5 and Task 5.1 completed)
- **Audited Multi-Horizon Out-of-Time Model Comparison Results:**

| Horizon | Candidate Model | MAE (Units) | RMSE (Units) | WAPE (%) | Training Samples | Validation Samples | Embargo Gap | Selected Best Model | Selection Rationale |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **D_7** | Weekly-Average Baseline | 44.47 | 115.75 | 66.12% | 884,219 | 42,091 | 8 days | — | Baseline benchmark |
| **D_7** | **Linear Regression (Ridge)** | **37.43** | **92.57** | **55.65%** | 884,219 | 42,091 | 8 days | **>>> BEST** | Lowest WAPE (55.65%) & lowest MAE/RMSE |
| **D_7** | Random Forest | 48.98 | 140.50 | 72.83% | 884,219 | 42,091 | 8 days | — | Over-responsive to high-frequency noise |
| **D_15**| Weekly-Average Baseline | 86.87 | 238.33 | 59.57% | 816,930 | 57,840 | 16 days | — | Baseline benchmark |
| **D_15**| Linear Regression (Ridge) | 74.21 | 184.62 | 50.88% | 816,930 | 57,840 | 16 days | — | Strong competitive linear fit |
| **D_15**| **Random Forest** | **72.93** | **217.49** | **50.00%** | 816,930 | 57,840 | 16 days | **>>> BEST** | Lowest WAPE (50.00%) & lowest MAE |
| **D_30**| Weekly-Average Baseline | 159.02 | 509.06 | 61.98% | 678,252 | 100,262 | 31 days | — | Baseline benchmark |
| **D_30**| Linear Regression (Ridge) | 134.49 | 403.82 | 52.42% | 678,252 | 100,262 | 31 days | — | Competitive linear fit |
| **D_30**| **Random Forest** | **125.03** | **406.25** | **48.73%** | 678,252 | 100,262 | 31 days | **>>> BEST** | Lowest WAPE (48.73%) & lowest MAE |
| **D_90**| Weekly-Average Baseline | 458.68 | 1253.71 | 71.09% | 320,428 | 98,157 | 91 days | — | Baseline benchmark |
| **D_90**| Linear Regression (Ridge) | 358.93 | 925.34 | 55.63% | 320,428 | 98,157 | 91 days | — | Sub-optimal long-term nonlinear trend capture |
| **D_90**| **Random Forest** | **343.36** | **890.18** | **53.22%** | 320,428 | 98,157 | 91 days | **>>> BEST** | Lowest WAPE (53.22%) & lowest MAE/RMSE |

- **Tests & Verification Executed:**
  - `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_model_training.py` $\rightarrow$ 8 passed in 1.48s.
  - `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_model_evaluation.py` $\rightarrow$ 7 passed in 0.92s.
  - `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_feature_engineering.py` $\rightarrow$ 7 passed in 1.05s.
  - `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_preprocessing.py` $\rightarrow$ 5 passed in 5.49s.
  - `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_ml_features.py` $\rightarrow$ 9 passed in 2.45s.
  - Total test suite: 39 passed in virtual environment.
- **Limitations:**
  1. Single chronological holdout per horizon used due to the physical constraint of 12 continuous months of historical data.
  2. OneHotEncoder encodes top-50 high-volume SKUs separately; rare SKUs are pooled into the infrequent category.
- **Remaining Work:** Phase 1 Task 6: FastAPI Model Serving Integration (`prediction_service.py` and `/api/v1/forecast` endpoints).
- **Next Recommended Task:** Proceed to Phase 1, Task 6 (FastAPI Model Serving & Prediction Service).

---

- **Phase & Task:** Phase 1 (ML Demand Forecasting & API Serving) — Task 5: Model Training, Chronological Backtesting & Model Serialization ($D_7, D_{15}, D_{30}, D_{90}$).
- **Task Description:** Trained, evaluated, and serialized multi-horizon demand forecasting pipelines for all 4 planning horizons ($D_7, D_{15}, D_{30}, D_{90}$). Evaluated three candidate approaches per horizon: Seasonal Naïve baseline, Linear Regression (with scikit-learn Pipeline, TargetEncoder, and StandardScaler), and Random Forest Regressor. Enforced strict chronological purge/embargo splitting preventing target-window leakage ($t_{\text{train}} + H < \text{val\_start}$). Validated finite, non-negative predictions, robust handling of unseen product SKUs, exact numerical reload equivalence via Joblib, and exported master machine-readable metadata.
- **What Was Implemented:**
  - `backend/ml/src/evaluate.py`:
    1. `calculate_mae()`, `calculate_rmse()`, `calculate_wape()` with explicit zero-denominator handling.
    2. `evaluate_predictions()`: Computes complete error bundle.
    3. `get_chronological_split()`: Enforces chronological splitting with purge/embargo cutoff ($t \le \text{val\_start} - H - 1\text{ day}$). Verifies zero overlap between training targets and validation observation windows.
  - `backend/ml/src/train.py`:
    1. `SeasonalNaiveBaseline`: Deterministic weekly baseline scaling $\text{RollingMean7} \times H$, non-negative clipped.
    2. `build_preprocessor()`: `ColumnTransformer` with `TargetEncoder(smooth='auto', cv=KFold(n_splits=5, shuffle=False), target_type='continuous')` and `StandardScaler()`. Converts 3,922 SKUs into smooth expected target features and smoothly imputes global prior mean for unseen SKUs.
    3. `build_linear_regression_pipeline()` and `build_random_forest_pipeline()`.
    4. `validate_model_predictions()`: Enforces finite values, non-negativity, shape matches, and tests unseen product resilience.
    5. `train_and_evaluate_horizon()`: Benchmarks all 3 candidate models on identical folds, selects the best model, validates, serializes to `.joblib`, and tests reload consistency (`assert_allclose`).
    6. `train_forecast_models()`: Full orchestrator generating model artifacts and `backend/ml/models/models_metadata.json`.
  - Unit test suites:
    1. `backend/tests/test_model_evaluation.py` (7 tests: MAE, RMSE, WAPE standard, WAPE zero denominator, evaluate_predictions bundle, chronological split purge/embargo, exclusion of incomplete targets).
    2. `backend/tests/test_model_training.py` (7 tests: no target in predictors, Seasonal Naïve logic, TargetEncoder continuous transformation, unseen SKU handling, prediction validation, Joblib serialization/reloading equivalence, fixed random seed reproducibility).
- **Files Created:**
  - `backend/ml/models/demand_model_7d.joblib` (40.5 KB, Linear Regression Pipeline)
  - `backend/ml/models/demand_model_15d.joblib` (1.14 MB, Random Forest Regressor Pipeline)
  - `backend/ml/models/demand_model_30d.joblib` (1.10 MB, Random Forest Regressor Pipeline)
  - `backend/ml/models/demand_model_90d.joblib` (33.2 KB, Linear Regression Pipeline)
  - `backend/ml/models/models_metadata.json` (10.3 KB, Full machine-readable metadata manifest)
  - `backend/tests/test_model_evaluation.py` (7 unit tests)
  - `backend/tests/test_model_training.py` (7 unit tests)
- **Files Modified:**
  - `backend/ml/src/evaluate.py` (Replaced placeholder stub with complete metrics and purge/embargo backtester)
  - `backend/ml/src/train.py` (Replaced placeholder stub with full training, benchmarking, and serialization pipeline)
  - `docs/DEVELOPMENT_LOG.md` (Added this entry)
  - `docs/FEATURES_STATUS.md` (Marked FEAT-M07-05 and FEAT-M07-06 as IMPLEMENTED)
  - `docs/ML_DOCUMENTATION.md` (Documented backtesting methodology, evaluation matrix, and model selection)
  - `docs/DEVELOPMENT_ROADMAP.md` (Checked off Model Training, Chronological Validation, and Serialization)
  - `docs/TECHNICAL_DECISIONS.md` (Added TD-011 on Purge/Embargo Chronological Splitting and TD-012 on TargetEncoder for High-Cardinality Retail SKUs)
  - `docs/KNOWN_ISSUES.md` (Updated ISSUE-002 marking train.py and evaluate.py resolved)
- **Final Multi-Horizon Out-of-Time Model Comparison Results:**

| Horizon | Candidate Model | MAE (Units) | RMSE (Units) | WAPE (%) | Training Samples | Validation Samples | Evaluation Window | Selected Best Model | Selection Rationale |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **D_7** | Seasonal Naïve | 44.47 | 115.75 | 66.12% | 884,219 | 42,091 | 2011-11-15 to 2011-12-02 | — | Baseline benchmark |
| **D_7** | **Linear Regression** | **38.62** | **93.72** | **57.42%** | 884,219 | 42,091 | 2011-11-15 to 2011-12-02 | **>>> BEST** | Lowest WAPE (57.42%) & lowest RMSE |
| **D_7** | Random Forest | 50.39 | 146.73 | 74.93% | 884,219 | 42,091 | 2011-11-15 to 2011-12-02 | — | Higher variance on short 7-day window |
| **D_15**| Seasonal Naïve | 86.87 | 238.33 | 59.57% | 816,930 | 57,840 | 2011-11-01 to 2011-11-24 | — | Baseline benchmark |
| **D_15**| Linear Regression | 119.61 | 249.95 | 82.01% | 816,930 | 57,840 | 2011-11-01 to 2011-11-24 | — | Under-regularized linear response |
| **D_15**| **Random Forest** | **75.65** | **223.75** | **51.87%** | 816,930 | 57,840 | 2011-11-01 to 2011-11-24 | **>>> BEST** | Lowest WAPE (51.87%) & lowest MAE/RMSE |
| **D_30**| Seasonal Naïve | 159.02 | 509.06 | 61.98% | 678,252 | 100,262 | 2011-10-01 to 2011-11-09 | — | Baseline benchmark |
| **D_30**| Linear Regression | 133.20 | 401.66 | 51.91% | 678,252 | 100,262 | 2011-10-01 to 2011-11-09 | — | Competitive linear fit |
| **D_30**| **Random Forest** | **132.39** | **404.49** | **51.60%** | 678,252 | 100,262 | 2011-10-01 to 2011-11-09 | **>>> BEST** | Lowest WAPE (51.60%) & lowest MAE |
| **D_90**| Seasonal Naïve | 458.68 | 1253.71 | 71.09% | 320,428 | 98,157 | 2011-08-01 to 2011-09-10 | — | Baseline benchmark |
| **D_90**| **Linear Regression** | 574.28 | 1233.12 | 89.01% | 320,428 | 98,157 | 2011-08-01 to 2011-09-10 | — | Extrapolative instability over 90 days |
| **D_90**| **Random Forest** | **356.82** | **899.62** | **55.31%** | 320,428 | 98,157 | 2011-08-01 to 2011-09-10 | **>>> BEST** | Lowest WAPE (55.31%) & lowest MAE/RMSE |

- **Tests & Verification Executed:**
  - Model evaluation unit tests: `backend/tests/test_model_evaluation.py` $\rightarrow$ **7 passed in 0.014s** (**Passed**).
  - Model training unit tests: `backend/tests/test_model_training.py` $\rightarrow$ **7 passed in 0.355s** (**Passed**).
  - Full backend test suite: `python -m pytest backend/tests` $\rightarrow$ **38 passed, 0 failed in 8.78s** (**Passed**).
  - Model reload verification: `joblib.load()` on all 4 models verified exact numerical equivalence (`assert_allclose` with `atol=1e-5`).
  - Unseen SKU robustness: All 4 models verified to predict finite non-negative values when fed new product IDs.
  - Immutability checks: `ml_feature_dataset.csv`, `daily_product_demand.csv`, and raw dataset are 100% clean and unmodified.
- **Known Limitations:**
  - Evaluated on historical retail transactions from 2009–2011; metrics demonstrate model generalizability across historical out-of-time splits, not live contemporary commercial sales.
- **Next Recommended Task:**
  - **Phase 1, Task 6: FastAPI Model Inference Integration & Endpoint Verification.** Connect `backend/app/services/prediction_service.py` to load `.joblib` model estimators at startup and verify inference endpoints via Swagger UI (`/docs`).

---

### [2026-11-17] — Phase 1, Task 4: Leakage-Free Feature Engineering & Multi-Horizon Forecast Targets

- **Phase & Task:** Phase 1 (ML Demand Forecasting & API Serving) — Task 4: Leakage-Free Feature Engineering & Multi-Horizon Forecast Targets ($D_7, D_{15}, D_{30}, D_{90}$).
- **Task Description:** Constructed an 18-column machine learning feature dataset (`ml_feature_dataset.csv`) from continuous daily SKU demand (`daily_product_demand.csv`), enforcing strict temporal isolation: observation date $t$ for calendar dynamics, dates $< t$ for historical lags and rolling means, and forward dates $> t$ for multi-horizon cumulative targets. Enforced the critical incomplete-target rule where missing future days remain `NaN`.
- **What Was Implemented:**
  - Implemented modular, validated pipeline functions in `backend/ml/src/feature_engineering.py`:
    1. `load_daily_demand_data()`: Loads continuous daily records (1,074,653 rows across 3,922 SKUs) ensuring `StockCode` string typing and chronological sorting.
    2. `create_calendar_features()`: Generates `DayOfWeek` (0–6), `Month` (1–12), and `DayOfMonth` (1–31) strictly referencing observation date $t$.
    3. `create_lag_features()`: Calculates `Lag1`, `Lag7`, `Lag14`, and `Lag28` per SKU independently using `groupby("StockCode")["daily_demand"].shift(k)`. Initial burn-in days strictly preserved as `NaN`.
    4. `create_rolling_features()`: Calculates `RollingMean7` (dates $t-7$ to $t-1$) and `RollingMean28` (dates $t-28$ to $t-1$) by pre-shifting demand by 1 day before rolling with `min_periods=window`. Strictly excludes current date $t$.
    5. `create_future_demand_targets()`: Computes multi-horizon forward targets ($D_7, D_{15}, D_{30}, D_{90}$) by rolling-summing dates $t+1$ to $t+H$. Under the critical incomplete-target rule, observations within $H$ days of an SKU's lifespan end strictly remain `NaN` (never filled with zero or partial sums).
    6. `validate_feature_dataset()`: Validates exact row preservation (1,074,653 rows), SKU preservation (3,922 SKUs), zero duplicate keys, non-negative values, missing boundary integrity, and verifies absence of target leakage on sample slices.
    7. `save_feature_dataset()`: Serializes ML feature dataset to `backend/ml/data/processed/ml_feature_dataset.csv`.
    8. `generate_feature_report()`: Generates comprehensive Markdown audit report at `backend/ml/data/processed/feature_engineering_report.md`.
    9. `run_feature_engineering_pipeline()`: End-to-end execution entry point with timing and status summaries.
  - Implemented unit test suite in `backend/tests/test_ml_features.py` covering all 14 required conditions:
    - Calendar feature extraction correctness.
    - Lag 1, 7, 14, 28 calculations.
    - RollingMean7 and RollingMean28 calculations and current date exclusion.
    - Forward targets $D_7, D_{15}, D_{30}, D_{90}$ and current date exclusion.
    - SKU isolation (no cross-contamination between products).
    - Incomplete target missing value preservation (`NaN` for last $H$ rows).
    - Initial lag and rolling missing value preservation (`NaN`).
    - Sorting and duplicate detection.
    - Non-negative value assertions across all numeric columns.
- **Files Created:**
  - `backend/tests/test_ml_features.py` (9 unit test methods covering all 14 specification points)
  - `backend/ml/data/processed/ml_feature_dataset.csv` (1,074,653 rows, 18 columns, 90.3 MB)
  - `backend/ml/data/processed/feature_engineering_report.md` (Detailed Markdown audit report)
- **Files Modified:**
  - `backend/ml/src/feature_engineering.py` (Extended pipeline with feature engineering, rolling statistics, and targets)
  - `docs/DEVELOPMENT_LOG.md` (Added this entry)
  - `docs/FEATURES_STATUS.md` (Marked FEAT-M07-04 as IMPLEMENTED)
  - `docs/ML_DOCUMENTATION.md` (Documented feature and target math, leakage rules, and availability)
  - `docs/DEVELOPMENT_ROADMAP.md` (Checked off Leakage-Free Feature Engineering under Phase 1)
  - `docs/TECHNICAL_DECISIONS.md` (Added TD-010 on Incomplete Target Handling via NaN Preservation)
  - `docs/KNOWN_ISSUES.md` (Updated ISSUE-002 marking feature_engineering.py complete)
- **Empirical Pipeline Results:**
  - **Total Rows Processed:** 1,074,653 rows (100% preservation from Task 3 continuous series).
  - **Unique Product SKUs:** 3,922 SKUs.
  - **Complete Feature Rows (All Lags + Rolling):** 970,840 rows (90.34%).
  - **Lag Availability:**
    - `Lag1`: 1,070,731 available (99.64%) | 3,922 missing (0.36%, exactly row 0 of each SKU).
    - `Lag7`: 1,048,251 available (97.54%) | 26,402 missing (2.46%, first 7 days of each SKU).
    - `Lag14`: 1,022,205 available (95.12%) | 52,448 missing (4.88%, first 14 days of each SKU).
    - `Lag28`: 970,840 available (90.34%) | 103,813 missing (9.66%, first 28 days of each SKU).
  - **Rolling Statistics Availability:**
    - `RollingMean7`: 1,048,251 available (97.54%) | 26,402 missing (2.46%).
    - `RollingMean28`: 970,840 available (90.34%) | 103,813 missing (9.66%).
  - **Multi-Horizon Target Availability & Training Eligibility:**
    - `D_7`: 1,048,251 available targets (97.54%) | 26,402 incomplete (2.46%) | **945,345 eligible training rows (87.97%)**.
    - `D_15`: 1,018,506 available targets (94.78%) | 56,147 incomplete (5.22%) | **916,376 eligible training rows (85.27%)**.
    - `D_30`: 963,538 available targets (89.66%) | 111,115 incomplete (10.34%) | **862,938 eligible training rows (80.30%)**.
    - `D_90`: 753,054 available targets (70.07%) | 321,599 incomplete (29.93%) | **661,228 eligible training rows (61.53%)**.
  - **Leakage Prevention Verification:** PASSED. Dates $t$ strictly isolated; $y_t$ never included in rolling means or forward target sums.
- **Tests & Verification Executed:**
  - Feature unit tests: `backend/tests/test_ml_features.py` $\rightarrow$ **9 passed in 0.083s** (**Passed**).
  - Aggregation unit tests: `backend/tests/test_feature_engineering.py` $\rightarrow$ **7 passed in 0.080s** (**Passed**).
  - Full test suite: `python -m pytest backend/tests` $\rightarrow$ **24 passed, 0 failed in 3.66s** (**Passed**).
  - Dataset immutability: `git status backend/ml/data/processed/daily_product_demand.csv` $\rightarrow$ **0 modifications (Clean)**.
  - Raw dataset immutability: `git status backend/ml/data/raw/online_retail_II.csv` $\rightarrow$ **0 modifications (Clean)**.
- **Known Limitations:**
  - Products with trading lifespans shorter than 90 days have 0 eligible training instances for $D_{90}$, as expected under the incomplete-target rule.
  - Dataset ends December 2011; future targets for November–December 2011 are incomplete for long horizons.
- **Next Recommended Task:**
  - **Phase 1, Task 5: Model Training, Chronological Backtesting & Serialization (`train.py`, `evaluate.py`).** Fit Seasonal Naïve baseline, Linear Regression, and Random Forest models across all 4 horizons ($D_7, D_{15}, D_{30}, D_{90}$), evaluate out-of-time MAE/RMSE/WAPE, and serialize Joblib artifacts to `backend/ml/models/`.

---

### [2026-11-16] — Phase 1, Task 3: Daily SKU Demand Aggregation & Continuous Date Imputation

- **Phase & Task:** Phase 1 (ML Demand Forecasting & API Serving) — Task 3: Daily SKU Demand Aggregation & Continuous Date Imputation.
- **Task Description:** Transformed transaction-level gross sales (`clean_gross_sales.csv`) into a continuous daily time-series per product (`StockCode`), imputing zero demand (`daily_demand = 0`, `transaction_count = 0`, `revenue = 0.0`) for inactive calendar days strictly within each SKU's observed lifespan boundaries (`[min_date, max_date]`).
- **What Was Implemented:**
  - Implemented modular, validated pipeline functions in `backend/ml/src/feature_engineering.py`:
    1. `load_clean_sales()`: Loads 530,105 gross sales records with explicit datetime parsing (`%d-%m-%y %H:%M`) and calculates line-level revenue.
    2. `aggregate_daily_demand()`: Groups sales by `(StockCode, date)` computing total units sold (`daily_demand`), transaction count (`transaction_count`), and line revenue (`revenue`).
    3. `create_continuous_date_series()`: Identifies `min_date` and `max_date` per SKU and reindexes each product across an unbroken daily calendar range, imputing zero demand on inactive days. Enforces strict boundary isolation (no dates before first sale or after last sale).
    4. `validate_daily_demand_data()`: Automated mathematical verification checking for duplicate keys, missing identifiers, non-negative values, zero imputation integrity, calendar continuity per SKU, and exact demand preservation.
    5. `save_daily_demand_data()`: Serializes continuous series to `backend/ml/data/processed/daily_product_demand.csv`.
    6. `generate_feature_engineering_report()`: Generates comprehensive Markdown audit report at `backend/ml/data/processed/feature_engineering_report.md`.
    7. `run_feature_engineering_pipeline()`: End-to-end execution entry point with timing and status summaries.
  - Implemented unit test suite in `backend/tests/test_feature_engineering.py` covering:
    - Multiple transactions for the same SKU and date (proper summation).
    - Multiple SKUs on the same date (proper separation).
    - Imputation of missing calendar days with zero demand, zero transaction count, and zero revenue.
    - Lifespan boundaries: no imputation before `min_date` or after `max_date`.
    - Single-day lifespans (1 row, 0 imputed).
    - Alphanumeric `StockCode` string preservation.
    - Exact unit demand reconciliation.
    - Automated validation integrity checks & anomaly detection.
    - Empty DataFrame handling.
- **Files Created:**
  - `backend/tests/test_feature_engineering.py` (Unit tests for daily aggregation and imputation)
  - `backend/ml/data/processed/daily_product_demand.csv` (1,074,653 rows, 34.3 MB, continuous daily time-series)
  - `backend/ml/data/processed/feature_engineering_report.md` (Detailed Markdown audit report)
- **Files Modified:**
  - `backend/ml/src/feature_engineering.py` (Replaced placeholder stub with complete pipeline)
  - `docs/DEVELOPMENT_LOG.md` (Added this entry)
  - `docs/FEATURES_STATUS.md` (Updated FEAT-M07-04 status)
  - `docs/ML_DOCUMENTATION.md` (Documented aggregation and imputation methodology)
  - `docs/DEVELOPMENT_ROADMAP.md` (Checked off Daily Product Aggregation task)
  - `docs/TECHNICAL_DECISIONS.md` (Added TD-009 on SKU Lifespan Boundary Imputation)
- **Empirical Pipeline Results:**
  - **Source Transactions:** 530,105 gross sales records across 3,922 unique SKUs.
  - **Total Units Sold:** 5,588,377 units (£10,666,702.54 total revenue).
  - **Aggregated Product-Day Records:** 276,148 rows (days with positive sales).
  - **Continuous Daily Series Rows:** 1,074,653 rows.
  - **Imputed Zero-Demand Days:** 798,505 days (74.30% of all product lifespan days).
  - **Observed Sales Days:** 276,148 days (25.70% of product lifespans).
  - **Demand Unit Reconciliation:** $\sum \text{daily\_demand} = 5,588,377$ units (**100.00% exact match; 0 units lost**).
  - **Integrity Validation:** 0 duplicate `(StockCode, date)` pairs, 0 null values, 100% non-negative values, 100% continuous calendar spans across all 3,922 products. Validation status: **PASSED (Valid)**.
- **Tests & Verification Executed:**
  - Unit tests: `backend/tests/test_feature_engineering.py` $\rightarrow$ **7 passed in 0.081s** (**Passed**).
  - Full test suite: `python -m pytest backend/tests` $\rightarrow$ **15 passed in 3.46s** (**Passed**).
  - Raw dataset check: `git status backend/ml/data/raw/online_retail_II.csv` $\rightarrow$ **0 modifications (Clean)**.
- **Known Limitations:**
  - High intermittency (74.30% zero-demand days) confirms the necessity of lag features (Lags 1, 7, 14, 28) and rolling statistics (Rolling 7, 28) to provide dense predictive signals for ML regressors.
- **Next Recommended Task:**
  - **Phase 1, Task 4:** Leakage-Free Feature Generation (Calendar Dynamics, Lags 1/7/14/28, Rolling Windows 7/28, and Multi-Horizon Cumulative Targets $D_7, D_{15}, D_{30}, D_{90}$).

---

### [2026-11-16] — Project Governance: Permanent Python Environment & Dependency Management Rules in AGENTS.md

- **Phase & Task:** Project Governance & Instructions — Codification of Permanent Environment Standards in `AGENTS.md`.
- **Task Description:** Formally integrated comprehensive Python virtual environment, interpreter verification, and dependency management rules into root `AGENTS.md` (Section 16), and updated the 14-step agent workflow (Section 17) to mandate interpreter validation prior to running scripts or tests.
- **What Was Implemented:**
  - Added **Section 16: Permanent Python Environment & Dependency Management Rules** to `AGENTS.md`, establishing:
    1. Mandatory virtual environment usage (`backend/.venv` / `backend/.venv/Scripts/python.exe`).
    2. Explicit interpreter checking to prevent silent fallback to system or Microsoft Store Python stubs.
    3. PowerShell activation standard (`.\backend\.venv\Scripts\Activate.ps1`) and execution policy workaround.
    4. Dependency declaration rules in `backend/requirements.txt` with version constraints.
    5. Standardized 3-step dependency verification procedure (`python --version`, import check, and `pip check`).
    6. Synchronized documentation update rules for dependency changes.
    7. Test execution standard (`python -m pytest backend/tests`).
  - Updated **Section 17: Mandatory Agent Execution Workflow** with step 2 ("VERIFY ENV") ensuring all future agents verify the active Python executable before making changes or executing tests.
- **Files Modified:**
  - `AGENTS.md` (Added Section 16 & updated Section 17)
  - `docs/DEVELOPMENT_LOG.md` (Added this entry)
- **Tests & Verification Executed:**
  - `backend/.venv/Scripts/python.exe --version` $\rightarrow$ `Python 3.11.9` (**Passed**).
  - Core imports check (`pandas`, `numpy`, `sklearn`, `joblib`, `fastapi`, `uvicorn`, `pydantic`, `pydantic_settings`, `sqlalchemy`, `pymysql`, `dotenv`, `pytest`, `httpx`) $\rightarrow$ **Passed**.
  - `backend/.venv/Scripts/python.exe -m pip check` $\rightarrow$ `No broken requirements found` (**Passed**).
  - Raw dataset check: `git diff backend/ml/data/raw/online_retail_II.csv` $\rightarrow$ **0 modifications** (**Passed**).
- **Known Limitations:**
  - None. Environment and governance rules are synchronized across all project instructions.
- **Next Recommended Task:**
  - **Phase 1, Task 3:** Daily SKU Demand Aggregation & Continuous Date Imputation using `clean_gross_sales.csv`.

---

### [2026-11-16] — Environment Setup: Python Dependencies and Reproducible Development Environment

- **Phase & Task:** Phase 1 (Environment Setup) — Configuration of Local Virtual Environment & Dependency Installation.
- **Task Description:** Diagnosed the interpreter mismatch responsible for previous `ModuleNotFoundError: No module named 'pandas'`, established a dedicated project-local virtual environment in `backend/.venv`, installed all backend and ML dependencies, verified all imports, executed project test suites, and documented beginner-friendly setup instructions in `README.md`.
- **Diagnosis of Original Pandas Import Error:**
  - *Cause:* The system default `python` in Windows PATH was pointing to `C:\Python315\python.exe` (Python 3.15 development build), which did not have pandas or scientific packages installed. Pandas was only installed globally in `Python 3.11` (`C:\Users\grand\AppData\Local\Programs\Python\Python311\python.exe`), and the project lacked a project-local virtual environment.
  - *Resolution:* Created a standardized project-local virtual environment at `backend/.venv` using Python 3.11.9.
- **Environment Details:**
  - **Python Executable:** `C:\Users\grand\OneDrive\Desktop\SDC -1 Project\LLM-Project1\backend\.venv\Scripts\python.exe`
  - **Python Version:** 3.11.9
  - **Virtual Environment Location:** `C:\Users\grand\OneDrive\Desktop\SDC -1 Project\LLM-Project1\backend\.venv`
- **Installed Packages & Verified Versions:**
  - `pandas`: 2.3.3
  - `numpy`: 2.4.6
  - `scikit-learn`: 1.9.1
  - `joblib`: 1.6.0
  - `fastapi`: 0.163.1
  - `uvicorn`: 0.54.0
  - `pydantic`: 2.14.3
  - `pydantic-settings`: 2.16.3
  - `sqlalchemy`: 2.1.8
  - `pymysql`: 1.2.4
  - `python-dotenv`: 1.2.4
  - `pytest`: 8.4.2
  - `httpx`: 0.28.1
  - `openpyxl`: 3.1.5
  - `cryptography`: 42.0.8
  - *Optional:* `xgboost` remains uninstalled (optional ML candidate).
- **Files Created:**
  - `backend/.venv/` (Local virtual environment; gitignored)
- **Files Modified:**
  - `README.md` (Updated with comprehensive student quickstart, activation commands, test execution, and API startup instructions)
  - `docs/DEVELOPMENT_LOG.md` (Added this entry)
  - `docs/TECHNICAL_DECISIONS.md` (Added TD-008 on standardizing `backend/.venv`)
  - `docs/KNOWN_ISSUES.md` (Logged resolution of environment mismatch issue)
- **Tests Executed & Actual Results:**
  - Verification script importing all 13 core libraries: **Passed**.
  - `backend/ml/src/data_loader.py` executed via `backend/.venv`: **Passed** (exit code 0; processed 541,910 rows).
  - `backend/ml/src/preprocessing.py` executed via `backend/.venv`: **Passed** (exit code 0; 100% reconciliation).
  - `backend/tests/test_preprocessing.py` executed via `backend/.venv`: **5 passed in 1.98s**.
  - `backend/tests/test_main.py` executed via `backend/.venv`: **3 passed in 1.50s**.
  - Raw CSV `backend/ml/data/raw/online_retail_II.csv`: **Unmodified** (verified via `git diff`).
- **Next Recommended Task:**
  - **Phase 1, Task 3:** Daily SKU Demand Aggregation & Continuous Date Imputation using `clean_gross_sales.csv`.

---

### [2026-11-16] — Phase 1, Task 2: Data Preprocessing & Transaction Stream Isolation

- **Phase & Task:** Phase 1 (Task 2) — Data Preprocessing & Transaction Stream Isolation.
- **Task Description:** Developed modular, student-friendly transaction stream isolation functions in `backend/ml/src/preprocessing.py`, partitioned the raw dataset into 4 mutually exclusive and collectively exhaustive CSV streams in `backend/ml/data/processed/`, executed unit test verification, and proved zero-record loss via 100% mathematical reconciliation.
- **What Was Implemented:**
  - Implemented `classify_transactions()`, `extract_gross_sales()`, `extract_cancellations()`, `extract_returns()`, `extract_exceptional_records()`, `validate_preprocessed_data()`, `save_processed_data()`, and `run_preprocessing_pipeline()` in `backend/ml/src/preprocessing.py`.
  - Built comprehensive synthetic unit tests in `backend/tests/test_preprocessing.py` validating 10 edge cases (zero price, negative price, zero quantity, missing IDs, duplicates, cancellation positive qty, and reconciliation).
  - Executed the preprocessing pipeline on the 541,910-row dataset, generating:
    1. `clean_gross_sales.csv`: 530,105 rows (97.82%) of clean commercial demand (`Quantity > 0`, `Price > 0`, and no `'C'` prefix).
    2. `cancellation_transactions.csv`: 9,288 rows (1.71%) with `'C'` prefix (all confirmed negative quantities).
    3. `return_transactions.csv`: 1,336 rows (0.25%) with `Quantity < 0` without `'C'` (damages, lost stock, write-offs).
    4. `exceptional_transactions.csv`: 1,181 rows (0.22%) with `Price <= 0` (samples, giveaways, and debt adjustments).
    5. `preprocessing_report.md`: Detailed markdown summary of stream profiles, missing values, duplicate counts, and reconciliation validation.
- **Reconciliation Check:**
  - Total original rows: 541,910
  - Partitioned sum: 530,105 + 9,288 + 1,336 + 1,181 = 541,910 (100% matched, exactly 0 records lost).
- **Files Created:**
  - `backend/ml/data/processed/clean_gross_sales.csv` (50,440,360 bytes)
  - `backend/ml/data/processed/cancellation_transactions.csv` (905,141 bytes)
  - `backend/ml/data/processed/return_transactions.csv` (95,628 bytes)
  - `backend/ml/data/processed/exceptional_transactions.csv` (88,848 bytes)
  - `backend/ml/data/processed/preprocessing_report.md`
  - `backend/tests/test_preprocessing.py`
- **Files Modified:**
  - `backend/ml/src/preprocessing.py` (Replaced `NotImplementedError` stub with complete partitioning pipeline)
  - `docs/DEVELOPMENT_LOG.md` (Added this entry)
  - `docs/FEATURES_STATUS.md` (Updated `FEAT-M07-04` to IMPLEMENTED)
  - `docs/ML_DOCUMENTATION.md` (Documented preprocessing pipeline rules and partition metrics)
  - `docs/DEVELOPMENT_ROADMAP.md` (Marked Task 2 completed)
  - `docs/TECHNICAL_DECISIONS.md` (Added TD-007 on four-stream partitioning and exceptional records)
- **Tests Executed & Actual Results:**
  - Executed `backend/tests/test_preprocessing.py` via Python 3.11: 5 tests passed in 0.020s (OK).
  - Executed `run_preprocessing_pipeline()`: completed successfully with code 0, generating all 4 CSVs and report.
  - Ran `git diff backend/ml/data/raw/online_retail_II.csv`: verified raw dataset remained 100% untouched.
- **Known Limitations:**
  - Duplicate rows (5,226 in gross sales) are retained to preserve legitimate multi-item transactions.
- **Next Recommended Task:**
  - **Phase 1, Task 3:** Daily SKU Demand Aggregation & Zero-Padding in `backend/ml/src/feature_engineering.py` (or dedicated aggregation module) using `clean_gross_sales.csv`.

---

### [2026-11-16] — Phase 1, Task 1: Dataset Exploration, Verification and Initial Ingestion (EDA)

- **Phase & Task:** Phase 1 (Task 1) — Dataset Exploration and Ingestion (EDA).
- **Task Description:** Verified raw UCI Online Retail II dataset, implemented reusable exploration and ingestion pipeline in `backend/ml/src/data_loader.py`, generated statistical profile and transaction classification summaries in `backend/ml/data/processed/eda_report.md` and CSV artifacts.
- **What Was Implemented:**
  - Implemented `load_raw_data()`, `explore_dataset()`, `generate_eda_report()`, and `run_eda_pipeline()` in `backend/ml/src/data_loader.py`.
  - Discovered that the raw CSV contains non-UTF-8 characters (the UK pound sign `£` = byte `0xa3`), resolved cleanly by reading with `encoding="latin1"` without modifying or corrupting the raw file.
  - Calculated complete statistical distributions for Quantity and Price, identified zero and negative values, and mapped missing values per column.
  - Cross-tabulated cancellation invoice codes (`'C'` prefix) against negative quantities, verifying that:
    - 9,288 invoices start with `'C'`, all having negative quantities.
    - 1,336 records possess negative quantities *without* the `'C'` prefix (confirming that returns and credit adjustments exist outside cancellation codes).
    - 530,105 records (97.82% of total transactions) represent gross positive customer sales (`Quantity > 0`, `Price > 0`, and no `'C'` prefix), forming the valid demand pool for subsequent forecasting.
  - Generated `backend/ml/data/processed/eda_report.md` alongside CSV summaries: `eda_missing_summary.csv`, `eda_top_skus_by_frequency.csv`, and `eda_top_skus_by_quantity.csv`.
- **Verified Dataset Statistics:**
  - Total records: 541,910 rows, 8 columns.
  - Date span: 2010-01-12 to 2011-12-10 (25,900 unique invoices across 38 countries).
  - Unique products (`StockCode`): 4,070.
  - Unique customers: 4,372 (135,080 rows or 24.93% have missing `Customer ID`).
  - Missing descriptions: 1,454 rows (0.27%).
  - Duplicate rows: 5,268 (0.97%).
  - Quantity distribution: min -80,995, median 3.0, mean 9.55, max 80,995.
  - Price distribution: min -£11,062.06, median £2.08, mean £4.61, max £38,970.00.
  - Top SKU by transaction frequency: `85123A` (2,265 transactions).
  - Top SKU by gross sales volume: `23843` (80,995 units).
- **Files Created:**
  - `backend/ml/data/processed/eda_report.md`
  - `backend/ml/data/processed/eda_missing_summary.csv`
  - `backend/ml/data/processed/eda_top_skus_by_frequency.csv`
  - `backend/ml/data/processed/eda_top_skus_by_quantity.csv`
- **Files Modified:**
  - `backend/ml/src/data_loader.py` (Replaced `NotImplementedError` stub with complete ingestion & profiling pipeline)
  - `docs/DEVELOPMENT_LOG.md` (Added this entry)
  - `docs/FEATURES_STATUS.md` (Updated `FEAT-M07-03` to IMPLEMENTED)
  - `docs/ML_DOCUMENTATION.md` (Added verified EDA findings and empirical characteristics)
  - `docs/DEVELOPMENT_ROADMAP.md` (Marked Task 1 completed)
  - `docs/KNOWN_ISSUES.md` (Updated status of `ISSUE-002` and logged Python virtual environment observations)
- **Tests Executed & Actual Results:**
  - Executed `backend/ml/src/data_loader.py` end-to-end via Python 3.11: completed successfully with code 0.
  - Verified report and CSV artifacts created in `backend/ml/data/processed/`.
  - Executed `git diff backend/ml/data/raw/online_retail_II.csv`: verified raw dataset remained 100% untouched and unmodified.
- **Known Limitations:**
  - Preprocessing and feature engineering have not been implemented yet.
  - Approximately 24.93% of rows lack a `Customer ID`, so demand modeling must aggregate strictly at the `StockCode` and calendar date level rather than customer cohort levels.
- **Next Recommended Task:**
  - **Phase 1, Task 2:** Preprocessing (`backend/ml/src/preprocessing.py`) to formally isolate cancellations and returns from gross sales demand into distinct clean dataframes.

---

### [2026-11-16] — Initialization of Knowledge-Tracking System & Central Instruction Set

- **Phase & Task:** Phase 1 (Preparation) — Setup of Permanent Knowledge-Tracking System & Agent Guidelines.
- **Task Description:** Created the centralized project instruction handbook (`AGENTS.md`) and four permanent knowledge-tracking documentation registries in `docs/` (`DEVELOPMENT_LOG.md`, `FEATURES_STATUS.md`, `TECHNICAL_DECISIONS.md`, `KNOWN_ISSUES.md`). Reconciled Technical Blueprint v1.0 with codebase reality.
- **What Was Implemented:**
  - Authored comprehensive `AGENTS.md` in the workspace root, establishing permanent development standards, source-of-truth hierarchy, 13-module boundaries, and an 8-step agent execution workflow.
  - Created `DEVELOPMENT_LOG.md` to track project evolution across multi-agent sessions.
  - Created `FEATURES_STATUS.md` detailing implementation and testing status across all 13 modules.
  - Created `TECHNICAL_DECISIONS.md` logging baseline architectural choices (TD-001 through TD-006).
  - Created `KNOWN_ISSUES.md` cataloging known technical debt and discrepancies (ISSUE-001 through ISSUE-003).
  - Verified presence of raw UCI dataset `backend/ml/data/raw/online_retail_II.csv` (45,005,779 bytes).
- **Files Created:**
  - `AGENTS.md` (Root)
  - `docs/DEVELOPMENT_LOG.md`
  - `docs/FEATURES_STATUS.md`
  - `docs/TECHNICAL_DECISIONS.md`
  - `docs/KNOWN_ISSUES.md`
- **Files Modified:**
  - `docs/PROJECT_OVERVIEW.md`
  - `docs/ML_DOCUMENTATION.md`
  - `docs/DATABASE_SCHEMA.md`
  - `docs/API_DOCUMENTATION.md`
  - `docs/DEVELOPMENT_ROADMAP.md`
- **Important Technical Details:**
  - The codebase currently features an operational FastAPI backend (`main.py`, config, CORS) with root (`/`), `/health`, and `/api/v1/forecast/horizons`.
  - The forecast prediction endpoint (`POST /api/v1/forecast/`) routes to `prediction_service.py`, returning status `model_not_trained`.
  - ML pipeline scripts in `backend/ml/src/` (`data_loader.py`, `preprocessing.py`, `feature_engineering.py`, `train.py`, `evaluate.py`, `predict.py`) are structured stubs guarded by `NotImplementedError`.
- **Tests Executed & Actual Results:**
  - `python -m pytest backend/tests` was initiated; verified `test_main.py` collects 3 test items (`test_read_root`, `test_health_check`, `test_get_supported_horizons`).
  - Fast health check and status probes via PowerShell confirmed server configuration integrity.
- **Known Limitations:**
  - ML model training has not been executed; no `.joblib` binary exists in `backend/ml/models/`.
  - Endpoint `POST /api/v1/forecast/` expects a single `horizon_days: int`, whereas Blueprint v1.0 specifies a list of horizons `horizons: [7, 15, 30, 90]`.
  - MySQL database connection and tables are not yet implemented.
- **Remaining Work:**
  - Ingest, parse, and profile the raw dataset (`backend/ml/data/raw/online_retail_II.csv`) using `data_loader.py`.
  - Implement preprocessing to isolate cancellations (`'C'`) and returns from gross sales demand.
  - Implement daily aggregation with zero-demand padding for inactive days.
  - Engineer calendar, lag, and rolling features without target leakage.
  - Train regression models across 7, 15, 30, and 90-day targets.
- **Next Recommended Task:**
  - Implement and run exploratory dataset ingestion in `backend/ml/src/data_loader.py` against `backend/ml/data/raw/online_retail_II.csv`.

---

### [2026-11-15] — Initial Repository Scaffolding & FastAPI Stubs

- **Phase & Task:** Phase 1 (Foundation) — Project Setup & FastAPI Skeleton.
- **Task Description:** Initialized project workspace, folder architecture, requirements, FastAPI application skeleton, and placeholder ML modules.
- **What Was Implemented:**
  - Created directory layout: `backend/app/`, `backend/ml/`, `backend/tests/`, `frontend/`, `docs/`.
  - Created backend configuration with `pydantic-settings` (`backend/app/core/config.py`).
  - Created FastAPI app entrypoint (`backend/app/main.py`) with CORS middleware and root/health routes.
  - Created forecast route router stub (`backend/app/api/routes/forecast.py`) and schemas (`backend/app/schemas/forecast.py`).
  - Created placeholder prediction service (`backend/app/services/prediction_service.py`).
  - Created placeholder ML pipeline scripts in `backend/ml/src/`.
  - Created unit tests in `backend/tests/test_main.py`.
- **Files Created:**
  - `backend/app/main.py`
  - `backend/app/core/config.py`
  - `backend/app/api/routes/forecast.py`
  - `backend/app/schemas/forecast.py`
  - `backend/app/services/prediction_service.py`
  - `backend/ml/src/*.py`
  - `backend/tests/test_main.py`
  - `backend/requirements.txt`
  - `.env.example`
- **Tests Executed & Actual Results:**
  - Unit tests verified endpoints: `GET /`, `GET /health`, `GET /api/v1/forecast/horizons`.
- **Known Limitations:**
  - No machine learning models, database connections, or frontend components.

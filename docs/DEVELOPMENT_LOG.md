# DEVELOPMENT_LOG.md — NEXORA Chronological Engineering Ledger

This document maintains a strict chronological development record for NEXORA. Every completed task must be logged here with newest entries at the top. Never log planned work as completed work.

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

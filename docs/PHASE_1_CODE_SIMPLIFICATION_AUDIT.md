# PHASE_1_CODE_SIMPLIFICATION_AUDIT.md — Phase 1 Code Quality & Maintainability Audit

**Audit Date:** 2026-11-17  
**Auditor:** Senior Software Engineer, Python Code Quality Specialist, ML Systems Reviewer  
**Target Milestone:** Phase 1 (ML Demand Forecasting & FastAPI Inference Serving)  
**Python Runtime:** `backend/.venv/Scripts/python.exe` (Python 3.11.9)  
**Baseline Test Execution:** 59 passed in 11.32s (100% pass rate, 0 failed, 0 skipped, 0 errors)  

---

## 1. Executive Summary & Purpose

NEXORA's Phase 1 implementation comprises data loading, transaction stream preprocessing, continuous daily SKU demand aggregation, leakage-free feature engineering, multi-horizon model training, chronological out-of-time evaluation, model serialization, and FastAPI multi-horizon inference serving.

The purpose of this audit is to systematically review every source file in Phase 1 to identify:
1. Unnecessarily complicated implementations that hinder maintainability or student viva explanations.
2. Code duplication across model fitting, evaluation, validation, and data transformations.
3. Unused imports, dead code stubs, and redundant operations.
4. Opportunities to enhance code clarity, type safety, and runtime robustness without changing mathematical behavior, API contracts, or model artifact compatibility.

---

## 2. Baseline Status

| Component | Status | Metric / Evidence |
| :--- | :---: | :--- |
| **Python Environment** | Verified | `backend/.venv/Scripts/python.exe` (Python 3.11.9) |
| **Backend Test Suite** | 59 / 59 Passed | 59 collected, 59 passed in 11.32s, 0 failed, 0 errors |
| **Model Artifacts** | Verified | `demand_model_7d.joblib` (Ridge, 19.7 KB)<br>`demand_model_15d.joblib` (RF, 1.15 MB)<br>`demand_model_30d.joblib` (RF, 1.14 MB)<br>`demand_model_90d.joblib` (RF, 1.04 MB)<br>`models_metadata.json` (11.3 KB) |
| **API Endpoints** | Verified | `GET /api/v1/forecast/horizons`<br>`GET /api/v1/forecast/model-metrics`<br>`GET /api/v1/forecast/model-info`<br>`POST /api/v1/forecast/`<br>`POST /api/v1/forecast/predict` |
| **Model Selection** | Verified | $D_7$: Ridge (55.65% WAPE)<br>$D_{15}$: Random Forest (50.00% WAPE)<br>$D_{30}$: Random Forest (48.73% WAPE)<br>$D_{90}$: Random Forest (53.22% WAPE) |

---

## 3. Detailed File-by-File Inspection & Audit Findings

### A. `backend/ml/src/train.py`
- **Current Lines of Code:** 475 lines.
- **Role:** Model building, training orchestrator, chronological backtesting, and model serialization.
- **Audit Findings:**
  1. *Candidate Model Evaluation Duplication (MEDIUM):* In `train_and_evaluate_horizon`, the fitting, prediction timing, clipping, metric evaluation (`evaluate_predictions`), and dictionary construction are repeated nearly verbatim three times across `WeeklyAverageDemandRateBaseline`, `Ridge`, and `RandomForestRegressor` (lines 227–312).
  2. *Unused Imports (LOW):* `os` (line 13) and `Tuple` (line 19) are imported but never referenced in the module.
  3. *Redundant Variable Operations (LOW):* In `validate_model_predictions`, `hasattr(preds, "values")` followed by `np.clip(np.asarray(preds, dtype=float), 0.0, None)` can be simplified to a single NumPy clipping call.
- **Recommendation:**
  - Introduce a concise private helper `_evaluate_candidate(name, model, X_train, y_train, X_val, y_val, algorithm, hyperparams)` to eliminate ~50 lines of duplicate timing/evaluation boilerplate while keeping model definitions explicit.
  - Remove unused imports (`os`, `Tuple`).

### B. `backend/ml/src/feature_engineering.py`
- **Current Lines of Code:** 800 lines.
- **Role:** Task 3 (daily aggregation & continuous zero-padding) and Task 4 (calendar, lag, rolling mean, forward target generation).
- **Audit Findings:**
  1. *Unused Imports (LOW):* `import os` (line 20) is imported but never used.
  2. *Clean Groupby Transformations (NO CHANGE):* The forward target construction `s.iloc[::-1].shift(1).rolling(window=h, min_periods=h).sum().iloc[::-1]` and shifted rolling means `s.shift(1).rolling(window=w, min_periods=w).mean()` are mathematically exact, prevent temporal leakage, and preserve incomplete targets as NaN. These must NOT be modified.
  3. *Validation Redundancies (LOW):* `validate_daily_demand_data` and `validate_feature_dataset` contain comprehensive assertions. They are well-structured and serve as rigorous self-testing functions.
- **Recommendation:**
  - Remove unused import `os`.
  - Preserve all date handling, zero-imputation, and target calculation logic untouched.

### C. `backend/ml/src/preprocessing.py`
- **Current Lines of Code:** 351 lines.
- **Role:** Data loading, transaction stream classification, and reconciliation.
- **Audit Findings:**
  1. *Redundant Classification Assignment (LOW):* In `classify_transactions`, line 72 initializes `df_classified["transaction_stream"] = "exceptional"`. Line 76 then redundantly re-applies `df_classified.loc[mask_exceptional, "transaction_stream"] = "exceptional"`.
  2. *Unused Imports (LOW):* `import os` (line 14) and `Tuple` (line 16) are unused.
  3. *Stream Isolation Preservation (NO CHANGE):* The four transaction stream definitions (`gross_sales`, `cancellation`, `return_credit`, `exceptional`) and their precedence rules are clear, tested, and correct.
- **Recommendation:**
  - Remove redundant line 76 assignment.
  - Remove unused imports (`os`, `Tuple`).
  - Preserve stream classification rules and reconciliation checks untouched.

### D. `backend/ml/src/evaluate.py`
- **Current Lines of Code:** 165 lines.
- **Role:** Calculation of MAE, RMSE, WAPE, and chronological purge/embargo splitting.
- **Audit Findings:**
  1. *Evaluation Accuracy (NO CHANGE):* Metric calculation functions (`calculate_mae`, `calculate_rmse`, `calculate_wape`, `evaluate_predictions`) are concise, mathematically sound, and properly handle edge cases (e.g., zero denominator in WAPE).
  2. *Chronological Purge/Embargo (NO CHANGE):* `get_chronological_split` enforces $t_{\text{train}} \le \text{val\_start} - (H + 1)$, ensuring zero target overlap. This is vital to prevent temporal leakage.
- **Recommendation:**
  - Keep file unchanged; it is already clean, focused, and well-tested.

### E. `backend/ml/src/predict.py`
- **Current Lines of Code:** 22 lines.
- **Role:** Inference module.
- **Audit Findings:**
  1. *Dead Stub / Incomplete Implementation (MEDIUM):* `predict.py` contains a single placeholder function `run_inference` that raises `NotImplementedError("Model inference is not yet available...")`. While FastAPI serves inference through `prediction_service.py`, having a dead placeholder stub in `backend/ml/src/predict.py` is misleading to developers and students.
- **Recommendation:**
  - Implement `run_inference` to load model artifacts via `PredictionService` and return predictions for specified SKUs, providing a functional Python API for offline testing and viva demonstrations without raising `NotImplementedError`.

### F. `backend/app/services/prediction_service.py`
- **Current Lines of Code:** 257 lines.
- **Role:** Singleton model registry, lifespan model loading, input feature formatting, non-negativity clipping, and unseen SKU resilience.
- **Audit Findings:**
  1. *Unused Import (LOW):* `import os` (line 10) is unused.
  2. *Architecture & Decoupling (NO CHANGE):* Lifespan loading, singleton pattern, and decoupling from FastAPI routes are well-implemented. The feature contract mapping (`['StockCode', 'DayOfWeek', 'Month', 'DayOfMonth', 'Lag1', 'Lag7', 'Lag14', 'Lag28', 'RollingMean7', 'RollingMean28']`) and unseen SKU warning generation are clean and maintainable.
- **Recommendation:**
  - Remove unused import `os`.
  - Preserve inference logic, non-negativity clipping, and warning mechanisms.

### G. `backend/app/api/routes/forecast.py`
- **Current Lines of Code:** 95 lines.
- **Role:** REST endpoints under `/api/v1/forecast/`.
- **Audit Findings:**
  1. *Accidental Duplicate Stubs at Top of File (HIGH - Resolved):* The working copy had duplicate docstrings and placeholder stubs at lines 24–48, which were cleaned prior to the baseline test run.
  2. *Route Cleanliness (NO CHANGE):* Current routes (`/horizons`, `/model-metrics`, `/model-info`, `/`, `/predict`) are clean, well-typed, and adhere to HTTP status code conventions (503 for missing artifacts, 422 for bad requests, 200 for predictions).
- **Recommendation:**
  - Ensure route file remains clean and verified.

### H. `backend/app/core/config.py`
- **Audit Findings:**
  1. *Pydantic Boolean Parsing from Environment (HIGH - Resolved):* On machines where an OS environment variable `DEBUG=release` exists, Pydantic's `DEBUG: bool` fails with validation error. Added `@field_validator("DEBUG", mode="before")` to cleanly parse strings like `'release'`, `'prod'`, `'debug'` into booleans.
- **Recommendation:**
  - Keep the validator in place; it prevents environmental failure across different developer workstations.

### I. Test Suite in `backend/tests/`
- **Audit Findings:**
  1. *Coverage & Organization (NO CHANGE):* 59 tests covering all 7 test modules. Tests are modular, use expressive names, and verify mathematical boundaries (zero leakage, unseen SKU handling, adversarial future-spike resilience, numerical reload equivalence).
  2. *Timeout Safety:* Configured `pytest.ini` with 30s timeout prevents hanging.
- **Recommendation:**
  - Keep all 59 tests completely intact; zero tests removed or weakened.

---

## 4. Risk Classification of Planned Improvements

| File | Change | Classification | Description & Justification |
| :--- | :--- | :---: | :--- |
| `backend/ml/src/train.py` | Refactor repeated evaluation boilerplate | **MEDIUM** | Consolidates repeated timing/fitting/evaluation code into a small private helper `_evaluate_candidate()`. Safe: reduces ~45 lines of duplication without altering model training or hyperparameters. |
| `backend/ml/src/train.py` | Remove unused imports | **LOW** | Removes unused `os` and `Tuple`. Completely safe. |
| `backend/ml/src/preprocessing.py` | Remove redundant assignment & unused imports | **LOW** | Eliminates redundant `mask_exceptional` re-assignment and unused `os`, `Tuple`. Completely safe. |
| `backend/ml/src/feature_engineering.py` | Remove unused import | **LOW** | Removes unused `os`. Completely safe. |
| `backend/ml/src/predict.py` | Implement working `run_inference()` | **MEDIUM** | Connects `run_inference` to `PredictionService` so the module works rather than raising `NotImplementedError`. |
| `backend/app/services/prediction_service.py` | Remove unused import | **LOW** | Removes unused `os`. Completely safe. |
| `backend/ml/src/evaluate.py` | No changes | **NO CHANGE** | Already clean, concise, and mathematically verified. |
| `backend/app/api/routes/forecast.py` | Clean up duplicate stubs | **HIGH (Resolved)** | Eliminates duplicate stubs; verified with test suite. |

---

## 5. Items That Must NOT Be Changed (Protected Boundaries)

1. **Model Serialization & Artifacts:** Do not retrain or reserialize models. The four `.joblib` files and `models_metadata.json` are verified and active.
2. **Model Hyperparameters:** Ridge $\alpha=1.0$, Random Forest $n_{\text{estimators}}=25, \text{max\_depth}=10, \text{random\_state}=42$, `OneHotEncoder(max_categories=50)`.
3. **Purge/Embargo Formula:** $t_{\text{train}} \le \text{val\_start} - (H + 1)$. Must remain untouched to guarantee zero temporal target leakage.
4. **Feature & Target Definitions:** Lags (1, 7, 14, 28), 1-day shifted rolling means (7, 28), and reverse-shifted cumulative sums for $D_7, D_{15}, D_{30}, D_{90}$ with NaN preservation.
5. **API Request/Response Schemas:** Multi-horizon `horizons: List[int]`, `horizon_days: Optional[int]`, flat/nested historical feature access.
6. **Existing Test Assertions:** All 59 tests must remain intact.

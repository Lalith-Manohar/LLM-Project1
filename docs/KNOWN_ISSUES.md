# KNOWN_ISSUES.md — NEXORA Technical Issue & Bug Registry

This document maintains an active registry of known technical issues, architectural inconsistencies, and bugs across the NEXORA codebase. Issues must never be marked as resolved without empirical verification.

---

## Active Issues

### ISSUE-001: Prediction API Request Schema Mismatch with Blueprint
- **Severity:** Medium
- **Module Affected:** Module 7 (Predictive Planner) / Backend API
- **Relevant Files:**
  - `backend/app/schemas/forecast.py`
  - `backend/app/api/routes/forecast.py`
  - `backend/app/services/prediction_service.py`
- **Description:** Currently, `ForecastRequest` expects a single integer `horizon_days: int` (e.g., `{"stock_code": "85123A", "horizon_days": 30}`). However, Section 9 of the Technical Blueprint v1.0 specifies a multi-horizon request body taking a list of horizons: `{"stock_code": "85123A", "horizons": [7, 15, 30, 90]}` and returning predictions for all requested horizons in a single response.
- **Reproduction Steps:**
  1. Inspect `backend/app/schemas/forecast.py`.
  2. Send a request body with `"horizons": [7, 15, 30, 90]`; FastAPI returns a 422 Unprocessable Entity error because it expects `horizon_days`.
- **Current Status:** Open (Identified during blueprint reconciliation).
- **Proposed Resolution:** Refactor `ForecastRequest` to accept `horizons: List[int]` (or optionally accept both `horizon_days` for backwards compatibility and `horizons: List[int]` for multi-horizon requests). Update `ForecastResponse` to return a map of horizon to prediction.
- **Target Resolution Phase:** Phase 1 (when wiring real model inference).

---

### ISSUE-002: ML Pipeline Script Stubs (In Progress)
- **Severity:** Low (Expected for current milestone stage)
- **Module Affected:** Machine Learning Subsystem
- **Relevant Files:**
  - `backend/ml/src/data_loader.py` (RESOLVED: Implemented in Task 1)
  - `backend/ml/src/preprocessing.py`
  - `backend/ml/src/feature_engineering.py`
  - `backend/ml/src/train.py`
  - `backend/ml/src/evaluate.py`
  - `backend/ml/src/predict.py`
- **Description:** Pipeline scripts in `backend/ml/src/` were structured stubs. With Phase 1 Task 1 completed, `data_loader.py` is fully implemented and tested. The remaining modules (`preprocessing.py`, `feature_engineering.py`, `train.py`, `evaluate.py`, `predict.py`) still contain stubs with `NotImplementedError`.
- **Current Status:** In Progress (Task 1 completed, Tasks 2–5 remaining for Milestone 1).
- **Proposed Resolution:** Implement each pipeline module sequentially starting with `preprocessing.py` and daily aggregation, followed by model training.
- **Target Resolution Phase:** Phase 1 (Target: 21 November 2026).

---

### ISSUE-004: Raw CSV Encoding Requirement (Latin1 for UK Pound Symbol)
- **Severity:** Low (Resolved in data_loader.py)
- **Module Affected:** Machine Learning Subsystem / Ingestion
- **Relevant Files:**
  - `backend/ml/src/data_loader.py`
  - `backend/ml/data/raw/online_retail_II.csv`
- **Description:** Reading the raw CSV with default UTF-8 encoding fails with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa3` because the dataset contains the British Pound symbol (`£` = 0xa3 in Windows-1252 / ISO-8859-1).
- **Reproduction Steps:**
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

## Resolved Issues
*(No resolved issues yet — all verified fixes will be recorded here with resolution date and test confirmation.)*

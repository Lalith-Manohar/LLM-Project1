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

### ISSUE-002: ML Pipeline Script Stubs Raise NotImplementedError
- **Severity:** Low (Expected for current milestone stage)
- **Module Affected:** Machine Learning Subsystem
- **Relevant Files:**
  - `backend/ml/src/data_loader.py`
  - `backend/ml/src/preprocessing.py`
  - `backend/ml/src/feature_engineering.py`
  - `backend/ml/src/train.py`
  - `backend/ml/src/evaluate.py`
  - `backend/ml/src/predict.py`
- **Description:** All pipeline scripts in `backend/ml/src/` are currently structured stubs containing function definitions that immediately raise `NotImplementedError`. While the dataset `backend/ml/data/raw/online_retail_II.csv` is now available, data loading, preprocessing, and training logic have not yet been implemented.
- **Current Status:** Open (In progress for Milestone 1).
- **Proposed Resolution:** Implement each pipeline module sequentially starting with `data_loader.py` and `preprocessing.py`, followed by automated tests.
- **Target Resolution Phase:** Phase 1 (Target: 21 November 2026).

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

# NEXORA – AI-Powered Retail Management & Intelligence System

Welcome to **NEXORA**, an enterprise-grade retail platform uniting day-to-day store operations, inventory risk intelligence, and machine-learning-driven demand forecasting.

---

## 1. Project Directory Structure

```text
NEXORA/
│
├── AGENTS.md                          # Central multi-agent instruction & architecture manual
├── README.md                          # Project introduction and student setup guide
│
├── backend/
│   ├── .venv/                         # Project-local Python virtual environment (ignored by git)
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── forecast.py        # Demand forecasting endpoints (/api/v1/forecast)
│   │   ├── core/
│   │   │   └── config.py              # Application settings (Pydantic Settings)
│   │   ├── schemas/
│   │   │   └── forecast.py            # Pydantic validation schemas
│   │   └── services/
│   │       └── prediction_service.py  # Inference orchestration service
│   │
│   ├── ml/
│   │   ├── data/
│   │   │   ├── raw/                   # Raw UCI Online Retail II dataset (online_retail_II.csv)
│   │   │   └── processed/             # Cleaned datasets and reports (clean_gross_sales.csv, etc.)
│   │   ├── models/                    # Saved ML models (.joblib binaries)
│   │   ├── notebooks/                 # Exploratory data analysis notebooks
│   │   └── src/
│   │       ├── data_loader.py         # Raw data ingestion & statistical profiling
│   │       ├── preprocessing.py       # 4-way transaction stream partitioning & reconciliation
│   │       ├── feature_engineering.py # Daily aggregation & time-series features
│   │       ├── train.py               # Multi-horizon model training
│   │       ├── evaluate.py            # Out-of-time evaluation (MAE, RMSE, WAPE)
│   │       └── predict.py             # Inference pipeline
│   │
│   ├── tests/
│   │   ├── test_feature_engineering.py # Daily aggregation & boundary tests (7 tests)
│   │   ├── test_ml_features.py         # Leakage-free features & targets tests (10 tests)
│   │   ├── test_model_training.py      # Pipelines, OneHot, reproducibility tests (10 tests)
│   │   ├── test_model_evaluation.py    # Purge/embargo & metric tests (9 tests)
│   │   ├── test_forecast_api.py        # Multi-horizon inference API & offline tests (16 tests)
│   │   ├── test_main.py                # FastAPI root & health endpoints (3 tests)
│   │   └── test_preprocessing.py       # Stream isolation & reconciliation tests (5 tests)
│   ├── requirements.txt               # Backend & ML dependencies
│   └── .env.example                   # Environment configuration template
│
├── frontend/                          # React + TypeScript demonstration client
│   ├── src/
│   │   ├── services/api.ts            # Typed HTTP API client (fetch)
│   │   ├── types/forecast.ts          # Schema interfaces matching backend
│   │   ├── App.tsx                    # Interactive forecasting UI & JSON inspector
│   │   └── main.tsx                   # Entry point
│   ├── package.json                   # React 18, TypeScript 5, Vite 5
│   └── README.md                      # Frontend architecture & setup guide
│
└── docs/                              # System documentation & knowledge registries
    ├── NEXORA — Technical Blueprint v1.0.md  # Canonical specification
    ├── DEVELOPMENT_LOG.md             # Chronological engineering ledger
    ├── FEATURES_STATUS.md             # Feature implementation matrix
    ├── TECHNICAL_DECISIONS.md         # Architectural Decision Records (ADRs)
    ├── KNOWN_ISSUES.md                # Defect and technical debt tracker
    ├── PROJECT_OVERVIEW.md            # Vision, scope, and boundaries
    ├── ML_DOCUMENTATION.md            # Machine learning pipeline documentation
    ├── DATABASE_SCHEMA.md             # Relational MySQL 19-table schema
    ├── API_DOCUMENTATION.md           # REST API endpoint reference
    └── DEVELOPMENT_ROADMAP.md         # Phased milestones tracking
```

---

## 2. Student Quickstart & Environment Setup Guide

Follow these beginner-friendly Windows PowerShell instructions to set up your environment, run tests, and execute NEXORA services.

### Prerequisites
- **Python 3.10+** installed (Python 3.11 recommended).
- Confirm Python installation:
  ```powershell
  python --version
  ```

---

### Step 1: Create or Verify the Project Virtual Environment

The project standardizes on a local virtual environment located at `backend/.venv`.

Open Windows PowerShell in the project root directory (`NEXORA`):
```powershell
# Create the virtual environment inside backend/
python -m venv backend/.venv
```

---

### Step 2: Activate the Virtual Environment

```powershell
# In PowerShell:
.\backend\.venv\Scripts\Activate.ps1
```

*(Note: If PowerShell displays a script execution policy error, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once).*

Once activated, your command prompt will be prefixed with `(.venv)`.

---

### Step 3: Install Project Dependencies

With the virtual environment active:
```powershell
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

#### Optional Dependencies:
- **XGBoost:** To test optional gradient boosting models:
  ```powershell
  python -m pip install xgboost
  ```

---

### Step 4: Verify Environment Packages

Run this quick one-line verification check:
```powershell
python -c "import pandas, numpy, sklearn, joblib, fastapi, uvicorn, pydantic, sqlalchemy, pytest, httpx; print('Environment Ready!')"
```

---

### Step 5: How to Run ML Scripts and Pipelines

Always run scripts from the project root using the virtual environment:

1. **Run Dataset Ingestion & Statistical Profiling:**
   ```powershell
   python backend/ml/src/data_loader.py
   ```
   *Generates `eda_report.md` and statistical summaries in `backend/ml/data/processed/`.*

2. **Run Data Preprocessing & Transaction Stream Isolation:**
   ```powershell
   python backend/ml/src/preprocessing.py
   ```
   *Generates `clean_gross_sales.csv`, `cancellation_transactions.csv`, `return_transactions.csv`, and `preprocessing_report.md`.*

3. **Run Multi-Horizon Feature Engineering:**
   ```powershell
   python backend/ml/src/feature_engineering.py
   ```
   *Generates `daily_product_demand.csv` and `ml_feature_dataset.csv`.*

4. **Run Model Training & Evaluation:**
   ```powershell
   python backend/ml/src/train.py
   ```
   *Trains Ridge and Random Forest models across all 4 horizons, saving artifacts to `backend/ml/models/`.*

5. **Run Quick CLI Prediction:**
   ```powershell
   python backend/ml/src/predict.py
   ```
   *Runs demo inference on SKU '85123A' across 7, 15, 30, and 90-day horizons.*

---

### Step 6: How to Run Automated Tests

Run the complete 60-test backend verification suite:
```powershell
# Run the complete test suite with timeout safety
python -m pytest backend/tests/ -v --tb=short
```

---

### Step 7: How to Start the FastAPI Backend

Start the local development server:
```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Interactive Swagger UI Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Probe:** [http://localhost:8000/health](http://localhost:8000/health)

---

### Step 8: How to Start the React Frontend Client

In a separate PowerShell window, start the frontend development client:
```powershell
cd frontend
npm install
npm run dev
```

- **Client Web Interface:** [http://localhost:5173](http://localhost:5173)
- Features real-time backend health check, demo SKU selector presets, multi-horizon forecast inputs, model metrics display (WAPE), and an interactive HTTP Request/Response JSON Inspector drawer for academic viva demonstrations.

---

## 3. Important Project Rules for Developers

1. **Source of Truth:** Always consult [AGENTS.md](file:///c:/Users/grand/OneDrive/Desktop/SDC%20-1%20Project/LLM-Project1/AGENTS.md) before writing or modifying code.
2. **Never Touch Raw Data:** Do not modify `backend/ml/data/raw/online_retail_II.csv`.
3. **Keep Logs Synchronized:** Update [DEVELOPMENT_LOG.md](file:///c:/Users/grand/OneDrive/Desktop/SDC%20-1%20Project/LLM-Project1/docs/DEVELOPMENT_LOG.md) and [FEATURES_STATUS.md](file:///c:/Users/grand/OneDrive/Desktop/SDC%20-1%20Project/LLM-Project1/docs/FEATURES_STATUS.md) whenever you complete a task.

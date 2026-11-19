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

## 2. Windows Quickstart: Single-Command Automated Startup

For anyone running NEXORA on Windows (including after extracting a fresh GitHub ZIP download), the system provides a fully automated setup and development launcher:

```powershell
.\start.ps1
```

### Windows Prerequisites
Before running the launcher for the first time, ensure your computer has:
1. **Python 3.10+** (Python 3.11 recommended):
   - Download from: [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
   - **Crucial:** During installation, check the box: **"Add python.exe to PATH"**.
2. **Node.js LTS** (v18+ recommended):
   - Download from: [https://nodejs.org/](https://nodejs.org/)
   - Install with standard defaults (includes `npm`).

### What `.\start.ps1` Does Automatically
When you run `.\start.ps1`, the script executes four automated stages without requiring manual intervention:
1. **Asset Integrity Verification:** Checks that all 6 required datasets and pre-trained model binaries exist (`daily_product_demand.csv`, `models_metadata.json`, and the four multi-horizon `.joblib` pipelines).
2. **Virtual Environment & Backend Setup:** Detects host Python, creates `backend/.venv` if missing, and installs dependencies from `backend/requirements.txt` (skips re-installation if already satisfied).
3. **Frontend Dependency Setup:** Detects `node` and `npm`, and installs dependencies via `npm ci` inside `frontend/` (skips re-installation if already satisfied).
4. **Service Orchestration:** Checks port availability, then launches the FastAPI Backend and Vite Frontend in separate PowerShell console windows to keep real-time logs visible.

### Application Access Points
Once launched, open your web browser or API client (Postman/curl) to:
- **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173) (Interactive UI with automated demand forecasting)
- **Backend API Docs (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Liveness Health Probe:** [http://localhost:8000/health](http://localhost:8000/health) (Reports process liveness: `200 OK`)
- **Readiness Subsystem Probe:** [http://localhost:8000/ready](http://localhost:8000/ready) (Reports model & dataset readiness: `200 OK` or `503 Service Unavailable`)
- **Forecast Prediction Endpoint:** [http://localhost:8000/api/v1/forecast/predict](http://localhost:8000/api/v1/forecast/predict) (Multi-horizon demand inference)

### How to Stop the Services
- Simply press **Ctrl+C** inside each opened PowerShell window, or close the windows.
- To restart at any time, execute `.\start.ps1` again.

### Common Windows Startup Issues & Solutions
- **PowerShell Execution Policy Restricted:**
  - *Symptom:* `start.ps1 cannot be loaded because running scripts is disabled on this system.`
  - *Fix:* Run this command once in PowerShell:
    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    ```
- **Python Not Recognized or Missing in PATH:**
  - *Symptom:* `[ERROR] Compatible Python 3.10+ was not found on this computer.`
  - *Fix:* Reinstall Python from [python.org](https://www.python.org/downloads/windows/) and ensure **"Add python.exe to PATH"** is selected.
- **Port 8000 or 5173 Already in Use:**
  - *Symptom:* `[WARNING] Port 8000 is already active.`
  - *Fix:* If an earlier FastAPI server is still running in the background, close its terminal window or terminate the process holding port 8000.

---

## 3. Manual Step-by-Step Setup Guide (Optional / Non-Windows / Kaggle)

If you are developing on Linux/macOS, running inside Kaggle Notebooks, or prefer manual control, follow these step-by-step instructions.

> [!NOTE]
> **Kaggle Environment Rule:** Kaggle notebooks run on Linux containers without Windows PowerShell. Do not attempt to run `start.ps1` on Kaggle. In Kaggle, use standard Linux Python commands directly without virtual environment activation.

### Step 1: Create or Verify the Project Virtual Environment
```powershell
python -m venv backend/.venv
```

### Step 2: Activate the Virtual Environment
- **Windows PowerShell:**
  ```powershell
  .\backend\.venv\Scripts\Activate.ps1
  ```
- **Linux / macOS / Bash:**
  ```bash
  source backend/.venv/bin/activate
  ```

### Step 3: Install Backend Dependencies
```bash
python -m pip install -r backend/requirements.txt
```

### Step 4: Verify Environment Packages
```bash
python -c "import pandas, numpy, sklearn, joblib, fastapi, uvicorn, pydantic, sqlalchemy, pytest, httpx; print('Environment Ready!')"
```

### Step 5: How to Run ML Scripts and Pipelines (Offline Training)
Always run scripts from the project root using the project virtual environment:
1. **Dataset Ingestion & Profiling:** `python backend/ml/src/data_loader.py`
2. **Data Preprocessing & Stream Isolation:** `python backend/ml/src/preprocessing.py`
3. **Multi-Horizon Feature Engineering:** `python backend/ml/src/feature_engineering.py`
4. **Model Training & Evaluation:** `python backend/ml/src/train.py`
5. **Quick CLI Prediction Test:** `python backend/ml/src/predict.py`

### Step 6: How to Run Automated Backend Tests
Run the complete 84-test backend verification suite:
```bash
python -m pytest backend/tests/ -v --tb=short
```

### Step 7: How to Start the FastAPI Backend Manually
```powershell
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Step 8: How to Start the React Frontend Client Manually
```powershell
cd frontend
npm install
npm run dev
```

---

## 4. Postman API Testing & Public Deployment Readiness Guide

NEXORA’s FastAPI backend is fully configured for local and public API testing via Postman, cURL, and tunneling services (e.g. ngrok).

### 4.1 System Endpoints Summary
| Method | Endpoint | Description | Expected Status |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Process liveness probe | `200 OK` |
| `GET` | `/ready` | Model and dataset readiness probe | `200 OK` / `503 Unavailable` |
| `GET` | `/api/v1/forecast/horizons` | Supported forecasting windows (7, 15, 30, 90 days) | `200 OK` |
| `POST` | `/api/v1/forecast/predict` | Multi-horizon demand inference (Primary Endpoint) | `200 OK` |
| `POST` | `/api/v1/forecast/` | Multi-horizon demand inference (Direct Route) | `200 OK` |

### 4.2 Postman Request: Multi-Horizon Forecast (Automatic CSV Features)
- **Method:** `POST`
- **URL:** `http://localhost:8000/api/v1/forecast/predict` (or your public ngrok URL, e.g. `https://<subdomain>.ngrok-free.app/api/v1/forecast/predict`)
- **Headers:**
  - `Content-Type: application/json`
  - *(When testing via ngrok free tier)* `ngrok-skip-browser-warning: 69420`
- **Request Body (raw JSON):**
```json
{
  "stock_code": "85123A"
}
```
*Note: To request specific horizons, include `"horizons": [7, 15, 30, 90]`.*

- **Expected Response (`200 OK`):**
```json
{
  "stock_code": "85123A",
  "horizons": [7, 15, 30, 90],
  "predictions": {
    "7": 771.5717,
    "15": 3009.3201,
    "30": 3062.395,
    "90": 9427.142
  },
  "horizon_details": [
    {
      "horizon_days": 7,
      "predicted_demand": 771.5717,
      "model_name": "Linear Regression",
      "wape": 55.65
    },
    {
      "horizon_days": 15,
      "predicted_demand": 3009.3201,
      "model_name": "Random Forest",
      "wape": 50.0
    },
    {
      "horizon_days": 30,
      "predicted_demand": 3062.395,
      "model_name": "Random Forest",
      "wape": 48.73
    },
    {
      "horizon_days": 90,
      "predicted_demand": 9427.142,
      "model_name": "Random Forest",
      "wape": 53.22
    }
  ],
  "units": "units",
  "model_version": "Phase 1 (Task 5 Model Training & Serialization)",
  "observation_date": "2011-12-09",
  "history_days": 374,
  "is_auto_generated": true,
  "status": "success",
  "warnings": [
    "Historical demand features automatically generated from 374 daily records up to observation date 2011-12-09 (UCI Online Retail II dataset)."
  ]
}
```

### 4.3 Postman Error Test Scenarios
1. **Unknown SKU (HTTP 404):**
   - **Body:** `{"stock_code": "NON_EXISTENT_SKU_99999"}`
   - **Response (`404 Not Found`):**
     ```json
     {
       "detail": "Product SKU 'NON_EXISTENT_SKU_99999' was not found in historical sales records. Ensure the SKU exists in the UCI Online Retail II catalog."
     }
     ```
2. **Insufficient History SKU (HTTP 422):**
   - **Body:** `{"stock_code": "21777"}`
   - **Response (`422 Unprocessable Content`):**
     ```json
     {
       "detail": "Insufficient historical sales data for SKU '21777' (6 calendar days available; minimum 29 days required to compute 28-day lag and rolling average features)."
     }
     ```
3. **Backend Not Ready Probe (HTTP 503):**
   - If models or historical datasets have not completed initialization, `GET /ready` and `POST /api/v1/forecast/predict` return HTTP 503 Service Unavailable with component-level diagnostic details.

### 4.4 Deployment & ngrok Tunneling Readiness
- **FastAPI / Uvicorn Port Binding:** By default, Uvicorn runs on `127.0.0.1:8000` (or `0.0.0.0:8000` when configured).
- **Tunneling Compatibility:** Compatible with ngrok (`ngrok http 8000`). FastAPI CORS middleware permits all origins (`*`) and methods.
- **Host Filtering:** No `TrustedHostMiddleware` restrictions are enforced, allowing public hostnames (e.g. `*.ngrok-free.app`) to pass directly to endpoints.
- **Python Version:** Python 3.10+ required; certified and verified on Python 3.11.9 (64-bit).

---

## 5. Important Project Rules for Developers

1. **Source of Truth:** Always consult [AGENTS.md](file:///c:/Users/grand/OneDrive/Desktop/SDC%20-1%20Project/LLM-Project1/AGENTS.md) before writing or modifying code.
2. **Never Touch Raw Data:** Do not modify `backend/ml/data/raw/online_retail_II.csv`.
3. **Keep Logs Synchronized:** Update [DEVELOPMENT_LOG.md](file:///c:/Users/grand/OneDrive/Desktop/SDC%20-1%20Project/LLM-Project1/docs/DEVELOPMENT_LOG.md) and [FEATURES_STATUS.md](file:///c:/Users/grand/OneDrive/Desktop/SDC%20-1%20Project/LLM-Project1/docs/FEATURES_STATUS.md) whenever you complete a task.

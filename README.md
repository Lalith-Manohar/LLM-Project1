# NEXORA – AI-Powered Retail Management & Intelligence System

Welcome to **NEXORA**, an intelligent retail platform delivering machine learning demand forecasting, inventory control, and enterprise management capabilities.

---

## 1. Project Directory Structure

```text
NEXORA/
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       └── forecast.py        # Demand forecasting endpoints
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py              # Application settings
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── forecast.py            # Pydantic validation schemas
│   │   └── services/
│   │       ├── __init__.py
│   │       └── prediction_service.py  # Inference orchestration
│   │
│   ├── ml/
│   │   ├── data/
│   │   │   ├── raw/                   # Place UCI Online Retail II dataset here
│   │   │   └── processed/             # Cleaned feature-engineered sets
│   │   ├── models/                    # Saved ML models (.joblib)
│   │   ├── notebooks/                 # Exploratory data analysis
│   │   └── src/
│   │       ├── __init__.py
│   │       ├── data_loader.py         # Raw data ingestion
│   │       ├── preprocessing.py       # Data cleaning & filtering
│   │       ├── feature_engineering.py # Lag & temporal features
│   │       ├── train.py               # Model training script
│   │       ├── evaluate.py            # Accuracy metrics
│   │       └── predict.py             # Inference functions
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_main.py               # API unit tests
│   ├── requirements.txt               # Backend & ML dependencies
│   └── .env.example                   # Environment configuration template
│
├── frontend/                          # Future React + TypeScript frontend
│   └── README.md
│
├── docs/                              # System documentation
│   ├── PROJECT_SPEC.md                # System roadmap & specs
│   ├── ML_DESIGN.md                   # Machine learning architecture
│   └── DATABASE_DESIGN.md             # Future MySQL schema design
│
├── .gitignore
└── README.md
```

---

## 2. Quickstart & Setup Guide

### Prerequisites
- Python 3.10+ installed

### Step 1: Create a Python Virtual Environment
Navigate to the `backend` folder and create a virtual environment:

**Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Run the FastAPI Application
From inside the `backend` directory:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 4: Access Swagger UI Documentation
Open your browser and navigate to:
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc UI:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

---

## 3. Running Unit Tests
With the virtual environment activated in `backend/`:
```bash
pytest
```

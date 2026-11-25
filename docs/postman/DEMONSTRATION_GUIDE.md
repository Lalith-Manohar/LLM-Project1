# NEXORA — Academic Demonstration & Postman Evaluation Guide

**Project:** NEXORA – AI-Powered Retail Management & Intelligence System  
**Academic Target Date:** 21 November 2026  
**Active Git Branch:** `uni_api_submission`  
**Architecture:** Trained ML Models → FastAPI Backend → ngrok Public HTTPS Tunnel → Postman  

---

## 1. Compliance with College Requirements

| Requirement | Implementation in NEXORA | Verification Status |
| :--- | :--- | :--- |
| **1. Build and train the ML model** | Multi-horizon demand regression pipelines ($D_7$ Ridge, $D_{15}/D_{30}/D_{90}$ Random Forest) trained on UCI Online Retail II dataset, evaluated via chronological holdouts without target leakage, serialized to `backend/ml/models/`. | **Verified & Completed** |
| **2. Deploy on local server using FastAPI** | FastAPI service (`backend/app/main.py`) serving endpoints under `/api/v1/forecast/predict`, `/health`, and `/ready`, running on Uvicorn ASGI on `http://127.0.0.1:8000`. | **Verified & Running** |
| **3. Generate a public URL using ngrok** | ngrok tunnel forwarding traffic from `http://localhost:8000` to a secure public HTTPS endpoint (`https://antonym-headband-harpist.ngrok-free.dev`). | **Verified & Running** |
| **4. Test deployed model using Postman** | Postman collection containing 6 automated requests tested against the live public URL, returning expected numerical predictions across all horizons. | **Verified & Tested** |

---

## 2. Active Deployment Parameters

- **Local Backend Endpoint:** `http://127.0.0.1:8000`
- **Active Public ngrok URL:** `https://antonym-headband-harpist.ngrok-free.dev`
- **Swagger Documentation (Public):** `https://antonym-headband-harpist.ngrok-free.dev/docs`
- **Postman Collection Location:** `docs/postman/NEXORA_Academic_API.postman_collection.json`

---

## 3. How to Import and Execute in Postman

1. Open the **Postman** desktop application (or web client).
2. Click **Import** (top left).
3. Select and upload:
   ```text
   docs/postman/NEXORA_Academic_API.postman_collection.json
   ```
4. The collection **"NEXORA Academic Deployment API"** will appear in your sidebar with 6 pre-configured requests.
5. In the collection's **Variables** tab, verify that `baseUrl` is set to:
   ```text
   https://antonym-headband-harpist.ngrok-free.dev
   ```
   *(Note: If you restart ngrok on demonstration day, update this variable to the new forwarding URL).*
6. Execute the requests sequentially:
   - **Request 1 (`GET /health`):** Returns `HTTP 200 OK` (`{"status": "healthy"}`).
   - **Request 2 (`GET /ready`):** Returns `HTTP 200 OK` (4 models ready, 3,922 SKUs indexed).
   - **Request 3 (`GET /api/v1/forecast/horizons`):** Returns supported planning windows `[7, 15, 30, 90]`.
   - **Request 4 (`POST /api/v1/forecast/predict`):** Valid SKU `85123A`. Returns `HTTP 200 OK` with all 4 predictions.
   - **Request 5 (`POST /api/v1/forecast/predict`):** Unknown SKU `NON_EXISTENT_SKU_99999`. Returns `HTTP 404 Not Found`.
   - **Request 6 (`POST /api/v1/forecast/predict`):** Insufficient history SKU `21777`. Returns `HTTP 422 Unprocessable Content`.

---

## 4. Reference Forecast Predictions for SKU `85123A`

When evaluating the primary forecast endpoint with `{"stock_code": "85123A"}`:

| Horizon | Estimator Algorithm | Historical WAPE | Verified Prediction |
| :---: | :--- | :---: | :---: |
| **$D_7$** | Ridge Linear Regression | 55.65% | **771.5717 units** |
| **$D_{15}$** | Random Forest Regressor | 50.00% | **3009.3201 units** |
| **$D_{30}$** | Random Forest Regressor | 48.73% | **3062.3950 units** |
| **$D_{90}$** | Random Forest Regressor | 53.22% | **9427.1420 units** |

- **Observation Date:** `2011-12-09` (historical cutoff date in retail dataset)
- **Historical Sales History:** 374 daily records

---

## 5. How to Re-Launch on Demonstration Day (21 November)

If the server or computer has been restarted, follow these two simple steps:

### Step 1: Start the FastAPI Backend
Open a PowerShell terminal in the repository root and run:
```powershell
$env:PYTHONPATH='backend'
.\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Verify readiness in your browser: [http://localhost:8000/ready](http://localhost:8000/ready).

### Step 2: Start the ngrok Tunnel
In a second PowerShell terminal, run:
```powershell
ngrok http 8000
```
ngrok will display a forwarding line such as:
```text
Forwarding   https://<your-new-domain>.ngrok-free.dev -> http://localhost:8000
```

### Step 3: Update Postman `baseUrl`
1. Copy the new HTTPS URL from the ngrok terminal.
2. In Postman, open **NEXORA Academic Deployment API** collection settings $\rightarrow$ **Variables** tab.
3. Paste the new URL into the `baseUrl` variable.
4. Click **Save** and begin your presentation.

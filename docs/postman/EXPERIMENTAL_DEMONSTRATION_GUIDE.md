# NEXORA — Experimental API Demonstration & Postman Evaluation Guide

**Project:** NEXORA – AI-Powered Retail Management & Intelligence System  
**Branch:** `uni_api_experimental`  
**Milestone:** Task 12 Model Selection & Task 20 Deployment Readiness  
**Target Collection:** `docs/postman/NEXORA_Experimental_API.postman_collection.json`  
**API Endpoints:** `/api/v1/experimental/forecast/*` alongside production baseline `/api/v1/forecast/*`

---

## 1. Executive Summary & Capabilities

The **NEXORA Experimental Demand Forecasting Subsystem** provides multi-horizon retail demand predictions powered by models selected during Task 12:
- **Strict 20-Column Feature Contract:** Calendar dynamics, 4 core demand lags ($1, 7, 14, 28$), extended $60$-day lag, 4 rolling averages ($7, 14, 28, 60$), rolling dispersion standard deviations ($7, 28$), zero-demand activity fraction ($28$), momentum velocity ratio, and point-in-time transaction unit pricing.
- **Leakage-Free Point-in-Time Pricing:** Dynamic historical transaction pricing indexed via cumulative daily sums, strictly isolating transactions prior to observation date $T$ to eliminate look-ahead bias.
- **Non-Negativity Guarantees:** Predictions are post-processed with $\hat{y} = \max(0, \hat{y})$ to guarantee physical validity.
- **Complete Subsystem Failure Isolation:** The baseline production prediction pipeline (`/api/v1/forecast/predict`) and primary readiness probe (`/ready`) remain fully operational with `HTTP 200` regardless of experimental pricing service status.

---

## 2. Experimental Postman Collection Overview

The collection contains **12 distinct automated requests** organized across 4 operational categories:

| # | Request Name | Method | Path | Expected Status | Key Assertion / Verification |
| :-: | :--- | :---: | :--- | :---: | :--- |
| **1** | Liveness Probe | `GET` | `/health` | `200 OK` | Process is running and responsive (`status: healthy`). |
| **2** | Production Readiness Probe | `GET` | `/ready` | `200 OK` | Baseline models & daily demand indexed; failure-isolated from experimental status. |
| **3** | Experimental Readiness Probe | `GET` | `/api/v1/experimental/ready` | `200 OK` | Task 12 models, historical demand, and PIT price index are all ready. |
| **4** | Experimental Supported Horizons | `GET` | `/api/v1/experimental/forecast/horizons` | `200 OK` | Returns `[7, 15, 30, 90]` days with Task 12 candidate algorithms. |
| **5** | Model Benchmark Metrics | `GET` | `/api/v1/experimental/forecast/model-metrics` | `200 OK` | Cross-validation WAPE and final holdout benchmark metrics. |
| **6** | Runtime Model Architecture | `GET` | `/api/v1/experimental/forecast/model-info` | `200 OK` | Strict 20-column feature contract transparency. |
| **7** | Multi-Horizon Forecast (Auto) | `POST` | `/api/v1/experimental/forecast/predict` | `200 OK` | SKU `85123A` auto-derives all 20 features and returns 4 horizons. |
| **8** | Selective Horizons Forecast | `POST` | `/api/v1/experimental/forecast/predict` | `200 OK` | SKU `85123A` with `horizons: [7, 30]` returns predictions only for D7 & D30. |
| **9** | Manual 20-Feature Forecast | `POST` | `/api/v1/experimental/forecast/predict` | `200 OK` | Full manual 20-column feature vector executed without requiring catalog records. |
| **10** | Unknown SKU Error Handling | `POST` | `/api/v1/experimental/forecast/predict` | `404 Not Found` | Unrecognized SKU rejected with clear catalog error detail. |
| **11** | Insufficient History Handling | `POST` | `/api/v1/experimental/forecast/predict` | `422 Unprocessable` | SKU `21777` with $<29$ days of records rejected with descriptive validation error. |
| **12** | Production Baseline Predict | `POST` | `/api/v1/forecast/predict` | `200 OK` | Baseline Phase 1 models execute independently with 10 features. |

---

## 3. How to Import and Run in Postman

1. Open **Postman** (desktop application or web version).
2. Click **Import** (top left button).
3. Choose **File** and select:
   ```text
   docs/postman/NEXORA_Experimental_API.postman_collection.json
   ```
4. The collection **"NEXORA Experimental Demand Forecasting API (Task 12)"** will load in your workspace sidebar.
5. In the collection settings, go to the **Variables** tab:
   - `baseUrl`: Set to `http://localhost:8000` for local development, or your public ngrok URL if testing over a tunnel.
6. Click **Run collection** to run all 12 requests in sequence, or click each request individually to inspect headers, payload, and response JSON.

---

## 4. Model Architectures & Benchmark Comparison

### Task 12 Model Selection Summary
- **$D_7$ (7-Day Shelf Replenishment):** ElasticNet ($\alpha=0.01, \text{l1\_ratio}=0.1$) — Holdout WAPE: $54.20\%$.
- **$D_{15}$ (15-Day Bi-Weekly Ordering):** Residual Ridge ($\alpha=1.0$) — Holdout WAPE: $44.88\%$.
- **$D_{30}$ (30-Day Monthly Planning):** Residual Ridge ($\alpha=100.0$) — Holdout WAPE: $46.52\%$.
- **$D_{90}$ (90-Day Quarterly Allocation):** Residual Ridge ($\alpha=10.0$) — Holdout WAPE: $46.12\%$.

### SKU `85123A` Empirical Forecast Comparison

| Horizon | Baseline (Phase 1) Model | Baseline Prediction | Experimental (Task 12) Model | Experimental Prediction |
| :---: | :--- | :---: | :--- | :---: |
| **$D_7$** | Ridge Regression | $771.57$ units | ElasticNet ($\alpha=0.01, \text{l1}=0.1$) | **$745.24$ units** |
| **$D_{15}$** | Random Forest Regressor | $3009.32$ units | Residual Ridge ($\alpha=1.0$) | **$1608.12$ units** |
| **$D_{30}$** | Random Forest Regressor | $3062.40$ units | Residual Ridge ($\alpha=100.0$) | **$3215.45$ units** |
| **$D_{90}$** | Random Forest Regressor | $9427.14$ units | Residual Ridge ($\alpha=10.0$) | **$9646.35$ units** |

---

## 5. Fresh-Clone Self-Healing Verification

On a newly cloned repository without pre-built cached artifacts:
1. `backend/ml/data/processed/clean_gross_sales.csv` and `pit_sku_price_history.json` are generated automatically upon first startup or first experimental inference request.
2. The self-healing pipeline detects raw dataset `online_retail_II.csv` and derives `clean_gross_sales.csv` in $\sim 5$ seconds.
3. The atomic price index builder creates `pit_sku_price_history.json` and updates the static lookup cache in $\sim 1$ second.
4. No manual script invocations or offline data engineering steps are required.

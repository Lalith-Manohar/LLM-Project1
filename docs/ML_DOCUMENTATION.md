# NEXORA – Machine Learning Documentation

## 1. Overview
The machine learning subsystem serves as the analytical intelligence engine of NEXORA. It generates multi-horizon demand forecasts across **7, 15, 30, and 90 days** using historical transaction logs, providing inventory managers and executive dashboards with empirical demand baselines to govern replenishment.

---

## 2. Implementation Status

| Stage / Component | Status | Current Reality in Codebase |
| :--- | :--- | :--- |
| **ML Directory Layout** | **Implemented** | `backend/ml/data/raw/`, `processed/`, `models/`, `notebooks/`, `src/` created. |
| **Pipeline Module Stubs** | **Implemented** | `data_loader.py`, `preprocessing.py`, `feature_engineering.py`, `train.py`, `evaluate.py`, `predict.py` created with `NotImplementedError` guards. |
| **FastAPI Forecast Stub** | **Implemented** | Endpoints active under `/api/v1/forecast/`, returning `model_not_trained` status without fabricated values. |
| **Dataset Acquisition** | **Planned (Milestone 1)** | Raw dataset not yet downloaded into `backend/ml/data/raw/`. |
| **Preprocessing & Isolation** | **Planned (Milestone 1)** | Cancellation (`C` prefix) and return separation logic planned. |
| **Daily SKU Aggregation** | **Planned (Milestone 1)** | Zero-demand padding and chronological aggregation planned. |
| **Feature Engineering** | **Planned (Milestone 1)** | Lags (1, 7, 14, 28) and rolling statistics (7, 28) planned without target leakage. |
| **Model Training & Comparison** | **Planned (Milestone 1)** | Seasonal baseline, Linear Regression, Random Forest, XGBoost planned across 4 horizons. |
| **Chronological Evaluation** | **Planned (Milestone 1)** | MAE, RMSE, WAPE calculation via rolling-origin backtesting planned. |
| **Artifact Persistence** | **Planned (Milestone 1)** | Joblib serialization to `backend/ml/models/` planned. |
| **API Model Integration** | **Planned (Milestone 1)** | Hooking `prediction_service.py` to load serialized `.joblib` estimators planned. |

> [!NOTE]
> No model training has been conducted yet, and no fabricated or mock accuracy metrics exist in the codebase.

---

## 3. Dataset Profile & Operational Limitations

### UCI Online Retail II Dataset
- **Source:** [UCI Machine Learning Repository – Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii)
- **Timeframe:** 01/12/2009 to 09/12/2011 (2-year transaction history).
- **Scope:** UK-based online retailer selling unique all-occasion gift-ware.

### Dataset Schema & Handling Plan
| Field | Type | Description | Handling Rule |
| :--- | :--- | :--- | :--- |
| `Invoice` | String / Object | 6-digit transaction identifier | Codes starting with `'C'` indicate cancellations. Kept separate from positive demand. |
| `StockCode` | String | Unique product SKU identifier | Grouping key for product-level daily time-series aggregation. |
| `Description` | String | Product name / description | Cleaned, stripped of whitespace; tracked for catalog indexing. |
| `Quantity` | Integer | Units per transaction | Positive integers indicate gross demand. Negative quantities represent returns/cancellations. |
| `InvoiceDate` | Datetime | Transaction timestamp | Parsed to datetime format for chronological sorting and daily aggregation. |
| `Price` | Decimal / Float | Unit price in Sterling (£) | Evaluated for transaction filtering; records with non-positive price removed from sales demand. |
| `Customer ID` | Float / String | Unique client identifier | Missing in certain transactions (~20%); handled without discarding general product sales records. |
| `Country` | String | Destination country | Used for regional sales distribution analysis. |

### Data Limitations & Ground Truth Distinctions
The UCI dataset is an uncurated historical transaction dump. It specifically lacks:
1. Real warehouse physical stock levels.
2. Supplier records and delivery lead times.
3. Complete customer billing/shipping street addresses.
4. Return justification reasons (defective vs wrong item).
5. Tax identification numbers and live carrier tracking.

*Design Principle:* Historical sales demand is derived from the dataset; current operational inventory, suppliers, customers, and shipments are maintained natively in MySQL.

---

## 4. Data Preprocessing & Demand Isolation Logic

The preprocessing pipeline (`backend/ml/src/preprocessing.py`) follows strict isolation rules:

```mermaid
flowchart TD
    Raw["Raw UCI Transactions"] --> Standardize["Standardize Column Names & Types"]
    Standardize --> Split{"Transaction Type Check"}
    
    Split -->|"Invoice starts with 'C'"| Canc["Cancellation Log (Tracked Separately)"]
    Split -->|"Quantity < 0 & No 'C'"| Ret["Return / Credit Log (Tracked Separately)"]
    Split -->|"Quantity > 0 & Price > 0"| Valid["Gross Sales Demand"]
    
    Valid --> DailyAgg["Daily Product Aggregation (Sum Quantity by StockCode, Date)"]
    DailyAgg --> ZeroFill["Sparse Date Imputation (Fill missing days with 0 demand)"]
    ZeroFill --> FeatureEngine["Feature Engineering Pipeline"]
```

### Critical Preprocessing Principles
1. **Separate Accounting Measures:** Maintain distinct counts for gross sales, cancellations, returns, and net volume (`Net = Gross - Returns - Cancellations`).
2. **Positive Demand for Training:** Demand forecasting models are trained on true customer sales demand (positive quantities from valid invoices). Returns and cancellations are monitored separately under Product Health & Anomaly modules.
3. **Sparse Demand Zero-Filling:** Retail products often have inactive days. The pipeline generates continuous daily date ranges per product and fills missing sales days with `0` rather than dropping dates.

---

## 5. Feature Engineering (Leakage-Free)

All feature generation (`backend/ml/src/feature_engineering.py`) enforces strict chronological boundaries:

| Feature Category | Features | Calculation & Leakage Prevention Rule |
| :--- | :--- | :--- |
| **Calendar Dynamics** | `DayOfWeek`, `Month`, `DayOfMonth` | Extracted directly from transaction date; captures weekly cycles and monthly seasonality. |
| **Lag Features** | `Lag1`, `Lag7`, `Lag14`, `Lag28` | Historical demand shifted by $t - k$. Never references current or future target days. |
| **Rolling Statistics** | `RollingMean7`, `RollingMean28` | Moving averages calculated over prior windows ($t-1$ backwards). Rolling windows exclude the current observation date. |
| **Horizon Alignment** | $D_7, D_{15}, D_{30}, D_{90}$ | Targets represent cumulative positive demand over the subsequent $H$ days: $\sum_{i=1}^{H} y_{t+i}$. In multi-step modeling, feature sets use information available strictly at time $t$. |

---

## 6. Multi-Horizon Forecasting Targets

| Target Code | Horizon Window | Operational Purpose in NEXORA |
| :--- | :--- | :--- |
| **D7** | 7 Days | Fast-moving item replenishment and weekly stockout prevention. |
| **D15** | 15 Days | Bi-weekly supplier ordering and batch replenishment cycles. |
| **D30** | 30 Days | Monthly warehouse space allocation and capital budgeting. |
| **D90** | 90 Days | Quarterly supply chain capacity planning and vendor volume agreements. |

*Model Strategy:* Dedicated regression models will be trained independently for each horizon ($H \in \{7, 15, 30, 90\}$) to optimize for horizon-specific variance and lead-time characteristics.

---

## 7. Model Candidates & Comparison Strategy

1. **Seasonal Naïve Baseline:** Repeats historical demand from the prior seasonal cycle (e.g., prior 7-day average). Establishes the performance benchmark.
2. **Linear Regression (Ridge / Lasso):** Provides a transparent, interpretable linear baseline.
3. **Random Forest Regressor:** Non-linear ensemble model capturing complex feature interactions and non-monotonic seasonality.
4. **XGBoost Regressor (Optional / Comparative):** Gradient boosting framework evaluated if computational environment and execution constraints permit.

---

## 8. Chronological Evaluation & Metrics

Random train/test splits cause extreme temporal data leakage in time-series forecasting. NEXORA enforces **chronological splitting** and **rolling-origin backtesting**:

- **Evaluation Window:** The final months of the dataset are reserved strictly as an out-of-time test set.
- **Metric Definitions:**
  - **MAE (Mean Absolute Error):** Measures average absolute deviation in units:
    $$\text{MAE} = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|$$
  - **RMSE (Root Mean Squared Error):** Penalizes large outlier forecast errors:
    $$\text{RMSE} = \sqrt{\frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$$
  - **WAPE (Weighted Absolute Percentage Error):** Robust to zero-demand days (avoids division-by-zero inherent to MAPE):
    $$\text{WAPE} = \frac{\sum_{i=1}^{n} |y_i - \hat{y}_i|}{\sum_{i=1}^{n} y_i}$$

---

## 9. Prediction Constraints & Serving Pipeline

- **Non-Negativity Guarantee:** Predicted demand cannot be negative. Post-processing enforces $\hat{y} = \max(0, \hat{y})$.
- **Insufficient History Handling:** SKUs with fewer than 28 days of history return an explicit `insufficient_history` indicator rather than arbitrary guesses.
- **Model Metadata Persistence:** Serialized `.joblib` files are stored alongside a manifest recording training date, horizon, features used, and validation metrics.
- **Decoupled Architecture:** Model training runs offline via batch scripts; the FastAPI service loads read-only Joblib binaries at startup for low-latency inference.

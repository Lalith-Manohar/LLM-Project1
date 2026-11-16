# NEXORA – Machine Learning Design Specification

## 1. Objective
Develop an accurate, interpretable demand forecasting system to predict future unit sales of products over multiple operational horizons:
- **7-day horizon:** Immediate inventory buffer and shelf replenishment.
- **15-day horizon:** Bi-weekly procurement ordering.
- **30-day horizon:** Monthly warehouse inventory planning.
- **90-day horizon:** Quarterly supply chain and vendor quota contracts.

---

## 2. Dataset Profile: UCI Online Retail II
- **Origin:** Real transactional records from a UK-based online gifts and homeware retailer spanning 2009 to 2011.
- **Key Attributes:**
  - `Invoice`: Unique 6-digit transaction identifier (invoices starting with 'C' denote cancellations).
  - `StockCode`: Product SKU identifier.
  - `Description`: Item name.
  - `Quantity`: Number of units purchased per transaction.
  - `InvoiceDate`: Timestamp of transaction.
  - `Price`: Unit price of item (in Sterling).
  - `Customer ID`: Unique customer identifier.
  - `Country`: Customer location.

---

## 3. ML Pipeline Architecture

```
Raw Data (data/raw/)
       │
       ▼
Data Cleaning & Quality Assurance (src/preprocessing.py)
  ├── Filter out cancelled orders (Invoice like 'C%')
  ├── Remove non-product rows (e.g., postage, test SKUs)
  ├── Handle missing identifiers
  └── Handle extreme returns / outliers
       │
       ▼
Aggregation & Resampling
  └── Group transactions into daily time-series per StockCode
       │
       ▼
Feature Engineering (src/feature_engineering.py)
  ├── Lag Features: t-1, t-7, t-14, t-30
  ├── Rolling Statistics: 7-day & 30-day rolling mean, min, max, std
  ├── Calendar Attributes: Day of week, month, day of month, weekend indicator
  └── Price Dynamics: Average unit price, price fluctuations
       │
       ▼
Model Training & Validation (src/train.py & src/evaluate.py)
  ├── Temporal / Time-Series Backtesting Splits (No lookahead bias)
  ├── Baseline Models (Moving Average, Exponential Smoothing)
  ├── Regressors: Ridge, Random Forest Regressor, Gradient Boosting
  └── Metrics: MAE, RMSE, WAPE, and MAPE
       │
       ▼
Model Persistence (ml/models/)
  └── Save fitted model pipelines & encoders using Joblib
       │
       ▼
API Serving (app/api/routes/forecast.py)
  └── Fast low-latency inference endpoint
```

---

## 4. Serving & Storage
- Trained models and scalers are saved under `backend/ml/models/`.
- The FastAPI service loads models in `backend/app/services/prediction_service.py` and returns structured Pydantic responses.

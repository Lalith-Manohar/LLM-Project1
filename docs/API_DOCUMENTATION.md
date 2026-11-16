# NEXORA – API Documentation

## 1. Overview
NEXORA utilizes **FastAPI** for its asynchronous REST application programming interface. Interactive API documentation is generated automatically via OpenAPI:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Base API Path:** `/api/v1`

---

## 2. Implemented Endpoints

### 2.1 General / Health Endpoints
| Method | Endpoint | Status | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | **Implemented** | Root health and service metadata. |
| `GET` | `/health` | **Implemented** | Service status and version probe. |

#### Root Response Example (`200 OK`)
```json
{
  "project": "NEXORA Retail Management & Intelligence System",
  "version": "0.1.0",
  "status": "online",
  "documentation": "/docs"
}
```

---

### 2.2 Forecasting Endpoints (Phase 1, Task 6 Implemented)

#### 1. Get Supported Horizons
- **Endpoint:** `GET /api/v1/forecast/horizons`
- **Status:** **Implemented**
- **Description:** Returns the list and operational definitions of forecast horizon windows supported by NEXORA.
- **Response `200 OK`:**
```json
{
  "supported_horizons_days": [7, 15, 30, 90],
  "description": "Multi-horizon retail demand planning windows (7 to 90 days).",
  "horizon_definitions": {
    "7": "Weekly fast-moving replenishment & shelf restock",
    "15": "Bi-weekly supplier batch ordering",
    "30": "Monthly inventory planning & space allocation",
    "90": "Quarterly supplier volume quotas & supply chain planning"
  }
}
```

#### 2. Get Model Benchmark Metrics
- **Endpoint:** `GET /api/v1/forecast/model-metrics`
- **Status:** **Implemented**
- **Description:** Returns out-of-time chronological backtesting error metrics (MAE, RMSE, WAPE) across candidate models.
- **Response `200 OK`:**
```json
{
  "project": "NEXORA – AI-Powered Retail Management & Intelligence System",
  "milestone": "Phase 1 (Task 5 Model Training & Serialization)",
  "dataset_reference": "ml_feature_dataset.csv",
  "training_timestamp": "2026-11-17 01:06:35",
  "encoding_strategy": "OneHotEncoder(max_categories=50, handle_unknown='infrequent_if_exist', sparse_output=False)",
  "backtesting_strategy": "Single chronological out-of-time holdout per horizon with strict purge/embargo gap",
  "models": {
    "D_7": {
      "horizon_days": 7,
      "selected_model": "Linear Regression",
      "model_file": "demand_model_7d.joblib",
      "best_metrics": { "mae": 37.4318, "rmse": 92.5686, "wape": 55.654 }
    },
    "D_15": {
      "horizon_days": 15,
      "selected_model": "Random Forest",
      "model_file": "demand_model_15d.joblib",
      "best_metrics": { "mae": 72.9252, "rmse": 217.4885, "wape": 50.0048 }
    },
    "D_30": {
      "horizon_days": 30,
      "selected_model": "Random Forest",
      "model_file": "demand_model_30d.joblib",
      "best_metrics": { "mae": 125.03, "rmse": 406.25, "wape": 48.7296 }
    },
    "D_90": {
      "horizon_days": 90,
      "selected_model": "Random Forest",
      "model_file": "demand_model_90d.joblib",
      "best_metrics": { "mae": 343.36, "rmse": 890.18, "wape": 53.2187 }
    }
  }
}
```

#### 3. Get Model Runtime Info
- **Endpoint:** `GET /api/v1/forecast/model-info`
- **Status:** **Implemented**
- **Description:** Returns active model architecture, scikit-learn version, feature column order, and infrequent SKU handling.
- **Response `200 OK`:**
```json
{
  "project": "NEXORA – AI-Powered Retail Management & Intelligence System",
  "version": "1.0.0",
  "status": "ready",
  "python_version": "3.11.9",
  "scikit_learn_version": "1.9.1",
  "supported_horizons": [7, 15, 30, 90],
  "active_models": {
    "D_7": "Ridge",
    "D_15": "RandomForestRegressor",
    "D_30": "RandomForestRegressor",
    "D_90": "RandomForestRegressor"
  },
  "feature_columns": ["StockCode", "DayOfWeek", "Month", "DayOfMonth", "Lag1", "Lag7", "Lag14", "Lag28", "RollingMean7", "RollingMean28"],
  "unseen_sku_handling": "OneHotEncoder infrequent category mapping (scikit-learn native)"
}
```

#### 4. Multi-Horizon Demand Prediction
- **Endpoints:**
  - `POST /api/v1/forecast/`
  - `POST /api/v1/forecast/predict` *(Blueprint alias)*
- **Status:** **Implemented & Verified**
- **Description:** Generates multi-horizon or single-horizon demand forecasts using in-memory pre-trained `.joblib` estimators. Guaranteed non-negative and finite predictions.
- **Request Body (Nested Features Example):**
```json
{
  "stock_code": "85123A",
  "horizons": [7, 15, 30, 90],
  "features": {
    "day_of_week": 2,
    "month": 11,
    "day_of_month": 15,
    "lag_1": 12.0,
    "lag_7": 15.0,
    "lag_14": 10.0,
    "lag_28": 14.0,
    "rolling_mean_7": 13.5,
    "rolling_mean_28": 12.8
  }
}
```
- **Alternative Request Body (Flat Single-Horizon Example):**
```json
{
  "stock_code": "85123A",
  "horizon_days": 30,
  "lag_1": 12.0,
  "lag_7": 15.0,
  "lag_14": 10.0,
  "lag_28": 14.0,
  "rolling_mean_7": 13.5,
  "rolling_mean_28": 12.8
}
```
- **Response `200 OK`:**
```json
{
  "stock_code": "85123A",
  "horizons": [7, 15, 30, 90],
  "predictions": {
    "7": 83.4307,
    "15": 184.358,
    "30": 576.6974,
    "90": 1588.9073
  },
  "horizon_details": [
    { "horizon_days": 7, "predicted_demand": 83.4307, "model_name": "Linear Regression", "wape": 55.65 },
    { "horizon_days": 15, "predicted_demand": 184.358, "model_name": "Random Forest", "wape": 50.00 },
    { "horizon_days": 30, "predicted_demand": 576.6974, "model_name": "Random Forest", "wape": 48.73 },
    { "horizon_days": 90, "predicted_demand": 1588.9073, "model_name": "Random Forest", "wape": 53.22 }
  ],
  "units": "units",
  "model_version": "Phase 1 (Task 5 Model Training & Serialization)",
  "timestamp": "2026-11-17T01:19:15.123456+00:00",
  "warnings": [],
  "status": "success",
  "total_predicted_demand": 83.4307,
  "horizon_days": null
}
```
- **Error Responses:**
  - `422 Unprocessable Entity`: Validation failure (unsupported horizon like 999, negative demand, missing required lags, non-finite values, or blank StockCode).
  - `503 Service Unavailable`: Models not ready or missing artifacts.

---

## 3. Planned Endpoints (Per Technical Blueprint v1.0)

> [!NOTE]
> The endpoints below represent the planned REST specification across upcoming project phases. None of these endpoints are currently implemented.

### 3.1 Authentication & RBAC (Phase 3)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Authenticate credentials and issue JWT | Public |
| `POST` | `/api/v1/auth/logout` | Revoke session / clear client cookie | Authenticated |
| `GET` | `/api/v1/auth/me` | Fetch active user profile, role, and permissions | Authenticated |

### 3.2 Product Catalog (Phase 2)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/products` | Paginated product listing with search/filter | Authenticated |
| `GET` | `/api/v1/products/{id}` | Detailed product record and price history | Authenticated |
| `POST` | `/api/v1/products` | Create a new product entry | Admin, Inventory Manager |
| `PUT` | `/api/v1/products/{id}` | Update product description or unit price | Admin, Inventory Manager |
| `DELETE` | `/api/v1/products/{id}` | Soft-delete / deactivate product SKU | Admin |

### 3.3 Inventory Management (Phase 2)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/inventory` | Master inventory list with current stock levels | Authenticated |
| `GET` | `/api/v1/inventory/{product_id}` | Detailed stock, safety stock, and reorder point | Authenticated |
| `POST` | `/api/v1/inventory/adjustments` | Post manual stock adjustments (audit logged) | Inventory Manager, Warehouse |
| `GET` | `/api/v1/inventory/movements` | Query historical stock movement ledger | Inventory Manager, Executive |
| `GET` | `/api/v1/inventory/alerts` | List active CRITICAL/ELEVATED stockout alerts | Inventory Manager, Executive |

### 3.4 Predictive Planner & ML Inference (Phase 1 Deliverable & Phase 4)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/forecast/predict` | Generate real-time multi-horizon demand inference | Authenticated |
| `GET` | `/api/v1/forecast/{product_id}` | Retrieve cached forecasts across 7, 15, 30, 90 days | Authenticated |
| `GET` | `/api/v1/forecast/summary` | Aggregate portfolio demand projections | Executive, Inventory Manager |
| `GET` | `/api/v1/forecast/model-metrics` | Return MAE, RMSE, and WAPE evaluation metrics | Authenticated |

#### Blueprint Multi-Horizon Prediction Request Schema
```json
{
  "stock_code": "85123A",
  "horizons": [7, 15, 30, 90]
}
```

#### Blueprint Multi-Horizon Prediction Response Schema
```json
{
  "stock_code": "85123A",
  "predictions": {
    "7": 24.5,
    "15": 51.2,
    "30": 104.8,
    "90": 310.4
  },
  "model_version": "v1"
}
```

### 3.5 Purchase Planning & Approval (Phase 6)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/purchase-orders` | List purchase orders with status filter | Inventory Manager, Executive |
| `POST` | `/api/v1/purchase-orders` | Create draft purchase order from simulation | Inventory Manager |
| `PUT` | `/api/v1/purchase-orders/{id}` | Edit draft quantities, items, or supplier | Inventory Manager |
| `POST` | `/api/v1/purchase-orders/{id}/approve` | Executive human approval of purchase order | Admin, Executive |
| `POST` | `/api/v1/purchase-orders/{id}/reject` | Reject purchase order with recorded reason | Admin, Executive |

### 3.6 Billing & Finance (Phase 6)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/customers` | Register customer with billing address | Finance, Sales |
| `GET` | `/api/v1/customers` | Search customer directory | Finance, Sales |
| `POST` | `/api/v1/invoices` | Generate invoice record with tax and totals | Finance |
| `GET` | `/api/v1/invoices` | Paginated invoice history | Finance, Executive |
| `GET` | `/api/v1/invoices/{id}` | Full invoice details and printable view data | Finance |
| `POST` | `/api/v1/credit-notes` | Issue credit note against an invoice | Finance |

### 3.7 Shipping & Packing Preparation (Phase 6)
| Method | Endpoint | Description | Role Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/shipping/orders` | Orders awaiting dispatch preparation | Warehouse, Inventory |
| `POST` | `/api/v1/shipping/packing-slip/{shipment_id}` | Generate digital packing checklist slip | Warehouse |
| `GET` | `/api/v1/shipping/label/{shipment_id}` | Generate internal routing label | Warehouse |
| `PUT` | `/api/v1/shipping/{shipment_id}/status` | Update internal shipment status | Warehouse |

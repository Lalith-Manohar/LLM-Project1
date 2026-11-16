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

### 2.2 Forecasting Endpoints (Current State)

#### Get Supported Horizons
- **Endpoint:** `GET /api/v1/forecast/horizons`
- **Status:** **Implemented**
- **Response `200 OK`:**
```json
{
  "supported_horizons_days": [7, 15, 30, 90],
  "description": "Short-term to quarterly retail demand horizons."
}
```

#### Request Demand Forecast
- **Endpoint:** `POST /api/v1/forecast/`
- **Status:** **Implemented (Placeholder Service)**
- **Description:** Submits a demand forecast request for an SKU and horizon. Currently connected to `prediction_service.py`, returning a status indicating model training is pending without returning fabricated values.
- **Request Body:**
```json
{
  "stock_code": "85123A",
  "horizon_days": 30
}
```
- **Response `200 OK` (Current state before ML training):**
```json
{
  "stock_code": "85123A",
  "horizon_days": 30,
  "total_predicted_demand": null,
  "daily_forecasts": [],
  "status": "model_not_trained",
  "message": "Model training pending. Place model artifact in backend/ml/models to enable inference."
}
```

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

# FEATURES_STATUS.md — NEXORA Feature Implementation Matrix

This document is the central feature tracking registry for NEXORA. It catalogs every feature across all 13 application modules with its current implementation status, associated files, endpoints, and testing verification.

Allowed Statuses:
- `IMPLEMENTED` — Fully written and empirically verified with tests.
- `PARTIALLY IMPLEMENTED` — Scaffolded, stubs created, or partially functional; requires completion.
- `PLANNED` — Architecturally designed and scheduled in the development roadmap; no code yet.
- `POSTPONED` — Deferred to future project iterations beyond initial academic deliverables.
- `EXCLUDED` — Explicitly excluded from project scope (DO NOT IMPLEMENT).

---

## Summary Matrix

| Module | Total Features Tracked | Implemented | Partially Implemented | Planned | Postponed / Excluded |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **M1: Role-Based Home Dashboard** | 6 | 0 | 0 | 6 | 0 |
| **M2: Analytics & Business Intelligence** | 5 | 0 | 0 | 5 | 0 |
| **M3: Seasonal Demand Calendar** | 4 | 0 | 0 | 4 | 0 |
| **M4: Product Lifecycle Intelligence** | 3 | 0 | 0 | 3 | 0 |
| **M5: Price & Revenue Intelligence** | 3 | 0 | 0 | 3 | 0 |
| **M6: Inventory Control** | 6 | 0 | 0 | 6 | 0 |
| **M7: Predictive Planner (Core ML)** | 8 | 7 | 0 | 1 | 0 |
| **M8: Purchase Planning Simulator** | 4 | 0 | 0 | 4 | 0 |
| **M9: Product Health & Return Intelligence** | 4 | 0 | 0 | 4 | 0 |
| **M10: Anomaly Detection & Alerts** | 3 | 0 | 0 | 3 | 0 |
| **M11: Billing & Finance** | 5 | 0 | 0 | 5 | 0 |
| **M12: Shipping & Delivery Preparation** | 4 | 0 | 0 | 4 | 0 |
| **M13: Role-Based Access Management (RBAC)**| 4 | 0 | 0 | 4 | 0 |
| **System Boundaries & Out-of-Scope** | 8 | 0 | 0 | 0 | 8 (Excluded) |

---

## Detailed Feature Registry

### Module 1: Role-Based Home Dashboard
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M01-01` | Executive High-Level KPI Summary | `PLANNED` | — | `/api/v1/analytics/dashboard` | `transactions`, `invoices` | Not Executed | Planned for Phase 4 |
| `FEAT-M01-02` | Inventory Manager Dashboard | `PLANNED` | — | `/api/v1/inventory/alerts` | `inventory`, `forecasts` | Not Executed | Planned for Phase 4 |
| `FEAT-M01-03` | Warehouse Worker Task Dashboard | `PLANNED` | — | `/api/v1/shipping/orders` | `shipments`, `inventory` | Not Executed | Planned for Phase 4 |
| `FEAT-M01-04` | Finance Revenue & Invoice Activity | `PLANNED` | — | `/api/v1/invoices` | `invoices`, `credit_notes` | Not Executed | Planned for Phase 4 |
| `FEAT-M01-05` | Sales Employee Trend Dashboard | `PLANNED` | — | `/api/v1/analytics/sales` | `transactions` | Not Executed | Planned for Phase 4 |
| `FEAT-M01-06` | Dynamic Home View Switching | `PLANNED` | `frontend/src/pages/` | `/api/v1/auth/me` | `users`, `roles` | Not Executed | Planned for Phase 4 |

---

### Module 2: Analytics & Business Intelligence
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M02-01` | Time-Series Sales Visualizer | `PLANNED` | — | `/api/v1/analytics/timeseries` | `transactions`, `transaction_items` | Not Executed | Planned for Phase 4/5 |
| `FEAT-M02-02` | Country Sales Breakdown | `PLANNED` | — | `/api/v1/analytics/countries` | `transactions` | Not Executed | Planned for Phase 4/5 |
| `FEAT-M02-03` | SKU Volume Velocity Rankings | `PLANNED` | — | `/api/v1/analytics/rankings` | `products`, `transaction_items` | Not Executed | Planned for Phase 4/5 |
| `FEAT-M02-04` | Periodic Sales Comparisons (QoQ, YoY)| `PLANNED` | — | `/api/v1/analytics/compare` | `transactions` | Not Executed | Planned for Phase 5 |
| `FEAT-M02-05` | Slow-Moving Item Identification | `PLANNED` | — | `/api/v1/analytics/slow-moving` | `inventory`, `transactions` | Not Executed | Planned for Phase 5 |

---

### Module 3: Seasonal Demand Calendar
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M03-01` | Day-of-Week Demand Concentration | `PLANNED` | — | `/api/v1/intelligence/seasonality/dow` | `transactions` | Not Executed | Planned for Phase 5 |
| `FEAT-M03-02` | Monthly Demand Heatmap | `PLANNED` | — | `/api/v1/intelligence/seasonality/monthly` | `transactions` | Not Executed | Planned for Phase 5 |
| `FEAT-M03-03` | Recurring Demand Surge Detection | `PLANNED` | — | `/api/v1/intelligence/seasonality/recurring` | `transactions` | Not Executed | Planned for Phase 5 |
| `FEAT-M03-04` | Historical Seasonal Overlay | `PLANNED` | — | `/api/v1/intelligence/seasonality/overlay` | `transactions` | Not Executed | Planned for Phase 5 |

---

### Module 4: Product Lifecycle Intelligence
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M04-01` | Algorithmic SKU Lifecycle Classification | `PLANNED` | — | `/api/v1/intelligence/lifecycle` | `products`, `transactions` | Not Executed | Planned for Phase 5 |
| `FEAT-M04-02` | Inactive / Dead Stock Identification | `PLANNED` | — | `/api/v1/intelligence/dead-stock` | `products`, `inventory` | Not Executed | Planned for Phase 5 |
| `FEAT-M04-03` | Lifecycle Transition Alerts | `PLANNED` | — | `/api/v1/intelligence/lifecycle/alerts` | `products` | Not Executed | Planned for Phase 5 |

---

### Module 5: Price & Revenue Intelligence
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M05-01` | Unit Price Distribution Analysis | `PLANNED` | — | `/api/v1/intelligence/price-distribution` | `products`, `transaction_items` | Not Executed | Planned for Phase 5 |
| `FEAT-M05-02` | Quantity vs Price Correlation | `PLANNED` | — | `/api/v1/intelligence/price-elasticity` | `transaction_items` | Not Executed | Explores correlation, not causal claims |
| `FEAT-M05-03` | Gross Revenue Contribution by SKU | `PLANNED` | — | `/api/v1/intelligence/revenue-contribution` | `transaction_items` | Not Executed | Planned for Phase 5 |

---

### Module 6: Inventory Control
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M06-01` | Master Stock Registry View | `PLANNED` | — | `/api/v1/inventory` | `products`, `inventory` | Not Executed | Planned for Phase 2 |
| `FEAT-M06-02` | Manual Stock Adjustments | `PLANNED` | — | `POST /api/v1/inventory/adjustments` | `inventory`, `inventory_movements` | Not Executed | Must log movement in same transaction |
| `FEAT-M06-03` | Transactional Movement History Ledger | `PLANNED` | — | `GET /api/v1/inventory/movements` | `inventory_movements` | Not Executed | Immutable ledger entry |
| `FEAT-M06-04` | Low-Stock & Reorder Point Alerts | `PLANNED` | — | `GET /api/v1/inventory/alerts` | `inventory_alerts` | Not Executed | Planned for Phase 2 |
| `FEAT-M06-05` | Disaggregated Sales/Returns/Cancels View | `PLANNED` | — | `/api/v1/inventory/volume-breakdown` | `transactions`, `transaction_items` | Not Executed | Planned for Phase 2 |
| `FEAT-M06-06` | Inventory Safety Factor Customization | `PLANNED` | — | `PUT /api/v1/inventory/{id}/safety` | `inventory` | Not Executed | Planned for Phase 2 |

---

### Module 7: Predictive Planner (Core ML Engine)
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M07-01` | Supported Horizon Listing | `IMPLEMENTED` | `backend/app/api/routes/forecast.py` | `GET /api/v1/forecast/horizons` | None | **Passed** | Returns `[7, 15, 30, 90]` |
| `FEAT-M07-02` | Multi-Horizon Forecast Inference API | `IMPLEMENTED` | `backend/app/api/routes/forecast.py`, `prediction_service.py`, `historical_data_service.py` | `POST /api/v1/forecast/`, `POST /api/v1/forecast/predict`, `GET /api/v1/forecast/model-metrics`, `GET /api/v1/forecast/model-info` | None | **Passed** | Fully integrated with 4 trained .joblib models via lifespan caching; automated CSV feature generation from daily_product_demand.csv, observation date transparency, multi-horizon predictions (7, 15, 30, 90d), unseen SKU resilience, non-negativity; 25 unit/integration tests passed |
| `FEAT-M07-03` | Dataset Ingestion Pipeline | `IMPLEMENTED` | `backend/ml/src/data_loader.py` | None | None | **Passed** | Reads raw CSV (latin1 encoding), generates statistical profile & eda_report.md |
| `FEAT-M07-04` | Leakage-Free Preprocessing & Features | `IMPLEMENTED` | `preprocessing.py`, `feature_engineering.py` | None | None | **Passed** | Preprocessing, stream isolation, continuous daily zero-imputation, and leakage-free feature/target generation complete & verified |
| `FEAT-M07-05` | Horizon Regressors Training (7/15/30/90d)| `IMPLEMENTED` | `backend/ml/src/train.py`, `models/` | None | None | **Passed** | Trained Seasonal Naive, Linear Regression, and Random Forest; serialized 4 pipelines to .joblib |
| `FEAT-M07-06` | Out-of-Time Backtesting (MAE/RMSE/WAPE) | `IMPLEMENTED` | `backend/ml/src/evaluate.py`, `models_metadata.json` | None | None | **Passed** | Strict chronological purge/embargo backtesting with MAE, RMSE, and WAPE across all 4 horizons |
| `FEAT-M07-07` | Stockout Risk Scoring (CRITICAL/ELEVATED/SAFE) | `PLANNED` | `prediction_service.py` | `POST /api/v1/forecast/predict` | `inventory_alerts` | Not Executed | Planned for Phase 1/2 |
| `FEAT-M07-08` | Phase 1 Demonstration Frontend Client | `IMPLEMENTED` | `frontend/src/App.tsx`, `api.ts`, `types/forecast.ts` | `GET /health`, `GET /api/v1/forecast/horizons`, `POST /api/v1/forecast/` | None | **Passed** | Clean, modern light-theme React + TS + Vite interface; automated CSV-driven forecast generation (no manual feature input required), catalog presets, observation date & historical base transparency, accurate Ridge/Random Forest model display, responsive container cards, collapsible JSON request/response inspector |
| `FEAT-M07-09` | Store-Wide Macro Demand Forecasting | `IMPLEMENTED` | `backend/ml/experiments/store_wide_forecasting.py`, `store_wide_service.py` | `GET /api/v1/forecast/store-wide` | None | **Passed** | Aggregates all 3,922 SKUs into total store daily sales; achieves 8.87% - 13.38% WAPE across D7, D15, D30, explaining external 10% WAPE claims; verified via test_experimental_forecast.py |
| `FEAT-M07-10` | Multi-Tier Evaluation Comparison API | `IMPLEMENTED` | `backend/app/api/routes/forecast.py`, `store_wide_service.py` | `GET /api/v1/forecast/evaluation-comparison` | None | **Passed** | Exposes 3-tier comparative matrix (Production SKU vs Optimized SKU vs Store-Wide Macro) across D7, D15, D30, D90; verifies consistent WAPE reductions across all horizons |

---

### Module 8: Purchase Planning Simulator
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M08-01` | Lead-Time & Demand Multiplier Scratchpad | `PLANNED` | — | `/api/v1/simulator/calculate` | `suppliers`, `inventory` | Not Executed | Planned for Phase 5 |
| `FEAT-M08-02` | Projected Stock Position Comparison | `PLANNED` | — | `/api/v1/simulator/compare` | `inventory`, `forecasts` | Not Executed | Planned for Phase 5 |
| `FEAT-M08-03` | Draft Purchase Order Generation | `PLANNED` | — | `POST /api/v1/purchase-orders` | `purchase_orders` | Not Executed | Human approval required |
| `FEAT-M08-04` | PO Approval & Rejection Workflow | `PLANNED` | — | `POST /api/v1/purchase-orders/{id}/approve` | `purchase_orders` | Not Executed | Admin/Executive only |

---

### Module 9: Product Health & Return Intelligence
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M09-01` | Disaggregated Sales/Returns/Net Accounting | `PLANNED` | — | `/api/v1/intelligence/returns/summary` | `transactions`, `transaction_items` | Not Executed | Planned for Phase 5 |
| `FEAT-M09-02` | Return Rate per SKU Calculation | `PLANNED` | — | `/api/v1/intelligence/returns/sku-rates` | `transaction_items` | Not Executed | Planned for Phase 5 |
| `FEAT-M09-03` | Unusual Return Activity Detection | `PLANNED` | — | `/api/v1/intelligence/returns/anomalies` | `transactions` | Not Executed | Planned for Phase 5 |
| `FEAT-M09-04` | Return Justification Ledger | `PLANNED` | — | `/api/v1/intelligence/returns/reasons` | `credit_notes` | Not Executed | For newly entered returns in MySQL |

---

### Module 10: Anomaly Detection & Alerts
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M10-01` | Statistical Demand Spike & Dip Alerts | `PLANNED` | — | `/api/v1/alerts/demand-anomalies` | `forecasts`, `transactions` | Not Executed | Uses rolling standard deviations |
| `FEAT-M10-02` | Sudden Return/Cancellation Surge Warning | `PLANNED` | — | `/api/v1/alerts/cancellation-surges` | `transactions` | Not Executed | Planned for Phase 5 |
| `FEAT-M10-03` | Rapid Inventory Depletion Alerts | `PLANNED` | — | `/api/v1/alerts/stock-depletion` | `inventory_alerts` | Not Executed | Planned for Phase 5 |

---

### Module 11: Billing & Finance
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M11-01` | Manual Customer Intake & Directory | `PLANNED` | — | `POST /api/v1/customers` | `customers` | Not Executed | Manual entry by staff |
| `FEAT-M11-02` | Sales Invoice Calculation (Subtotal, Tax, Total) | `PLANNED` | — | `POST /api/v1/invoices` | `invoices`, `invoice_items` | Not Executed | Strict DECIMAL precision |
| `FEAT-M11-03` | Printable Invoice Generation | `PLANNED` | — | `GET /api/v1/invoices/{id}/print` | `invoices` | Not Executed | Planned for Phase 6 |
| `FEAT-M11-04` | Credit Note Issuance & Refund Adjustment | `PLANNED` | — | `POST /api/v1/credit-notes` | `credit_notes` | Not Executed | Tied to existing invoice |
| `FEAT-M11-05` | Financial Revenue Reconciliation Ledger | `PLANNED` | — | `/api/v1/finance/reconciliation` | `invoices`, `credit_notes` | Not Executed | Planned for Phase 6 |

---

### Module 12: Shipping & Delivery Preparation
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M12-01` | Internal Warehouse Pick-Lists | `PLANNED` | — | `/api/v1/shipping/pick-lists` | `shipments`, `invoices` | Not Executed | Planned for Phase 6 |
| `FEAT-M12-02` | Digital Packing Slip Generation | `PLANNED` | — | `POST /api/v1/shipping/packing-slip/{id}` | `packing_slips` | Not Executed | Internal document |
| `FEAT-M12-03` | Internal Dispatch Routing Labels | `PLANNED` | — | `GET /api/v1/shipping/label/{id}` | `shipments` | Not Executed | Internal label (no carrier API) |
| `FEAT-M12-04` | Fulfillment Status Tracking | `PLANNED` | — | `PUT /api/v1/shipping/{id}/status` | `shipments` | Not Executed | Pending -> Packed -> Dispatched |

---

### Module 13: Role-Based Access Management (RBAC)
| Feature ID | Feature Name | Status | Relevant Files | Relevant Endpoints | DB Tables | Testing Status | Notes / Limitations |
| :--- | :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `FEAT-M13-01` | User Account Lifecycle & Credentials | `PLANNED` | — | `/api/v1/users` | `users`, `roles` | Not Executed | Password hashing via passlib/bcrypt |
| `FEAT-M13-02` | Stateless JWT Authentication (Login/Logout) | `PLANNED` | — | `POST /api/v1/auth/login` | `users` | Not Executed | Planned for Phase 3 |
| `FEAT-M13-03` | Server-Side Endpoint RBAC Dependencies | `PLANNED` | — | Backend Dependencies | `role_permissions` | Not Executed | Enforced in FastAPI dependencies |
| `FEAT-M13-04` | Immutable Activity Audit Logging | `PLANNED` | — | `/api/v1/audit/logs` | `activity_logs` | Not Executed | Planned for Phase 3 |

---

### Explicitly Excluded Features (Boundary Enforcement)
| Feature ID | Excluded Capability | Status | Justification / Architectural Boundary |
| :--- | :--- | :---: | :--- |
| `EXCL-01` | Official Governmental E-Way Bill Generation | `EXCLUDED` | Compliance requires legal API gateways outside scope of academic project. |
| `EXCL-02` | Real Shipping Carrier APIs (FedEx, UPS, DHL) | `EXCLUDED` | Requires production commercial accounts; internal dispatch labels used instead. |
| `EXCL-03` | Automated Supplier Order Dispatch via Email | `EXCLUDED` | Human approval required for all purchasing; no autonomous supplier transmission. |
| `EXCL-04` | Unilateral Automated Price Markdown Engine | `EXCLUDED` | Decision support only; discounts require human executive authorization. |
| `EXCL-05` | Conversational AI Chatbot / Natural Language POS| `EXCLUDED` | NEXORA focuses on regression forecasting and deterministic operational ERP. |
| `EXCL-06` | Market Basket / Purchase Affinity Mining | `EXCLUDED` | Association rule mining is outside the core demand forecasting problem statement. |
| `EXCL-07` | Multi-Supplier Algorithmic Linear Optimization | `EXCLUDED` | Postponed; simple single-supplier lead-time simulator is used. |
| `EXCL-08` | Automated Customer Address Scraping from Dataset | `EXCLUDED` | Dataset lacks full addresses; manual cashier data entry enforced. |

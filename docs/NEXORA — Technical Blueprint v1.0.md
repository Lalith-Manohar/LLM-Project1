# NEXORA
## Technical Project Blueprint

**Project:** AI-Powered Retail Management & Intelligence System  
**Version:** 1.0  
**Prepared:** 15 November 2026  
**Initial milestone:** 21 November 2026

---

# 1. Project Overview

NEXORA is a web-based retail management and intelligence application that combines operational retail activities with machine-learning-based business intelligence.

The system will allow employees to manage inventory, analyze sales, generate invoices, prepare purchase orders, manage shipping preparation and monitor product performance.

Its central intelligence engine will estimate product demand over 7, 15, 30 and 90 days using historical sales records. The forecasts will be combined with inventory information to identify products that may require replenishment.

The application will also include role-based access control so employees only see the dashboards and features relevant to their responsibilities.

## 1.1 Main objectives

1. Analyze historical retail transactions.
2. Forecast future product demand using machine learning.
3. Identify products that may require inventory attention.
4. Maintain current inventory records in MySQL.
5. Provide useful sales and product analytics.
6. Support purchase planning and approval.
7. Generate invoices and basic shipping documents.
8. Provide separate dashboards and permissions for different employee roles.

## 1.2 Important data limitations

The UCI dataset contains historical transaction information, not a complete live retail database.

It does not provide:
- Actual warehouse stock quantities.
- Supplier lead times.
- Supplier contact information.
- Complete customer billing addresses.
- Shipping addresses and vehicle details.
- Reasons for returns or cancellations.
- Complete tax and payment information.

These details will be collected through the application and stored in MySQL.

The application must distinguish historical dataset information from information manually entered by employees.

---

# 2. Technology Stack

| Layer | Technology | Responsibility |
|---|---|---|
| Frontend | React | User interface |
| Language | TypeScript | Frontend logic and type safety |
| Styling | Tailwind CSS | Layout and styling |
| Charts | Chart.js + react-chartjs-2 | Analytics and forecasting graphs |
| Backend | Python + FastAPI | API and application logic |
| Data processing | Pandas + NumPy | Dataset preparation |
| ML | Scikit-learn | Regression and evaluation |
| Optional ML | XGBoost | Additional model comparison |
| Database | MySQL | Application data storage |
| ORM | SQLAlchemy | Python-to-MySQL interaction |
| Validation | Pydantic | API request and response validation |
| Authentication | JWT + password hashing | Secure login |
| Model storage | Joblib | Saving trained models |
| API testing | Swagger UI / Postman | Endpoint testing |
| Development | Google Antigravity | AI-assisted development |
| Version control | GitHub | Source code and collaboration |

### Why Chart.js?

Chart.js is suitable for our project because it supports line charts, bar charts, doughnut charts and other common analytics visualizations. Its React integration is available through react-chartjs-2.

We do not need a complicated visualization framework for the first version.

---

# 3. High-Level System Architecture

The application will follow a layered architecture.

```text
                 NEXORA WEB APPLICATION
                           |
                    React Frontend
                           |
                 Authentication / JWT
                           |
                    FastAPI Backend
                           |
        +------------------+------------------+
        |                  |                  |
   ML Services        Business Services    Auth Services
        |                  |                  |
  Forecast Engine    Inventory Management   Role Checking
  Model Evaluation   Billing & Purchase     User Management
  Risk Calculation   Analytics & Shipping   Permissions
        |                  |                  |
        +------------------+------------------+
                           |
                       MySQL
                           |
       +-------------------+-------------------+
       |                   |                   |
  Historical Sales    Operational Data    User Data
  Products            Inventory           Roles
  Transactions        Invoices            Permissions
  Forecasts           Purchase Orders     Activity Logs
```

## 3.1 Main layers

**Frontend layer**

Displays dashboards, tables, forms, charts and employee workflows.

**Backend layer**

Handles business rules, database operations, authentication, API requests and communication with the ML engine.

**ML layer**

Processes historical sales and generates demand forecasts and inventory-risk indicators.

**Database layer**

Stores historical transactions, current inventory, employee accounts, forecasts, invoices and purchase records.

---

# 4. Application Modules

## Module 1: Role-Based Home Dashboard

The home page will change according to the logged-in user's role.

### Executive dashboard
- Total revenue.
- Unique order count.
- Top-performing countries.
- Sales comparisons.
- Critical inventory alerts.
- Demand forecast summaries.
- Overall business performance.

### Inventory manager dashboard
- Current inventory overview.
- Critical and elevated stock risks.
- AI restock recommendations.
- Purchase order approvals.
- Stock movement summaries.

### Warehouse worker dashboard
- Products requiring attention.
- Stock adjustment tasks.
- Packing tasks.
- Dispatch preparation.
- Recent inventory movements.

### Finance dashboard
- Revenue overview.
- Invoice activity.
- Credit notes.
- Returns and cancellations.
- Financial reports.

### Sales dashboard
- Sales trends.
- Product performance.
- Country performance.
- Order activity.

## Module 2: Analytics and Business Intelligence

- Time-series sales graph.
- Total quantity sold.
- Revenue analysis.
- Country filtering.
- Product performance table.
- Quarterly, half-yearly and yearly comparisons.
- Top-selling products.
- Slow-moving products.

## Module 3: Seasonal Demand Calendar

- Monthly demand patterns.
- Day-of-week demand patterns.
- Seasonal sales heatmap.
- Products with recurring demand increases.
- Historical seasonal comparisons.

This module uses historical data to show patterns. It should not claim that a seasonal increase will definitely happen again.

## Module 4: Product Lifecycle Intelligence

Products will be classified into understandable categories:

- Emerging.
- Growing.
- Stable.
- Declining.
- Inactive or potentially dead stock.

Classification will use configurable sales-history and demand-trend rules.

A product with no recent sales should not automatically be considered permanently discontinued.

## Module 5: Price and Revenue Intelligence

- Product revenue comparison.
- Unit-price analysis.
- Quantity sold by price range.
- Revenue trends.
- Product price and sales relationships.

The system will identify associations, not claim causal effects of price changes.

## Module 6: Inventory Control

- Master stock spreadsheet.
- Current stock quantities.
- Manual stock adjustments.
- Stock movement history.
- Low-stock alerts.
- Inventory search and filtering.
- Separate sales, cancellations and return views.
- Dead-stock identification.

All live stock records will be maintained in MySQL.

## Module 7: Predictive Planner

- 7-day demand forecasts.
- 15-day demand forecasts.
- 30-day demand forecasts.
- 90-day demand forecasts.
- Predicted demand versus current stock.
- Stockout-risk classification.
- Suggested purchase quantities.
- Forecast history.
- Model evaluation information.

## Module 8: Purchase Planning Simulator

- Enter or edit supplier lead time.
- Change available stock.
- Adjust expected demand.
- Simulate different purchase quantities.
- Compare projected stock positions.
- Generate an editable purchase order draft.

## Module 9: Product Health and Return Intelligence

- Gross sales quantity.
- Returned or credited quantity.
- Net quantity.
- Cancellation activity.
- Return rate.
- Products with unusual return activity.

Returns and cancellations will be tracked separately. Neither is sufficient evidence that a product is defective.

## Module 10: Anomaly Detection and Alerts

- Demand spikes.
- Demand drops.
- Unusual cancellation activity.
- Unusual return activity.
- Sudden inventory-risk changes.

Initial anomaly detection will use understandable statistical methods such as rolling averages, standard deviations and thresholds.

## Module 11: Billing and Finance

- Manual customer information entry.
- Customer billing address.
- Product selection.
- Quantity and unit-price entry.
- Subtotal calculation.
- Configurable tax calculation.
- Grand total calculation.
- Print-ready invoice generation.
- Invoice history.
- Credit note generation.
- Finance reports.

Customer information will be manually entered into the billing form. The historical UCI dataset will not be treated as a complete customer address database.

## Module 12: Shipping and Delivery Preparation

- Digital packing slips.
- Internal shipping labels.
- Order number and destination information.
- Delivery method filters.
- Packing checklist.
- Dispatch preparation.

The initial shipping label will be an internal document, not a carrier-issued shipping label.

## Module 13: Role-Based Access Management

- Login and logout.
- User account management.
- Employee roles.
- Role-based dashboards.
- Permission checks.
- Activity history.

---

# 5. Machine Learning Architecture

This is the most important technical component of NEXORA.

## 5.1 Dataset

**UCI Online Retail II**

Dataset URL: https://archive.ics.uci.edu/dataset/502/online+retail+ii

Important fields:

| Field | Purpose |
|---|---|
| Invoice | Transaction identifier |
| StockCode | Product identifier |
| Description | Product description |
| Quantity | Number of units |
| InvoiceDate | Transaction date |
| Price | Unit price |
| Customer ID | Customer identifier |
| Country | Customer country |

## 5.2 Data preprocessing

The preprocessing pipeline should:

1. Load the dataset.
2. Standardize column names.
3. Convert InvoiceDate to datetime.
4. Clean missing StockCode values.
5. Check duplicate and invalid records.
6. Identify cancellation invoices.
7. Identify negative quantity transactions.
8. Separate positive demand, cancellation activity and returns.
9. Aggregate demand by product and day.
10. Prepare features for model training.

### Cancellation and return handling

Invoice identifiers beginning with C indicate cancellation invoices.

Negative quantities can also represent returns or credit transactions.

The system should maintain separate measures:

- Gross positive sales quantity.
- Cancellation invoice activity.
- Negative quantity return/credit activity.
- Net quantity.

Do not count the same event twice. Do not assume that every negative quantity belongs to a cancellation invoice.

The primary demand forecast will use positive customer sales demand from eligible transactions. Returns and cancellations will be analyzed separately.

## 5.3 Feature engineering

Initial features:

| Feature | Description |
|---|---|
| StockCode | Product identifier |
| DayOfWeek | Day of the week |
| Month | Month of the year |
| DayOfMonth | Calendar date |
| Lag1 | Demand one day earlier |
| Lag7 | Demand seven days earlier |
| Lag14 | Demand fourteen days earlier |
| Lag28 | Demand twenty-eight days earlier |
| RollingMean7 | Average demand over previous seven days |
| RollingMean28 | Average demand over previous twenty-eight days |

All rolling and lag features must use historical information only. Rolling features must be shifted appropriately to avoid including the prediction target period.

For products with sparse sales, the pipeline must account for days without transactions rather than treating missing observations as unknown positive demand.

## 5.4 Forecasting horizons

We will create four forecasting targets.

| Model target | Prediction |
|---|---|
| D7 | Total demand over the next 7 days |
| D15 | Total demand over the next 15 days |
| D30 | Total demand over the next 30 days |
| D90 | Total demand over the next 90 days |

Initially, use separate horizon-specific models because each model has a different target.

## 5.5 Models to compare

1. Seasonal naive baseline.
2. Linear Regression.
3. Random Forest Regressor.
4. XGBoost Regressor, if time and environment allow.

We should first establish a working baseline and compare other models against it.

## 5.6 Model evaluation

Use:
- MAE.
- RMSE.
- WAPE.

Avoid relying on MAPE when actual demand can be zero.

Use chronological training and testing splits, not random row splitting.

For each horizon, ensure that training targets do not overlap the evaluation period. Use rolling-origin evaluation where possible.

## 5.7 Prediction handling

- Predictions should be non-negative.
- Products with insufficient history should receive an appropriate fallback or insufficient-data indicator.
- Sparse products should be handled carefully.
- Longer forecast horizons may have higher uncertainty.
- Predictions should be stored with their creation date, horizon and model version.

The historical dataset ends in 2011, so forecasts based on it are historical demonstrations unless newer sales records are added.

---

# 6. Inventory Risk Calculation

The ML model predicts demand. A separate inventory rule converts the prediction into an inventory warning.

### Initial formula

For a basic demonstration:

**Reorder threshold = Forecast demand × Safety factor**

Example:

- Predicted 7-day demand: 100 units.
- Safety factor: 1.2.
- Reorder threshold: 120 units.
- Current stock: 80 units.

Suggested purchase quantity:

`max(0, Reorder threshold - Current stock)`

Result: 40 units.

### Risk classification

| Condition | Risk |
|---|---|
| Stock below predicted demand | CRITICAL |
| Stock covers predicted demand but not safety threshold | ELEVATED |
| Stock covers safety threshold | SAFE |

The threshold must be configurable.

Later, when supplier lead time is available, we can improve the rule to calculate demand over the lead-time period plus safety stock.

This is an estimated inventory-risk indicator, not proof of an actual stockout.

---

# 7. MySQL Database Design

Use MySQL with InnoDB and foreign keys.

The following tables form the proposed database structure.

## 7.1 User and permission tables

### users
- id
- full_name
- email
- password_hash
- role_id
- is_active
- created_at

### roles
- id
- role_name
- description

### permissions
- id
- permission_name
- description

### role_permissions
- id
- role_id
- permission_id

### activity_logs
- id
- user_id
- action
- module
- record_id
- created_at

## 7.2 Product and sales tables

### products
- id
- stock_code
- description
- current_unit_price
- is_active
- created_at
- updated_at

### transactions
- id
- invoice_number
- invoice_date
- customer_id
- country
- transaction_type
- created_at

### transaction_items
- id
- transaction_id
- product_id
- quantity
- unit_price
- line_total

Historical imported transaction records should preserve their original invoice identifiers and source values.

## 7.3 Inventory tables

### inventory
- id
- product_id
- current_quantity
- minimum_stock
- safety_factor
- updated_at

### inventory_movements
- id
- product_id
- movement_type
- quantity_change
- reason
- reference_id
- created_by
- created_at

Inventory changes must be recorded as movements and reflected in the current inventory quantity using a database transaction.

## 7.4 Forecast tables

### model_runs
- id
- model_name
- model_version
- training_start_date
- training_end_date
- evaluation_metrics
- created_at

### forecasts
- id
- product_id
- model_run_id
- forecast_date
- horizon_days
- predicted_quantity
- created_at

### inventory_alerts
- id
- product_id
- risk_level
- predicted_demand
- current_stock
- suggested_quantity
- status
- created_at

## 7.5 Purchase tables

### suppliers
- id
- supplier_name
- contact_person
- email
- phone
- address
- lead_time_days

### purchase_orders
- id
- supplier_id
- created_by
- approved_by
- order_status
- order_date
- expected_delivery_date
- created_at

### purchase_order_items
- id
- purchase_order_id
- product_id
- quantity
- unit_cost

## 7.6 Billing tables

### customers
- id
- customer_name
- phone
- email
- billing_address
- city
- state
- postal_code
- country

### invoices
- id
- invoice_number
- customer_id
- invoice_date
- subtotal
- tax_amount
- grand_total
- payment_status
- created_by

### invoice_items
- id
- invoice_id
- product_id
- description
- quantity
- unit_price
- line_total

### credit_notes
- id
- invoice_id
- credit_note_number
- reason
- amount
- created_by
- created_at

## 7.7 Shipping tables

### shipments
- id
- invoice_id
- shipping_address
- delivery_method
- shipping_status
- tracking_reference
- created_at

### packing_slips
- id
- shipment_id
- generated_by
- generated_at

## 7.8 Database design rules

- Use primary keys and foreign keys.
- Use DECIMAL for money, not floating-point values.
- Use appropriate indexes for StockCode, InvoiceDate, invoice number and foreign keys.
- Keep passwords hashed.
- Record who performs important inventory and financial operations.
- Avoid deleting important financial and stock records without a proper reversal or audit process.
- Use database transactions for operations that update multiple related records.

---

# 8. Role-Based Access Control

The proposed roles are:

1. Admin.
2. Executive.
3. Inventory Manager.
4. Warehouse Worker.
5. Finance Employee.
6. Sales Employee.

| Module | Admin | Executive | Inventory | Warehouse | Finance | Sales |
|---|---|---|---|---|---|---|
| Executive dashboard | Full | Full | — | — | — | — |
| Inventory dashboard | Full | View | Full | Full | — | — |
| Finance dashboard | Full | View | — | — | Full | — |
| Sales dashboard | Full | View | View | — | View | Full |
| Analytics | Full | Full | View | Limited | View | Full |
| Inventory management | Full | View | Full | Limited | — | — |
| Forecasts | Full | View | Full | View | — | View |
| Purchase orders | Full | View | Full | View | — | — |
| Billing | Full | — | — | — | Full | — |
| Shipping | Full | — | View | Full | — | — |
| User management | Full | — | — | — | — | — |

"Full" means the permissions appropriate to that role, not necessarily unrestricted database access.

Permissions must be validated by FastAPI on the server. Hiding a frontend menu is not sufficient security.

---

# 9. FastAPI Endpoint Design

All endpoints will use a common API prefix such as `/api/v1`.

## Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /auth/login | Authenticate user |
| POST | /auth/logout | End session |
| GET | /auth/me | Get current user and role |

## Products

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /products | List products |
| GET | /products/{id} | View product |
| POST | /products | Add product |
| PUT | /products/{id} | Update product |
| DELETE | /products/{id} | Deactivate product |

## Inventory

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /inventory | List inventory |
| GET | /inventory/{product_id} | View product stock |
| POST | /inventory/adjustments | Adjust stock |
| GET | /inventory/movements | View stock history |
| GET | /inventory/alerts | View stock alerts |

## Forecasting

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /forecast/predict | Generate predictions |
| GET | /forecast/{product_id} | Retrieve product forecast |
| GET | /forecast/summary | Forecast overview |
| GET | /forecast/model-metrics | Model evaluation metrics |

Example prediction request:

```json
{
  "stock_code": "85123A",
  "horizons": [7, 15, 30, 90]
}
```

Example response:

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

The numbers above are illustrative, not actual model results.

## Purchase orders

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /purchase-orders | List purchase orders |
| POST | /purchase-orders | Create draft |
| PUT | /purchase-orders/{id} | Edit draft |
| POST | /purchase-orders/{id}/approve | Approve |
| POST | /purchase-orders/{id}/reject | Reject |

## Billing

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /customers | Create customer |
| GET | /customers | List customers |
| POST | /invoices | Generate invoice record |
| GET | /invoices | View invoices |
| GET | /invoices/{id} | View invoice |
| POST | /credit-notes | Create credit note |

Additional endpoints will be added as the corresponding modules are developed.

---

# 10. Frontend Page Structure

Suggested navigation:

```text
NEXORA
|
+-- Login
|
+-- Dashboard
|
+-- Analytics
|   +-- Sales Overview
|   +-- Product Performance
|   +-- Country Analysis
|
+-- Inventory
|   +-- Master Stock
|   +-- Stock Adjustments
|   +-- Stock Movements
|   +-- Stock Alerts
|
+-- Predictive Planner
|   +-- Demand Forecasts
|   +-- Restock Recommendations
|   +-- Model Performance
|
+-- Intelligence
|   +-- Seasonal Demand Calendar
|   +-- Product Lifecycle
|   +-- Price and Revenue
|   +-- Product Health
|   +-- Anomaly Alerts
|
+-- Purchase Planning
|   +-- Purchase Orders
|   +-- Purchase Simulator
|
+-- Billing and Finance
|   +-- Create Invoice
|   +-- Invoice History
|   +-- Credit Notes
|
+-- Shipping
|   +-- Packing Slips
|   +-- Shipping Labels
|
+-- Administration
    +-- User Management
    +-- Role Permissions
    +-- Activity Logs
```

Only the pages permitted for the logged-in user should be displayed.

---

# 11. Recommended Backend Folder Structure

```text
nexora/
|
+-- backend/
|   |
|   +-- app/
|   |   +-- main.py
|   |   +-- database.py
|   |   +-- models/
|   |   +-- schemas/
|   |   +-- routes/
|   |   |   +-- auth.py
|   |   |   +-- products.py
|   |   |   +-- inventory.py
|   |   |   +-- forecasts.py
|   |   |   +-- purchase_orders.py
|   |   |   +-- invoices.py
|   |   |
|   |   +-- services/
|   |   +-- permissions/
|   |
|   +-- ml/
|   |   +-- preprocessing.py
|   |   +-- feature_engineering.py
|   |   +-- train.py
|   |   +-- evaluate.py
|   |   +-- predict.py
|   |   +-- artifacts/
|   |
|   +-- tests/
|   +-- requirements.txt
|
+-- frontend/
|   +-- src/
|       +-- components/
|       +-- pages/
|       +-- layouts/
|       +-- services/
|       +-- hooks/
|       +-- types/
|
+-- dataset/
|
+-- docs/
|   +-- PROJECT_SPEC.md
|   +-- DATABASE_DESIGN.md
|   +-- API_DOCUMENTATION.md
|
+-- README.md
```

The ML training code and the API-serving code should be separate modules. The API should load a previously trained model rather than retrain the model on every prediction request.

---

# 12. Development Roadmap

## Phase 1 — ML and FastAPI

**Target: 21 November 2026**

- Download and inspect dataset.
- Understand all important columns.
- Clean transaction data.
- Handle cancellations and returns separately.
- Aggregate daily product demand.
- Create forecasting features.
- Train a baseline model.
- Train and compare regression models.
- Implement 7-, 15-, 30- and 90-day forecasts.
- Evaluate the models.
- Save model artifacts.
- Create FastAPI prediction endpoints.
- Test using Swagger UI or Postman.

**Deliverable:** a functioning ML prediction API.

## Phase 2 — MySQL and CRUD

- Configure MySQL.
- Create initial tables.
- Connect FastAPI to MySQL.
- Implement product CRUD.
- Implement inventory CRUD.
- Record inventory movements.
- Validate database operations.

**Deliverable:** functioning product and inventory management APIs.

## Phase 3 — Login and permissions

- Create user and role tables.
- Implement login.
- Hash passwords.
- Implement JWT authentication.
- Add backend permission checks.
- Build role-based dashboards.

**Deliverable:** secure employee login and access control.

## Phase 4 — Core application

- Executive dashboard.
- Analytics.
- Inventory management.
- Predictive planner.
- Stock-risk alerts.
- Forecast history.

## Phase 5 — Advanced intelligence

- Seasonal demand calendar.
- Product lifecycle.
- Price and revenue intelligence.
- Return analysis.
- Anomaly detection.
- Purchase planning simulator.

## Phase 6 — Operational features

- Purchase order drafts and approval.
- Invoice creation.
- Credit notes.
- Packing slips.
- Shipping labels.

## Phase 7 — Finalization

- Integration testing.
- Permission testing.
- Data validation.
- UI improvements.
- Documentation.
- Demonstration preparation.

---

# 13. Team Responsibilities

For a team of four:

| Member | Main responsibility |
|---|---|
| Member 1 | Dataset exploration, preprocessing and return/cancellation analysis |
| Member 2 | ML features, model training, evaluation and FastAPI prediction integration |
| Member 3 | MySQL, backend, CRUD, inventory and permissions |
| Member 4 | React frontend, dashboards, charts and integration testing |

For a team of three, combine backend and frontend responsibilities or divide the UI and database work between the available members.

Everyone should understand the overall architecture, not just their own module.

---

# 14. Antigravity Development Rules

We will use Antigravity as an AI-assisted development tool, but the team remains responsible for understanding and testing the generated code.

Follow these rules:

1. Do not ask Antigravity to generate the complete application in one prompt.
2. Build one module at a time.
3. Ask it to explain the files it creates and modifies.
4. Ask for beginner-friendly comments around important logic.
5. Ask it to preserve working modules when adding features.
6. Run the application after each major change.
7. Verify database operations rather than assuming they work.
8. Test APIs using actual requests.
9. Use real dataset records for the ML demonstration.
10. Do not use hardcoded sample results while presenting them as actual ML predictions.
11. Maintain GitHub commits after working milestones.
12. Keep PROJECT_SPEC.md updated as the source of truth.

---

# 15. Testing and Acceptance Criteria

Before declaring a module complete, verify its basic functionality.

### ML
- Dataset loads correctly.
- Invalid and cancellation records are handled consistently.
- Features do not leak future information.
- All four horizons return predictions.
- Predictions are non-negative.
- Evaluation metrics are generated.
- Model artifacts can be loaded again.

### Database
- CRUD operations work.
- Foreign keys are enforced.
- Inventory adjustments update stock correctly.
- Inventory movements are recorded.
- Financial values use appropriate decimal precision.

### Authentication
- Correct login works.
- Incorrect login fails.
- Inactive accounts cannot log in.
- Unauthorized API requests are rejected.
- Employees cannot access restricted functions by calling APIs directly.

### Inventory
- Stock can be added and adjusted.
- Stock history is available.
- Risk indicators update after relevant stock changes.

### Billing
- Customer details can be entered manually.
- Invoice totals are calculated correctly.
- Invoice records are saved.
- Generated documents display the saved invoice information.

### Integration
- Frontend communicates with backend.
- Backend retrieves data from MySQL.
- Forecasting service is connected to the API.
- Dashboard values come from actual application data.

---

# 16. Immediate Deliverable: 21 November

The first demonstration should be intentionally small and reliable.

It should show:

1. The dataset being processed.
2. A product's historical demand.
3. Features created from historical demand.
4. Model training and comparison.
5. Model evaluation results.
6. Predictions for 7, 15, 30 and 90 days.
7. A FastAPI endpoint returning those predictions.

The first milestone does not require the completed React application, billing module, login system or all MySQL tables.

Those will be developed in subsequent phases.

---

# 17. Final Development Principle

NEXORA should be developed as one connected application, not as a collection of disconnected demonstrations.

The ML model supplies demand intelligence. MySQL supplies operational information. FastAPI connects the application logic. React provides the employee interface. Role-based access ensures that each employee sees the appropriate features.

The team should be able to explain the purpose of every major table, endpoint, model feature and business rule.

**The goal is not to generate the largest amount of code with Antigravity. The goal is to build a working system that the team understands, can demonstrate and can confidently explain to judges.**
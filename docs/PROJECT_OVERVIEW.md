# NEXORA – Project Overview

## 1. Executive Vision & Objectives
**NEXORA – AI-Powered Retail Management & Intelligence System** is an enterprise-grade web application combining operational retail workflows with machine-learning-driven demand intelligence.

The system empowers retail personnel across multiple functional roles to manage inventory, analyze sales patterns, generate invoices and credit notes, prepare purchase orders with human approval, handle dispatch and shipping preparation, and monitor lifecycle product performance.

Its central intelligence engine estimates product demand over **7, 15, 30, and 90 days** using historical sales records, correlating these projections with live inventory levels in MySQL to detect stockout risks and recommend replenishment quantities.

### Core Objectives
1. **Analyze Historical Retail Transactions:** Clean, parse, and evaluate multi-year retail transactions.
2. **Forecast Future Demand via ML:** Multi-horizon regression models predicting total demand for 7, 15, 30, and 90-day intervals.
3. **Inventory Risk Identification:** Classify stock into CRITICAL, ELEVATED, and SAFE risk levels based on projected demand and configurable safety factors.
4. **Maintain Operational Inventory in MySQL:** Manage live warehouse stock, manual adjustments, and audit log movements in a transactional database.
5. **Business Intelligence & Analytics:** Deliver executive KPIs, time-series sales analysis, seasonal calendars, and product lifecycle classifications.
6. **Purchase Planning & Human Approval:** Support purchase order generation, supplier lead-time simulations, and human-gated approval workflows (no automated external ordering).
7. **Billing, Credit Notes & Shipping Preparation:** Create printable invoices with manually entered customer data, handle credit notes, and generate internal packing slips and shipping labels (without external carrier API dependencies).
8. **Role-Based Access Control (RBAC):** Provide granular, server-enforced role permissions and tailored dashboards across organizational hierarchies.

---

## 2. Boundaries, Assumptions & Exclusions

To ensure focus, reliability, and academic rigor, NEXORA establishes explicit system boundaries:

- **UCI Dataset Limitations:** The UCI Online Retail II dataset contains historical sales transactions (2009–2011), not live inventory, supplier master records, customer billing addresses, or shipping logs. These operational entities are collected interactively and stored in MySQL.
- **Human Approval for Purchasing:** Suggested purchase orders require human review and approval. No automated supplier procurement is permitted.
- **Manual Customer Entry for Billing:** Because historical retail records lack validated billing addresses and tax credentials, cashier/sales staff enter customer details manually during invoice generation.
- **Internal Shipping Preparation Only:** Generates digital packing slips and internal dispatch labels. No external shipping carrier API integrations (e.g., FedEx, DHL, UPS) or official governmental E-Way bill generation.
- **No Conversational AI or Chatbots:** The intelligence engine focuses strictly on statistical and machine learning regression, time-series forecasting, and deterministic rule-based inventory calculations.
- **No Automatic Markdown Recommendations:** System highlights slow-moving and lifecycle trends without unilaterally enforcing discount markdowns.

---

## 3. Technology Stack

| Layer | Technology | Version / Spec | Responsibility |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | React | 18+ | Component-driven web interface |
| **Language (Frontend)** | TypeScript | 5.x | Static type safety and structured models |
| **Styling** | Tailwind CSS | 3.x | Utility-first responsive design |
| **Data Visualization** | Chart.js + react-chartjs-2 | Latest stable | Line, bar, doughnut charts for sales & forecasts |
| **Backend Framework** | FastAPI | >=0.110.0 | High-performance asynchronous REST API |
| **Runtime & Language** | Python | 3.10+ | Core application logic and data pipelines |
| **Data Processing** | Pandas + NumPy | >=2.2.0, >=1.26.0 | Dataset cleaning, lag generation, aggregation |
| **Machine Learning** | Scikit-learn (+ XGBoost opt.) | >=1.4.0 | Baseline, regression models, cross-validation |
| **Model Serialization** | Joblib | >=1.3.0 | Persistent binary storage for trained estimators |
| **Database Engine** | MySQL | 8.x (InnoDB) | ACID-compliant relational data store |
| **ORM & Migrations** | SQLAlchemy + Alembic | >=2.0.0 | Pythonic data models and schema versioning |
| **Data Validation** | Pydantic | >=2.6.0 | Request/response schemas and config management |
| **Security & Auth** | JWT + Passlib (bcrypt) | Industry standard | Stateless authentication and password hashing |
| **Testing** | Pytest, HTTPX | >=8.0.0, >=0.27.0 | Unit, integration, and API testing |

---

## 4. User Roles and Role-Based Dashboards

NEXORA implements 6 distinct user roles enforced at the FastAPI backend layer:

1. **Admin:** Complete configuration, user lifecycle management, role-permission assignments, and global audit log inspection.
2. **Executive:** High-level strategic visibility, aggregate revenue KPIs, top-performing countries/products, macro demand trends, and critical stock warnings.
3. **Inventory Manager:** Master stock control, stock adjustment approvals, stock movement history, ML restock recommendations, and purchase order drafting/submission.
4. **Warehouse Worker:** Focused operational access for physical stock counting, manual adjustment logs, picking/packing checklists, and dispatch preparation.
5. **Finance Employee:** Invoicing operations, customer billing management, tax calculations, credit note issuance, cancellations/refund audits, and revenue reconciliation.
6. **Sales Employee:** Sales trends, product catalog pricing lookups, country performance metrics, customer order activity, and demand forecast visibility.

---

## 5. Complete Application Modules

- **Module 1: Role-Based Home Dashboard:** Dynamic home screen rendering metrics tailored to the authenticated employee role.
- **Module 2: Analytics and Business Intelligence:** Multi-dimensional sales exploration, volume analysis, country filtering, and SKU velocity rankings.
- **Module 3: Seasonal Demand Calendar:** Calendar heatmaps depicting day-of-week and monthly historical demand concentrations.
- **Module 4: Product Lifecycle Intelligence:** Algorithmic categorization into *Emerging*, *Growing*, *Stable*, *Declining*, and *Inactive / Dead Stock*.
- **Module 5: Price and Revenue Intelligence:** Association studies between unit price distributions, transaction quantities, and gross revenues.
- **Module 6: Inventory Control:** MySQL-backed master stock registry, manual adjustments, movement audit trails, and low-stock threshold monitoring.
- **Module 7: Predictive Planner:** Core forecasting module outputting 7-, 15-, 30-, and 90-day predictions against current stock, calculating safety thresholds and risk ratings.
- **Module 8: Purchase Planning Simulator:** Interactive "what-if" scratchpad testing lead times, expected demand multipliers, and safety buffers before creating draft POs.
- **Module 9: Product Health and Return Intelligence:** Disaggregated tracking of gross sales, invoice cancellations ('C' prefix), negative quantity returns, and net sales.
- **Module 10: Anomaly Detection and Alerts:** Statistical deviation alerts flagging demand spikes/drops and sudden cancellation/return surges.
- **Module 11: Billing and Finance:** Full customer intake form, invoice composition, automated subtotal/tax/grand-total calculations, and credit note issuance.
- **Module 12: Shipping and Delivery Preparation:** Internal packing slips, warehouse pick-lists, and internal parcel routing labels.
- **Module 13: Role-Based Access Management:** User registration, active/inactive toggling, password hashing, and endpoint permission enforcement.

---

## 6. Implementation Status Tracker

| Area / Component | Status | Current Reality in Workspace |
| :--- | :--- | :--- |
| **Project Workspace Layout** | **Implemented** | Structured directories: `backend/`, `frontend/`, `docs/`, `backend/ml/`. |
| **FastAPI Core Foundation** | **Implemented** | Working API server (`/`, `/health`, CORS, Swagger UI at `/docs`). |
| **API Forecast Stubs** | **Implemented** | `/api/v1/forecast/horizons` active; `/api/v1/forecast/` returns pending training status. |
| **ML Pipeline Architecture** | **Partially Implemented** | Directory layout and code stubs created in `backend/ml/src/`; actual dataset, preprocessing, training, and inference pending. |
| **Dataset Ingestion** | **Planned (Milestone 1)** | Raw dataset not yet acquired; `backend/ml/data/raw/` is empty (`.gitkeep` only). |
| **Model Training & Persistence** | **Planned (Milestone 1)** | Baseline and multi-horizon models (7, 15, 30, 90d) and evaluation pipeline pending. |
| **MySQL Database & ORM** | **Planned (Milestone 2)** | Schemas fully designed in blueprint; no live DB connection, tables, or migrations exist yet. |
| **Inventory Management** | **Planned (Milestone 2)** | Stock adjustments, risk ratings, and movement audit tables planned. |
| **Billing & Finance Module** | **Planned (Milestone 6)** | Invoices, credit notes, and customer management planned. |
| **Shipping Preparation** | **Planned (Milestone 6)** | Internal packing slips and shipment records planned. |
| **React + TypeScript Frontend** | **Planned (Phase 4 / Milestone 4)** | Reserved `frontend/` directory created; application initialization pending. |
| **RBAC & Authentication** | **Planned (Milestone 3)** | Role definitions documented; JWT authentication and user tables planned. |

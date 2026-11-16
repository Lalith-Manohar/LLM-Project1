# NEXORA – Project Specification

## 1. Executive Summary
**NEXORA** is an AI-powered retail management and intelligence platform designed to empower retailers with predictive demand planning, automated inventory replenishment, omnichannel billing, shipping logistics, and role-based operational governance.

---

## 2. Milestone Roadmap

### Milestone 1 (Immediate Target - In Progress)
- **Objective:** Establish the foundational architecture and build an ML-based demand forecasting engine using the **UCI Online Retail II dataset**.
- **Deliverables:**
  - Robust modular project structure for backend, ML, frontend, and tests.
  - FastAPI backend serving health and forecasting API endpoints.
  - Data ingestion, cleaning, feature engineering, and model training pipeline.
  - Forecasting capabilities for 7-day, 15-day, 30-day, and 90-day demand windows.

### Milestone 2: Relational Database & Inventory Integration
- Integration of MySQL with SQLAlchemy ORM and Alembic migrations.
- Product catalog, stock tracking, and supplier management.
- Dynamic reorder point calculation using forecasted demand + lead time.

### Milestone 3: Order Processing, Billing & Shipping
- POS / Invoice generation and receipt dispatch.
- Shipping partner tracking and fulfillment workflows.
- Tax and discount rule engines.

### Milestone 4: Frontend Dashboard & Role-Based Access Control (RBAC)
- React + TypeScript user interface with charts and management views.
- Authentication (JWT) and role enforcement:
  - **Administrator:** Full system access, configurations, and audit logs.
  - **Store Manager:** Analytics, demand projections, pricing, and approvals.
  - **Inventory Specialist:** Stock intake, adjustments, and warehouse transfers.
  - **Cashier / Staff:** POS transactions and return processing.

---

## 3. Architecture Overview
- **Backend Framework:** FastAPI (Asynchronous Python)
- **Machine Learning:** Scikit-learn, Pandas, NumPy, Joblib
- **Database (Future):** MySQL 8.x + SQLAlchemy
- **Frontend (Future):** React + TypeScript (Vite + TailwindCSS)
- **API Documentation:** Interactive OpenAPI documentation accessible via Swagger (`/docs`) and ReDoc (`/redoc`).

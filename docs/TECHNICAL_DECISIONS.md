# TECHNICAL_DECISIONS.md — NEXORA Architectural Decision Records (ADR)

This document formally records all major technical and architectural decisions for NEXORA. Every significant architectural choice, library selection, or scope boundary must be documented here with context, alternatives considered, and downstream consequences.

---

### TD-001: Selection of UCI Online Retail II Dataset for Historical Demand
- **Date:** 2026-11-15
- **Topic:** Dataset selection and boundaries.
- **Context:** NEXORA requires a rich, multi-year transaction dataset to train multi-horizon demand forecasting models.
- **Decision:** Use the UCI Online Retail II dataset (`online_retail_II.csv`) covering transactions from 2009 to 2011.
- **Reasoning:** Contains authentic retail transactions with invoice numbers, stock codes, descriptions, quantities, dates, and unit prices across tens of thousands of records.
- **Alternatives Considered:**
  - Synthetic retail transaction generators (rejected: lacks real-world seasonal and intermittent demand patterns).
  - Kaggle Store Item Demand Forecasting Challenge (rejected: limited SKU metadata and lacks cancellation records).
- **Impact on Other Modules:** The dataset does not provide live warehouse inventory, supplier lead times, or complete customer addresses. Operational entities must be maintained natively in MySQL.

---

### TD-002: Four Decoupled Planning Horizons (7, 15, 30, 90 Days)
- **Date:** 2026-11-15
- **Topic:** Forecasting target formulation.
- **Context:** Different operational retail decisions operate on distinct lead-time windows (weekly shelf restocking vs. quarterly vendor quota commitments).
- **Decision:** Train separate, dedicated regression models for four distinct horizons: $D_7$ (7 days), $D_{15}$ (15 days), $D_{30}$ (30 days), and $D_{90}$ (90 days).
- **Reasoning:** Direct multi-horizon modeling with dedicated models avoids recursive multi-step error accumulation and allows horizon-specific feature sets.
- **Alternatives Considered:**
  - Recursive single-day-ahead forecasting rolled out 90 times (rejected: severe error compounding over 90 steps).
  - Predicting only a single fixed horizon (e.g., 30 days) (rejected: insufficient for operational 7-day shelf replenishment).
- **Impact on Other Modules:** API schemas and database tables (`forecasts`) must store horizon identifiers alongside predictions.

---

### TD-003: Strict Transaction Stream Isolation (Gross Sales vs Cancellations vs Returns)
- **Date:** 2026-11-16
- **Topic:** Preprocessing and training target definition.
- **Context:** The raw dataset contains cancellation invoices (beginning with `'C'`), negative quantity adjustments, and normal sales. Mixing these degrades forecasting quality.
- **Decision:** Isolate transactions into three distinct streams:
  1. Gross positive sales demand ($\text{Quantity} > 0$, $\text{Price} > 0$, and no `'C'` prefix).
  2. Cancellations (invoices beginning with `'C'`).
  3. Returns/credit adjustments ($\text{Quantity} < 0$ without `'C'`).
- **Reasoning:** Demand forecasting must predict customer purchasing appetite. Returns and cancellations represent post-purchase friction and supply-chain events, tracked separately in Module 9.
- **Alternatives Considered:**
  - Silently dropping negative rows and cancellations (rejected: conceals return activity and distorts net volume).
  - Training on net quantity directly (rejected: negative targets cause model instability and distort true positive demand).
- **Impact on Other Modules:** Modules 9 and 10 will ingest cancellation and return streams; Module 7 uses only the gross demand stream.

---

### TD-004: Decimal Precision Rule for Financial and Monetary Data
- **Date:** 2026-11-16
- **Topic:** Database precision and currency arithmetic.
- **Context:** Invoicing, taxes, line totals, and inventory unit costs can accumulate floating-point rounding errors if stored as `FLOAT` or `DOUBLE`.
- **Decision:** Strictly mandate `DECIMAL(10, 2)` or `DECIMAL(12, 2)` across all MySQL tables and Python financial calculations.
- **Reasoning:** Standard enterprise accounting practice. Guarantees deterministic penny-perfect arithmetic across invoice generation and credit note adjustments.
- **Alternatives Considered:**
  - `FLOAT` / `DOUBLE` (rejected: IEEE 754 floating-point inaccuracies violate accounting requirements).
  - Storing integers as cents (rejected: complicates ORM calculations and reporting).
- **Impact on Other Modules:** SQLAlchemy models and Pydantic schemas must specify decimal types for prices and totals.

---

### TD-005: Decoupled Offline ML Model Training & Joblib Serving
- **Date:** 2026-11-15
- **Topic:** ML service architecture and FastAPI integration.
- **Context:** Fitting regression models across hundreds of SKUs is computationally intensive and cannot occur inside an HTTP API request lifecycle.
- **Decision:** Train and serialize models offline using Joblib into `backend/ml/models/`. The FastAPI service (`prediction_service.py`) loads these pre-trained estimators into memory at startup as read-only objects.
- **Reasoning:** Guarantees sub-50ms API response latency and prevents server blocking or resource starvation.
- **Alternatives Considered:**
  - Training on-the-fly per API request (rejected: HTTP requests would timeout).
  - External model serving platform (e.g., MLflow, Triton, TorchServe) (rejected: unnecessary complexity for a student project).
- **Impact on Other Modules:** Phase 1 training scripts must produce structured `.joblib` artifacts alongside a metadata manifest before FastAPI inference can be enabled.

---

### TD-006: Server-Enforced RBAC over Frontend Menu Hiding
- **Date:** 2026-11-16
- **Topic:** Security and authorization architecture.
- **Context:** NEXORA serves 6 different employee roles with varying degrees of operational sensitivity.
- **Decision:** Enforce role and permission checks strictly at the FastAPI backend level using dependency injection (`Depends(check_role)`). Frontend UI changes serve only user experience, not security.
- **Reasoning:** Client-side route guarding can be bypassed via direct API calls (e.g., Postman or curl). True security requires backend validation of JWT role claims.
- **Alternatives Considered:**
  - Frontend-only permission checks (rejected: violates fundamental security principles).
  - Role check in UI only (rejected: leaves API wide open).
- **Impact on Other Modules:** Every backend route handler for restricted operations must declare role dependencies.

---

### TD-007: Four-Way Mutually Exclusive and Collectively Exhaustive (MECE) Partitioning
- **Date:** 2026-11-16
- **Topic:** Data preprocessing, reconciliation, and exceptional record handling.
- **Context:** In Phase 1 Task 2, raw retail data needed to be partitioned without dropping records, while isolating pure commercial demand from cancellations, returns, and administrative non-sales adjustments.
- **Decision:** Implement a 4-way MECE classification:
  1. Gross Sales: `Quantity > 0`, `Price > 0`, `Invoice` not starting with `'C'`, and valid identifiers.
  2. Cancellations: `Invoice` starts with `'C'`.
  3. Returns: `Quantity < 0`, `Invoice` does not start with `'C'`.
  4. Exceptional: All remaining records (zero/negative prices, zero quantity, missing critical identifiers).
- **Reasoning:** Guarantees that every raw record is accounted for ($\sum \text{Streams} = \text{Total Raw}$), preventing silent data loss while insulating the ML demand models from contaminated £0 price entries or accounting debt adjustments.
- **Alternatives Considered:**
  - Dropping zero/negative price rows without tracking (rejected: violates NEXORA audit and reconciliation rules).
  - Grouping zero-price items into returns (rejected: inaccurate because many zero-price items are samples or promotional gifts).
- **Impact on Other Modules:** `clean_gross_sales.csv` provides clean training data for Task 3, while `exceptional_transactions.csv` is preserved for finance and data audit views in Module 11.

---

### TD-008: Standardization of Project-Local Virtual Environment (backend/.venv)
- **Date:** 2026-11-16
- **Topic:** Development environment and interpreter standardization.
- **Context:** A developer encountered `ModuleNotFoundError: No module named 'pandas'` because the system PATH defaulted to a bare Python 3.15 executable, while dependencies were installed in Python 3.11 without a project-local virtual environment.
- **Decision:** Standardize all development on a project-local virtual environment located at `backend/.venv` created with Python 3.11.9. Ensure `backend/.venv` is gitignored and referenced in `README.md`.
- **Reasoning:** Eliminates interpreter ambiguity across different developer machines and Google Antigravity sessions. Isolates dependencies per `backend/requirements.txt`.
- **Alternatives Considered:**
  - Relying on global Python installation (rejected: prone to version conflicts and missing PATH variables across team members).
- **Impact on Other Modules:** All terminal scripts, tests, and FastAPI startup commands must be invoked using `backend/.venv`.

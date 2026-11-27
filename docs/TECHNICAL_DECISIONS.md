# TECHNICAL_DECISIONS.md — NEXORA Architectural Decision Records (ADR)

This document formally records technical and architectural decisions (`TD-001`–`TD-019`) made across NEXORA's Phase 1 ML, API, and experimental milestones, together with alignment clarifications against the approved v2.x architecture ([`NEXORA — Technical Blueprint v1.0.md`](NEXORA%20%E2%80%94%20Technical%20Blueprint%20v1.0.md) v2.2, [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.9, [`FEATURES_STATUS.md`](FEATURES_STATUS.md) v2.3, [`ML_DOCUMENTATION.md`](ML_DOCUMENTATION.md) v2.0, and [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) v2.0).

### Status Governance
Every decision carries one standardized `Status` label reflecting current architectural validity and verified repository reality:
- **`ACTIVE (IMPLEMENTED)`** — Approved rule or baseline behavior active in current repository source code/artifacts.
- **`ACTIVE (PLANNED)`** — Approved target architectural/database standard not yet implemented on `main` (`0` live MySQL tables/ORM models).
- **`ACTIVE (EXPERIMENTAL)`** — Active experimental research isolated from production baseline contracts and `/ready`.
- **`HISTORICAL / PARTIALLY SUPERSEDED`** — Preserved early decision whose core historical rationale holds, while specific streams, modules, or counts were evolved or superseded by later decisions/tasks.
- **`SUPERSEDED / RETIRED`** — Retired design replaced by a newer ADR or Blueprint v2.2 architecture; preserved strictly for historical context and must **not** be implemented as current behavior.

### Legacy Module Numbering Note
Older entries below (`TD-003`, `TD-007`, `TD-011`, `TD-014`) cite **Blueprint v1.0** module numbers (`Module 2`–`Module 13`). Current approved NEXORA architecture defines **18 core modules (`M01`–`M18`) + 4 supporting capabilities (`SYS-01`–`SYS-04`)** per [`FEATURES_STATUS.md`](FEATURES_STATUS.md) Section `1.4`: e.g., legacy `Module 2` $\rightarrow$ `M06 Business Intelligence`; legacy `Module 7` $\rightarrow$ `M12 Demand Forecasting` + `M14 Predictive Planner`; legacy `Module 8` $\rightarrow$ `M11 Purchase Planning Simulator`; legacy `Module 9` $\rightarrow$ `M04 Sales Management` + `M16 Return Intelligence`; legacy `Module 10` $\rightarrow$ `M15 Anomaly Detection` + `SYS-03 Smart Alerts`; legacy `Module 11` $\rightarrow$ `M03 Customer Management` + `M17 Billing & Finance`; legacy `Module 13` auth/audit $\rightarrow$ retired auth + `SYS-02 Centralized History & Audit`.

---

### TD-001: Selection of UCI Online Retail II Dataset for Historical Demand
- **Status:** `ACTIVE (IMPLEMENTED)`
- **Date:** 2026-11-15
- **Topic:** Dataset selection and boundaries.
- **Context:** NEXORA requires a rich, multi-year transaction dataset to train multi-horizon demand forecasting models.
- **Decision:** Use the UCI Online Retail II dataset (`online_retail_II.csv`) covering transactions from 2009 to 2011 (`source_origin = 'uci_historical'`).
- **Reasoning:** Contains authentic retail transactions with invoice numbers, stock codes, descriptions, quantities, dates, and unit prices across tens of thousands of records.
- **Alternatives Considered:**
  - Synthetic retail transaction generators (rejected: lacks real-world seasonal and intermittent demand patterns).
  - Kaggle Store Item Demand Forecasting Challenge (rejected: limited SKU metadata and lacks cancellation records).
- **Impact on Other Modules:** The dataset is GBP-denominated (`GBP`) and does not provide live warehouse inventory, supplier lead times, or complete customer addresses. Operational entities must be maintained natively in MySQL using the approved `INR` default currency (`DDR-04`, `source_origin = 'operational'`), keeping historical GBP baselines separated from live operational INR records without implicit currency conversion.

---

### TD-002: Four Decoupled Planning Horizons (7, 15, 30, 90 Days)
- **Status:** `ACTIVE (IMPLEMENTED)`
- **Date:** 2026-11-15
- **Topic:** Forecasting target formulation.
- **Context:** Different operational retail decisions operate on distinct lead-time windows (weekly shelf restocking vs. quarterly vendor quota commitments).
- **Decision:** Train separate, dedicated regression models for four distinct horizons: $D_7$ (7 days), $D_{15}$ (15 days), $D_{30}$ (30 days), and $D_{90}$ (90 days).
- **Reasoning:** Direct multi-horizon modeling with dedicated models avoids recursive multi-step error accumulation and allows horizon-specific feature sets.
- **Alternatives Considered:**
  - Recursive single-day-ahead forecasting rolled out 90 times (rejected: severe error compounding over 90 steps).
  - Predicting only a single fixed horizon (e.g., 30 days) (rejected: insufficient for operational 7-day shelf replenishment).
- **Impact on Other Modules:** Enforced in API schemas (`SUPPORTED_HORIZONS = [7, 15, 30, 90]` in `backend/app/schemas/forecast.py`), committed metadata manifests, and planned MySQL constraints (`DATABASE_SCHEMA.md` v2.9 `model_runs.chk_mr_horizon`, `forecasts.chk_fc_horizon`, and composite `uq_mr_id_horizon` / `fk_fc_run_horizon`).

---

### TD-003: Strict Transaction Stream Isolation (Gross Sales vs Cancellations vs Returns)
- **Status:** `HISTORICAL / PARTIALLY SUPERSEDED` *(Evolved in Phase 1 into 4-way MECE partitioning [`TD-007`] and Stage 2 service-code isolation [`TD-019` / `backend/ml/src/preprocessing.py`])*
- **Date:** 2026-11-16
- **Topic:** Preprocessing and training target definition.
- **Context:** The raw dataset contains cancellation invoices (beginning with `'C'`), negative quantity adjustments, and normal sales. Mixing these degrades forecasting quality.
- **Decision:** Isolate transactions into three distinct streams:
  1. Gross positive sales demand ($\text{Quantity} > 0$, $\text{Price} > 0$, and no `'C'` prefix).
  2. Cancellations (invoices beginning with `'C'`).
  3. Returns/credit adjustments ($\text{Quantity} < 0$ without `'C'`).
- **Reasoning:** Demand forecasting must predict customer purchasing appetite. Returns and cancellations represent post-purchase friction and supply-chain events, tracked separately in legacy Module 9 *(mapped under Blueprint v2.2 to `M04 Sales Management` and `M16 Return Intelligence`)*.
- **Alternatives Considered:**
  - Silently dropping negative rows and cancellations (rejected: conceals return activity and distorts net volume).
  - Training on net quantity directly (rejected: negative targets cause model instability and distort true positive demand).
- **Impact on Other Modules & Current Scope Clarification:** Legacy Modules 9 and 10 correspond under Blueprint v2.2 to `M04 Sales Management` / `M16 Return Intelligence` and `M15 Anomaly Detection` / `SYS-03 Smart Alerts`; legacy Module 7 forecast modeling is now `M12 Demand Forecasting`. Phase 1 UCI historical preprocessing (`TD-007` 4-way MECE + Stage 2 service-code filtering in `preprocessing.py`) trains exclusively on `clean_gross_sales.csv` and does **not** yet implement the planned Phase 4 MySQL B2B pipeline (`DDR-06`, [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.9 Section `6.13`), which will aggregate confirmed `orders` using `effective_date = COALESCE(requested_delivery_date, DATE(created_at))`, subtract `'excess_stock_return'`, `'full_cancellation'`, and `'partial_open_cancellation'` via `demand_adjustments`, and leave `'defective'`/`'damaged'` returns unsubtracted from recurring demand baselines.

---

### TD-004: Decimal Precision Rule for Financial and Monetary Data
- **Status:** `ACTIVE (PLANNED)` *(Authoritative planned MySQL/Phase 2+ rule; `0` live MySQL tables or SQLAlchemy operational financial models exist on `main` today)*
- **Date:** 2026-11-16
- **Topic:** Database precision and currency arithmetic.
- **Context:** Invoicing, taxes, line totals, and inventory unit costs can accumulate floating-point rounding errors if stored as `FLOAT` or `DOUBLE`.
- **Decision:** Mandate exact fixed-point `DECIMAL` types across all operational MySQL tables (`0` `FLOAT`/`DOUBLE` DDL columns) and financial arithmetic per [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.9 Section `5.2` (broadening the initial monetary `(10, 2)`/`(12, 2)` rule to cover all operational decimal domains):
  - Monetary prices, costs, headers, payments, credit notes, refunds: `DECIMAL(10, 2)` and `DECIMAL(12, 2)`.
  - Base-UoM and commercial quantities, inventory balances, demand observations, and persisted `forecasts`: `DECIMAL(14, 4)`.
  - UoM conversion factors: `DECIMAL(12, 6)`.
  - Tax rates, safety buffers, and specialized analytics columns: schema-defined exact scales (`DECIMAL(5, 2)` for `tax_rate`, `DECIMAL(4, 2)` for `safety_factor`, `DECIMAL(10, 4)` for `order_frequency`, `DECIMAL(8, 4)` for `deviation_score`).
- **Reasoning:** Enterprise accounting practice (`DDR-04`) mandates `INR` as the operational default currency, tax-exclusive `ROUND_HALF_UP` header tax calculation, and deterministic fixed-point arithmetic across invoices, credit notes, UoM conversions, and stock ledgers.
- **Alternatives Considered:**
  - `FLOAT` / `DOUBLE` in database storage (rejected: IEEE 754 floating-point inaccuracies violate accounting requirements).
  - Storing integers as cents (rejected: complicates ORM calculations and reporting).
- **Impact on Other Modules & ML Boundary:** Planned Phase 2+ SQLAlchemy models and operational financial/inventory/UoM Pydantic schemas must use `DECIMAL`/`Decimal` with approved rounding rules (`0` operational ORM models exist yet on `main`). Conversely, ML feature matrices, NumPy/scikit-learn estimators, `.joblib` pipeline inference, and Phase 1 stateless API schemas (`forecast.py`, `inventory.py`) legitimately use floating-point numerical computation.

---

### TD-005: Decoupled Offline ML Model Training & Joblib Serving
- **Status:** `ACTIVE (IMPLEMENTED)`
- **Date:** 2026-11-15
- **Topic:** ML service architecture and FastAPI integration.
- **Context:** Fitting regression models across hundreds of SKUs is computationally intensive and cannot occur inside an HTTP API request lifecycle.
- **Decision:** Train and serialize models offline using Joblib into `backend/ml/models/` (production baseline), keeping experimental models isolated in `backend/ml/models_task12/` and `backend/ml/models_experimental/`. At startup (`lifespan` in `backend/app/main.py`), `PredictionService` (`backend/app/services/prediction_service.py`) loads production estimators into memory as read-only objects, isolated from `ExperimentalPredictionService` and `StoreWideService`.
- **Reasoning:** Prevents request-time training or disk I/O blocking and targets **sub-50ms** API inference response time as a **design objective** *(not a verified production HTTP SLA; Phase 6 API latency checks in `DEVELOPMENT_ROADMAP.md` remain unexecuted, and no automated `< 50 ms` test assertion exists in `backend/tests/`)*. For reference, Task 13/15 **experimental** microbenchmarks in [`DEVELOPMENT_LOG.md`](DEVELOPMENT_LOG.md) measured isolated estimator inference (`15.07 ms` 4-horizon mean / `4.53 ms` 1-horizon mean), startup loading (`5,773 ms`), and PIT price binary search (`1.687 microseconds/query`) separately—metrics that must not be conflated with end-to-end production HTTP latency.
- **Alternatives Considered:**
  - Training on-the-fly per API request (rejected: HTTP requests would timeout).
  - External model serving platform (e.g., MLflow, Triton, TorchServe) (rejected: unnecessary complexity for a student project).
- **Impact on Other Modules:** Phase 1 training scripts produce `.joblib` artifacts and `models_metadata.json` manifests prior to serving. In Phase 4+, `DDR-06` governs operational B2B demand and ML integration, while `model_runs` generation isolation (`'production'`, `'experimental'`, `'macro_store_wide'`) and explicit controlled model promotion (never automatic by WAPE) are governed by [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.9 Sections `3.8` and `6.12`.

---

### TD-006: Server-Enforced RBAC over Frontend Menu Hiding
- **Status:** `SUPERSEDED / RETIRED`
- **Date:** 2026-11-16
- **Topic:** Security and authorization architecture *(Historical Blueprint v1.0 Draft Context Only)*.

> [!WARNING]
> **SUPERSESSION NOTICE — DO NOT IMPLEMENT FOR CURRENT NEXORA:**
> The six-role authentication and server-enforced JWT/RBAC design below was **permanently retired** by approved **Technical Blueprint v2.2**, [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.9 Section `1.1`, [`FEATURES_STATUS.md`](FEATURES_STATUS.md) Section `1.4` (`FEAT-M13-01`–`FEAT-M13-03` marked `RETIRED`), [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) Section `1.4`, and [`AGENTS.md`](../AGENTS.md) Section `9.9`.
>
> **Approved Current Architecture (`SYS-01`):**
> - NEXORA uses **four UI-only operational workspaces**: `Store Manager (Admin)`, `Inventory Staff`, `Purchase Manager`, and `Finance Staff`.
> - Workspace selection is **UI-level navigation and `X-NEXORA-Workspace` provenance context only** — NEXORA does **not** implement user authentication, password-based login, JWT identity verification, server-enforced RBAC, or `Depends(check_role)` dependencies.
> - Developers and agents must **never** implement `/api/v1/auth/*`, `users`/`roles`/`permissions` tables, or JWT/RBAC dependencies unless a separate post-v2.2 authentication redesign is explicitly approved.

- **Context *(Historical)*:** Earlier v1.0 planning assumed NEXORA served 6 different employee roles with varying degrees of operational sensitivity.
- **Decision *(Retired)*:** Enforce role and permission checks strictly at the FastAPI backend level using dependency injection (`Depends(check_role)`). Frontend UI changes serve only user experience, not security.
- **Reasoning *(Historical Context Only)*:** Client-side route guarding can be bypassed via direct API calls (e.g., Postman or curl); if an authenticated multi-user security boundary were ever introduced in a separate future redesign, true enforcement would require backend verification of credentials/tokens rather than UI hiding.
- **Alternatives Considered:**
  - Frontend-only permission checks (rejected as a security boundary).
  - Role check in UI only (noted as non-cryptographic; current NEXORA intentionally omits authentication and models workspace selection strictly as operational UX context).
- **Impact on Other Modules:** Retired (`0` auth/RBAC routes or tables exist or are planned). Replaced by `SYS-01` Workspace Selection and `X-NEXORA-Workspace` provenance tracking.

---

### TD-007: Four-Way Mutually Exclusive and Collectively Exhaustive (MECE) Partitioning
- **Status:** `ACTIVE (IMPLEMENTED)`
- **Date:** 2026-11-16
- **Topic:** Data preprocessing, reconciliation, and exceptional record handling.
- **Context:** In Phase 1 Task 2, raw retail data needed to be partitioned without dropping records, while isolating pure commercial demand from cancellations, returns, and administrative non-sales adjustments.
- **Decision:** Implement a Stage 1 4-way MECE classification (`classify_transactions()` in `backend/ml/src/preprocessing.py`):
  1. Gross Sales: `Quantity > 0`, `Price > 0`, `Invoice` not starting with `'C'`, and valid identifiers.
  2. Cancellations: `Invoice` starts with `'C'`.
  3. Returns: `Quantity < 0`, `Invoice` does not start with `'C'`.
  4. Exceptional: All remaining records (zero/negative prices, zero quantity, missing critical identifiers).
- **Reasoning:** Guarantees that every raw record is accounted for ($\sum \text{Streams} = \text{Total Raw}$), preventing silent data loss while insulating the ML demand models from contaminated £0 price entries or accounting debt adjustments.
- **Alternatives Considered:**
  - Dropping zero/negative price rows without tracking (rejected: violates NEXORA audit and reconciliation rules).
  - Grouping zero-price items into returns (rejected: inaccurate because many zero-price items are samples or promotional gifts).
- **Impact on Other Modules:** Subsequently extended in Stage 2 (`save_processed_data(filter_service_codes=True)` in [`backend/ml/src/preprocessing.py`](../backend/ml/src/preprocessing.py), `TD-019`, and [`ML_DOCUMENTATION.md`](ML_DOCUMENTATION.md) Section `4.1`), which filters 11 non-merchandise service codes out of the gross-sales stream into `service_transactions.csv` before writing commercial merchandise records (`clean_gross_sales.csv`) for downstream daily aggregation — Stage 2 is a downstream filter on Stage 1 gross sales rather than a fifth Stage 1 MECE stream. `exceptional_transactions.csv` is retained for finance/audit inspection in legacy Module 11 (`M17 Billing & Finance` / `M04 Sales Management` per [`FEATURES_STATUS.md`](FEATURES_STATUS.md) Section `1.4`).

---

### TD-008: Standardization of Project-Local Virtual Environment (backend/.venv)
- **Status:** `ACTIVE (IMPLEMENTED)`
- **Date:** 2026-11-16
- **Topic:** Development environment and interpreter standardization.
- **Context:** A developer encountered `ModuleNotFoundError: No module named 'pandas'` because the system PATH defaulted to a bare Python 3.15 executable, while dependencies were installed in Python 3.11 without a project-local virtual environment.
- **Decision:** Standardize all development on a project-local virtual environment located at `backend/.venv` created with Python 3.11.9. Ensure `backend/.venv` is gitignored and referenced in `README.md`.
- **Reasoning:** Eliminates interpreter ambiguity across different developer machines and Google Antigravity sessions. Isolates dependencies per `backend/requirements.txt`.
- **Alternatives Considered:**
  - Relying on global Python installation (rejected: prone to version conflicts and missing PATH variables across team members).
- **Impact on Other Modules:** All terminal scripts, tests, and FastAPI startup commands must be invoked using `backend/.venv`.

---

### TD-009: SKU Lifespan Boundary Imputation vs Global Calendar Imputation
- **Status:** `ACTIVE (IMPLEMENTED)` *(Phase 1 CSV panel active; source-specific boundaries govern planned `daily_demand_observations` in [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.9 Section `3.8`)*
- **Date:** 2026-11-16
- **Topic:** Continuous time-series generation, zero-demand imputation, and temporal boundary integrity.
- **Context:** In Phase 1 Task 3, daily retail sales needed to be padded with zero-demand records to support lag feature construction. Products in the UCI dataset were introduced, traded, and phased out at different points between 2009 and 2011.
- **Decision:** Impute continuous calendar days strictly within each individual SKU's observed lifespan boundaries ($[\text{min\_date}, \text{max\_date}]$). Do not impute dates prior to a product's first recorded sale or after its final recorded sale.
- **Reasoning:**
  1. A product cannot have "zero sales" before it exists in the catalog or after it has been permanently discontinued. Pre-launch zero-inflation would artificially bias moving averages downward and distort lag distributions.
  2. Imputing within $[\text{min\_date}, \text{max\_date}]$ captures legitimate interior zero-demand days during an active lifecycle — **74.30%** in the initial Phase 1 1-year snapshot (`2010-12-01` to `2011-12-09`) and **76.78%** (`1,756,250 / 2,287,495` rows across `4,905` commercial SKUs spanning `2009-12-01` to `2011-12-09`) in the current tracked 2-year `daily_product_demand.csv` panel (`TD-019`, [`ML_DOCUMENTATION.md`](ML_DOCUMENTATION.md) Section `5.1`) — without introducing artificial calendar leakage. *(These two dataset snapshots are kept distinct.)*
- **Alternatives Considered:**
  - Global calendar grid imputation across all SKUs from `2010-12-01` to `2011-12-09` (initial 1-year reference; rejected: would inflate the dataset with over 1.4 million synthetic zero rows for products introduced late in 2011, contaminating demand velocity statistics).
  - Dropping days with zero sales (rejected: breaks time-series continuity, invalidating lag shifts $t-k$ and rolling windows).
- **Impact on Other Modules & Planned Operational Rule (`DATABASE_SCHEMA.md` v2.9 Section `3.8`):** `daily_product_demand.csv` (`is_imputed`) preserves continuous date ranges per product for lag/rolling calculation. In the planned `daily_demand_observations` schema, only two `source_origin` values are permitted (`'uci_historical'` and `'operational'`), cleanly distinguishing:
  1. **Interior zero-demand days** inside a source's own active window (`[uci_min_date, uci_max_date]` or `[op_first_confirmed_date, aggregation_cutoff]`): `is_zero_padded = TRUE`.
  2. **Actually observed days** whose net confirmed demand after adjustments equals `0.0000`: `is_zero_padded = FALSE`.
  3. **Out-of-window / unobserved gaps** (before launch, after cutoff, and explicitly across the multi-year historical UCI-to-operational gap such as `2011–2026`): **never zero-padded**.

---

### TD-010: Incomplete Multi-Horizon Target Handling via NaN Preservation
- **Status:** `ACTIVE (IMPLEMENTED)`
- **Date:** 2026-11-17
- **Topic:** Forward-looking target generation, incomplete horizon handling, and label leakage prevention.
- **Context:** In Phase 1 Task 4, multi-horizon cumulative targets ($D_7, D_{15}, D_{30}, D_{90}$) were constructed. Each product's series ends at its last observed sale date (`max_date`). For rows within $H$ days of `max_date`, complete future demand is unobserved.
- **Decision:** Strictly mark forward targets as missing (`NaN`) whenever the complete future window of $H$ days is unavailable. Never fill incomplete future windows with zero, partial sums, or forward-filled values.
- **Reasoning:**
  1. An unobserved future period is not evidence of zero consumer demand. Assuming zero sales for future dates beyond the observation window would artificially bias demand predictions downward, causing severe under-forecasting in operational models.
  2. Partial sums over fewer than $H$ days would create target scale distortion (e.g., comparing a 3-day sum to a full 7-day target), degrading regression loss functions.
  3. Preserving `NaN` allows model training to cleanly select valid instances (`df[target].notnull()`) independently for each horizon — in the Phase 1 `ml_feature_dataset.csv` artifact (`1,074,653` total rows), $D_7$ has `945,345` eligible rows and $D_{90}$ has `661,228` eligible rows ([`ML_DOCUMENTATION.md`](ML_DOCUMENTATION.md) Section `6`) — without label contamination.
- **Alternatives Considered:**
  - Zero-padding future unobserved days (rejected: creates false zero-sales signals for high-velocity items).
  - Truncating all SKUs to a single arbitrary cut-off date (rejected: needlessly discards hundreds of thousands of valid training rows for shorter horizons like $D_7$ and $D_{15}$).
- **Impact on Other Modules:** Both production training (`train.py`) and experimental evaluation filter non-null target masks independently per horizon model and test strictly against complete horizons.

---

### TD-011: Strict Chronological Purge/Embargo Window Splitting
- **Status:** `ACTIVE (IMPLEMENTED)`
- **Date:** 2026-11-17
- **Topic:** Time-series validation, leakage prevention, and out-of-time evaluation boundaries.
- **Context:** In Phase 1 Task 5, multi-horizon models ($D_7, D_{15}, D_{30}, D_{90}$) required empirical evaluation. In multi-day cumulative regression, an observation at date $t$ carries a forward label spanning $t+1..t+H$. Simple date-based train/validation splitting without purging would allow training observation targets to overlap into the validation period.
- **Decision:** Mandate an explicit purge/embargo cutoff rule: for validation starting at date $V$, a training sample is eligible if and only if $t_{\text{train}} + H < V$ ($t_{\text{train}} \le V - H - 1\text{ day}$).
- **Reasoning:**
  1. Guarantees that zero future target information from the training set leaks into the validation period.
  2. Ensures that validation samples are evaluated strictly out-of-time against genuine unseen future trading periods.
  3. Formulates a rigorous academic evaluation methodology defendable in viva and technical demonstrations.
- **Alternatives Considered:**
  - Standard k-fold cross-validation or random train/test split (rejected: severe temporal leakage, producing artificially inflated accuracy metrics).
  - Splitting on date $V$ without an embargo (rejected: samples observed $t \in [V - H, V]$ would have targets extending into the validation period).
- **Impact on Other Modules:** Phase 1 single-holdout production evaluation (`backend/ml/src/evaluate.py`, `get_chronological_split()`) enforces this cutoff directly, while Task 12 experimental multi-fold cross-validation extends it across 3 expanding date-grouped folds via `DateGroupedTimeSeriesSplit` (`backend/ml/src/time_series_split.py`, invoked in [`backend/ml/experiments/model_selection_task12.py`](../backend/ml/experiments/model_selection_task12.py)). All forecasting evaluation workflows under legacy Modules 2, 7, and 10 (now primarily **`M12 Demand Forecasting`**, alongside `M06 Business Intelligence` and `M15 Anomaly Detection` per [`FEATURES_STATUS.md`](FEATURES_STATUS.md) Section `1.4`) must adhere to chronological embargo protection.

---

### TD-012: Continuous TargetEncoder for High-Cardinality Retail Product SKUs
- **Status:** `SUPERSEDED / RETIRED` *(Superseded by `TD-013` for Production Baseline; experimental chronological target encoding researched separately in `TD-017`)*
- **Date:** 2026-11-17
- **Topic:** Categorical encoding, pipeline architecture, and inference resilience.
- **Context:** The initial Phase 1 training catalog contained 3,922 unique alphanumeric product SKUs (`StockCode`). One-hot encoding all 3,922 sparse/dense columns causes memory exhaustion (>8 GB array allocations) and slow training for tree-based estimators like Random Forest over 800,000+ samples, whereas label/ordinal encoding artificially imposes ordinal arithmetic relationships on discrete products.
- **Decision:** Implement scikit-learn's `TargetEncoder(smooth="auto", cv=KFold(5, shuffle=False), target_type="continuous")` coupled with `StandardScaler` inside a unified `Pipeline`.
- **Reasoning:**
  1. Compresses high-cardinality SKUs into a single informative continuous feature representing empirical target demand conditioned on SKU, with out-of-fold cross-validation and Bayes smoothing to limit overfitting.
  2. Ensures that unseen product SKUs at inference time automatically impute the global prior mean target without throwing exceptions or failing requests.
  3. Keeps preprocessing entirely self-contained inside the `.joblib` serialized pipeline, ensuring identical transformations during offline evaluation and live FastAPI serving.
- **Alternatives Considered:**
  - Unconstrained high-cardinality `OneHotEncoder` (rejected: causes memory exhaustion and excessive artifact size).
  - `OrdinalEncoder` (rejected: imposes arbitrary numerical distances between unrelated products).
- **Impact on Other Modules:** Superseded by `TD-013` following the Phase 1 Task 5.1 Temporal Leakage Audit.

---

### TD-013: OneHotEncoder Infrequent Categorical Encoding vs TargetEncoder Temporal Leakage
- **Status:** `ACTIVE (IMPLEMENTED)` *(Authoritative Phase 1 Production Baseline Contract)*
- **Date:** 2026-11-17
- **Topic:** Temporal target leakage elimination in high-cardinality SKU encoding.
- **Context:** During the Phase 1 Task 5.1 technical audit, `TargetEncoder(smooth="auto", cv=KFold(5, shuffle=False))` was inspected for temporal leakage. Because `KFold` is non-temporal, target values from future dates (e.g., in fold 4) were used to compute SKU target encodings for earlier training observations (e.g., in folds 0–3). This introduced internal cross-fitting target leakage into the training phase.
- **Decision:** Replace `TargetEncoder` in production training (`backend/ml/src/train.py`) with `OneHotEncoder(max_categories=50, handle_unknown="infrequent_if_exist", sparse_output=False)`. In the committed Phase 1 training dataset (`3,922` SKUs), the top 50 frequent high-volume SKUs receive individual binary indicator columns, while all remaining `3,872` SKUs (plus any additional SKUs from the later `4,905`-SKU 2-year serving panel and unseen SKUs at inference) collapse into a single `infrequent_SKU` category.
- **Reasoning:**
  1. **Zero Target Leakage:** `OneHotEncoder` is purely unsupervised; it maps category identifiers without ever reading target labels $y$. Future target values cannot leak into earlier feature representations.
  2. **Bounded Dimensionality:** Constraining `max_categories=50` adds 51 columns (top 50 + 1 infrequent) regardless of total catalog size, avoiding memory bloat and recording per-horizon Random Forest fit times of `6.589s`–`23.4s` in [`backend/ml/models/models_metadata.json`](../backend/ml/models/models_metadata.json) (`D_7` RF: `23.4s`; `D_15` RF: `20.583s`; `D_30` RF: `17.293s`; `D_90` RF: `6.589s`, while Ridge fit time was `0.457s`–`1.709s`).
  3. **Robust Unseen SKU Handling:** `handle_unknown="infrequent_if_exist"` ensures any unseen or non-top-50 SKU encountered during inference smoothly activates the infrequent indicator without raising an error.
  4. **Empirical Performance (`models_metadata.json` Production Baseline):** Ridge linear regression achieved **55.65%** WAPE (`55.654%`) on $D_7$, and Random Forest achieved **50.00%** (`50.0048%`) on $D_{15}$, **48.73%** (`48.7296%`) on $D_{30}$, and **53.22%** (`53.2187%`) on $D_{90}$ — all outperforming the Seasonal Naïve baseline (`66.12%` / `59.57%` / `61.98%` / `71.09%`) without target leakage.
- **Alternatives Considered:**
  - Rolling target encoding (rejected for Phase 1 production: higher complexity; later explored experimentally in `TD-017`).
  - Raw `OrdinalEncoder` (rejected: creates false numeric hierarchy among SKUs).
- **Impact on Other Modules:** Serialized production pipelines in `backend/ml/models/` (`demand_model_{7,15,30,90}d.joblib`) accept 10-column DataFrame inputs and were **not** automatically retrained on the later 2-year `4,905`-SKU commercial serving catalog (`HistoricalDataService`).

---

### TD-014: FastAPI Multi-Horizon Prediction Service & Lifespan Architecture
- **Status:** `ACTIVE (IMPLEMENTED)`
- **Date:** 2026-11-17
- **Topic:** ML model serving, lifespan memory management, and multi-horizon inference API.
- **Context:** Phase 1 Task 6 required integrating the four trained production model artifacts (`demand_model_{7,15,30,90}d.joblib`) into FastAPI while avoiding per-request disk I/O, preserving backward compatibility (`horizon_days: int` vs `horizons: List[int]`), and matching the 10-column training contract.
- **Decision:**
  1. Implement `PredictionService` (`backend/app/services/prediction_service.py`) initialized once at application startup via FastAPI's async `lifespan` handler (`backend/app/main.py`) so production `.joblib` models and `models_metadata.json` remain resident in RAM alongside `HistoricalDataService` (`backend/app/services/historical_data_service.py`). Experimental Task 12 models are loaded independently into `ExperimentalPredictionService` (`backend/app/services/experimental_prediction_service.py`) without gating `/ready` (`test_experimental_models_unavailable_failure_isolation`).
  2. Support both multi-horizon queries (`horizons: [7, 15, 30, 90]`) and legacy single-horizon (`horizon_days: int`) requests in `ForecastRequest`, plus automatic historical CSV feature extraction (`HistoricalDataService.get_features_for_sku()` when no manual features are supplied, enforcing `HTTP 404` on unknown SKUs and `HTTP 422` when fewer than `29` continuous calendar days exist).
  3. Format incoming payloads into a strictly typed 10-column pandas DataFrame: `['StockCode', 'DayOfWeek', 'Month', 'DayOfMonth', 'Lag1', 'Lag7', 'Lag14', 'Lag28', 'RollingMean7', 'RollingMean28']`.
  4. Enforce non-negativity post-processing $\max(0.0, \hat{y})$ and finiteness checks (`NaN`/`Inf` rejection).
  5. Emit an informational warning in `ForecastResponse.warnings` when a requested `StockCode` falls outside the top-50 `frequent_skus` while relying on `OneHotEncoder(handle_unknown="infrequent_if_exist")` for robust inference.
- **Reasoning:**
  - Eliminates request-time disk I/O and keeps in-memory SKU lookup (`HistoricalDataService`), feature assembly, and model execution decoupled and thread-safe (`threading.Lock()`). Note: while in-memory SKU lookup is sub-millisecond and experimental Task 13 microbenchmarks measured estimator prediction latency (`4.53 ms` 1-horizon / `15.07 ms` 4-horizon mean), end-to-end HTTP endpoint latency is a design priority rather than a verified sub-millisecond or `< 50 ms` production SLA (`TD-005`).
  - Resolves `ISSUE-001` cleanly with zero breaking changes to client contracts and strict compliance with Phase 1 zero-leakage contracts.
- **Alternatives Considered:**
  - On-demand lazy model loading (rejected: introduces latency jitter on first request and potential race conditions).
  - Training inside the API request cycle (rejected: strictly prohibited).
- **Impact on Other Modules:** Production routes (`/api/v1/forecast/*`) belong to **`M12 Demand Forecasting`**, feeding planned **`M14 Predictive Planner`** and **`M11 Purchase Planning Simulator`** (legacy Modules 7 and 8 per [`FEATURES_STATUS.md`](FEATURES_STATUS.md) Section `1.4`). On `main`, `POST /api/v1/inventory/recommend` (`backend/app/services/inventory_service.py`) operates solely as a stateless Phase 1 prototype accepting caller-supplied stock/lead-time parameters and is **not** a full MySQL-backed `M14` implementation (`DDR-01`–`DDR-03`).

---

### TD-015: Dual-Hierarchical Retail Forecasting (Store-Wide Macro vs SKU-Level Micro)
- **Status:** `ACTIVE (EXPERIMENTAL)` *(Comparative & store-wide macro research only — not production SKU replenishment)*
- **Date:** 2026-11-20
- **Topic:** Forecasting hierarchy distinction and empirical WAPE disparity resolution.
- **Context:** During model benchmarking, external claims of ~10% WAPE on the UCI Online Retail II dataset were audited against NEXORA's ~50% SKU-level WAPE.
- **Decision:** Formalize a dual-tier analytical comparison (`backend/ml/experiments/store_wide_forecasting.py`, `backend/app/services/store_wide_service.py`) distinguishing:
  1. **Tier 1 — Store-Wide (Macro) Demand (`EXPERIMENTAL`):** Daily store-level demand summed across all catalog SKUs in `backend/ml/models_experimental/store_wide/store_metadata.json`, canceling intermittent Poisson noise and achieving best-model macro WAPE of **`5.61%` to `12.15%`** across all four horizons: **`D_7`: `8.87%`** (`Moving_Average_28`), **`D_15`: `12.15%`** (`Random_Forest`), **`D_30`: `7.56%`** (`HistGradientBoosting`), and **`D_90`: `5.61%`** (`HistGradientBoosting`).
  2. **Tier 2 — SKU-Level (Micro) Demand:** Disaggregated demand per individual SKU for inventory replenishment and stockout prevention, where intermittent sparsity yields higher theoretical error (~45%–56% WAPE depending on horizon/generation).
- **Reasoning & Provenance Note:** Proves empirically that external ~10% WAPE figures correspond to macro store totals rather than intermittent SKU replenishment series. Both `GET /api/v1/forecast/evaluation-comparison` and `GET /api/v1/forecast/store-wide` are **`EXPERIMENTAL`** research endpoints reading static JSON snapshots (`models_experimental/`). Note on dataset provenance: `store_metadata.json` records `739` calendar days and `11,420,305` units (`2026-11-20`, reflecting the pre-Task-24 2-year panel before removing `17,563` service-code units), whereas `store_wide_service.py` retains a static description string referencing `"3,922 catalog SKUs"`; neither artifact reflects a retrain on the post-Task-24 `4,905`-SKU commercial panel.
- **Alternatives Considered:**
  - Claiming 10% WAPE on SKU-level by using random train/test splits (rejected: violates chronological causality and causes catastrophic data leakage).
  - Ignoring the external discrepancy (rejected: leaves stakeholders without empirical comparison across aggregation levels).
- **Impact on Other Modules:** Comparative macro metrics support analytical explanation only and do not feed production `M14` replenishment or alter `backend/ml/models/`.

---

### TD-016: Baseline-Anchored Residual Regressor Formulation for Multi-Horizon Demand
- **Status:** `ACTIVE (EXPERIMENTAL)` *(Task 12 `models_task12/` `D_15` experimental model research — NOT production and NOT used by Phase 2 CRUD)*
- **Date:** 2026-11-20
- **Topic:** Multi-horizon demand model architecture and tree-underfitting resolution.
- **Context:** Direct regression on multi-horizon cumulative sums ($D_{15}, D_{30}, D_{90}$) suffered from negative prediction bias (-25.14% on $D_{90}$ in Phase 1 production baseline) due to decision tree saturation in shallow Random Forests.
- **Decision:** Formulate forecasting as a baseline-anchored residual decomposition:
  $$\hat{y} = \max\left(0,\ \text{multiplier} \times X[\text{base\_feature}] + \hat{r}(X)\right)$$
  Implemented via `ResidualRegressor` (`backend/ml/src/residual_model.py`), where a moving-average run-rate anchors the forecast and a regularized linear estimator (`Ridge`) models the residual deviation $\hat{r}$.
- **Reasoning & Verified Artifact Attribution:**
  1. Preserves physical scale consistency across multi-day horizons (`multiplier = h`).
  2. **Do not conflate experimental runs or generalize `D_15` across all horizons:**
     - **Intermediate `models_experimental/` run (`backend/ml/models_experimental/models_metadata.json`, `2026-11-20T06:40:57Z`):** Used the pre-`TD-017` `TargetEncoder(cv=5)` and 15/17 features, recording `46.34%` WAPE on $D_{15}$ (`ResidualRegressor(MA28, h=15) + Ridge`, +3.66 pp vs. production) and `45.37%` on $D_{30}$ (`ResidualRegressor(MA28, h=30) + Ridge`, +3.36 pp vs. production).
     - **Task 12 `models_task12/` run (`backend/ml/models_task12/models_metadata.json`, `2026-11-20T10:10:47Z`):** Uses leakage-free `ChronologicalTargetEncoder` + PIT price (`20`-col input / `19` features + `date`) and 3-fold `DateGroupedTimeSeriesSplit` CV. There, `Residual_RollingMean28_Ridge_a_100.0` was selected **strictly for $D_{15}$**, achieving **`44.88%` untouched holdout WAPE** (`71.90%` pooled 3-fold CV WAPE), whereas `ElasticNet` linear pipelines won $D_7$ (`54.20%` holdout), $D_{30}$ (`45.10%` holdout), and $D_{90}$ (`48.22%` holdout).
  3. Seamlessly integrates with scikit-learn `Pipeline` and Joblib serialization.
- **Alternatives Considered:**
  - Training deeper random forests with 500+ trees (rejected: slow training, memory bloat, and persistent bias during seasonal regime shifts).
  - Pure moving average without residual adjustments (rejected: misses short-term momentum and price dynamics).
- **Impact on Other Modules & Promotion Boundary:** Neither `backend/ml/models_experimental/` nor `backend/ml/models_task12/` is used for Phase 2 operational CRUD or production predictive purchasing. Production endpoints (`/api/v1/forecast/*`) continue serving `backend/ml/models/` (`TD-013`), while Task 12 artifacts remain strictly isolated under `/api/v1/experimental/*`. Experimental models are **never** automatically promoted to production based on WAPE; any future promotion requires explicit controlled transition per [`DATABASE_SCHEMA.md`](DATABASE_SCHEMA.md) v2.9 Section `6.12` (`model_runs`).

---

### TD-017: Chronological Expanding-Window Target Encoding with Horizon Embargo
- **Status:** `ACTIVE (EXPERIMENTAL)` *(Task 12 experimental feature contract — NOT production `TD-013`)*
- **Date:** 2026-11-20
- **Topic:** Temporal target leakage elimination in categorical feature encoding.
- **Context:** Standard scikit-learn `TargetEncoder` cross-fitting (`cv=KFold(5, shuffle=False)` in `TD-012` and `cv=5` in intermediate `models_experimental/`, regardless of `shuffle` configuration) uses non-chronological partitions, allowing targets from future dates in later folds to contaminate earlier training rows' SKU encodings.
- **Decision:** Implement `ChronologicalTargetEncoder` (`backend/ml/src/chronological_encoder.py`), which computes m-smoothed cumulative target statistics strictly from historically realized dates $t \le T - (h + 1)$ for any forecast date $T$.
- **Reasoning:**
  1. Guarantees `0.0` future perturbation leakage: modifying future targets produces exact zero change on earlier encodings (`test_leakage_corrections.py`).
  2. Applies empirical Bayes smoothing (`smooth = 10.0`, `default_prior = 0.0`) with cumulative historical global prior (`final_encodings_`) for tail SKUs.
  3. Out-of-sample / inference rows map to frozen cumulative statistics learned from the full training set, falling back to `global_prior_` for unseen SKUs.
- **Alternatives Considered:**
  - Production `OneHotEncoder(max_categories=50)` (`TD-013`; retained for production baseline stability, whereas `TD-017` investigates continuous target encoding across all SKUs without collapsing tail SKUs into a single indicator).
  - Non-chronological K-Fold `TargetEncoder` (rejected: temporal cross-fitting target leakage).
- **Impact on Other Modules:** Used exclusively inside the experimental SKU optimization and Task 12 pipelines ([`backend/ml/src/chronological_encoder.py`](../backend/ml/src/chronological_encoder.py) and [`backend/ml/experiments/model_selection_task12.py`](../backend/ml/experiments/model_selection_task12.py)), served behind `/api/v1/experimental/*` (`ExperimentalPredictionService`). Production inference (`/api/v1/forecast/*`) continues using the `TD-013` 10-column `OneHotEncoder` feature contract.

---

### TD-018: Point-in-Time Historical Unit Price Aggregation & Coverage Restoration
- **Status:** `ACTIVE (EXPERIMENTAL)` *(Task 8/10/12 SKU experimental pipelines & `/api/v1/experimental/*` — NOT production baseline `TD-013` or macro/intermediate models)*
- **Date:** 2026-11-20
- **Topic:** Point-in-time price signals and validation sample preservation.
- **Context:** Naive global median SKU pricing leaked future price regimes, and dropping rows lacking 60-day history excluded 3,343 rows in $D_{30}$ and 2,329 rows in $D_{90}$ during earlier Task 8 runs (`ISSUE-010`).
- **Decision:**
  1. Implement `enrich_daily_with_pit_price` (`backend/ml/src/point_in_time_price.py`), computing expanding historical arithmetic mean SKU `UnitPrice` strictly from commercial sales occurring prior to forecast origin ($\text{tx\_date} < T$, excluding same-day `tx_date == T`), with expanding global historical fallback and default prior `2.10`.
  2. Implement `PointInTimePriceService` (`backend/ml/src/point_in_time_price.py`) building and caching prefix sums/counts (`pit_sku_price_history.json` with source size/mtime fingerprinting and atomic file replacement) for cutoff-aware experimental serving via `HistoricalDataService.get_unit_price(stock_code, as_of_date=...)` without blocking production `/ready`.
  3. Restore validation coverage by imputing missing `Lag60` and `RollingMean60` with `Lag28` and `RollingMean28` plus `Has60dHistory` (`1.0` if $\ge 61$ days history, else `0.0`).
  4. Implement `DateGroupedTimeSeriesSplit` (`backend/ml/src/time_series_split.py`) keeping all SKUs per date in the same fold and enforcing horizon embargo gaps ($\ge h + 1$).
- **Reasoning:** Restores 100% of validation rows matching the exact **Task 8 (`ISSUE-010`) 1-year baseline counts** (`42,091` on $D_7$, `57,840` on $D_{15}$, `100,262` on $D_{30}$, `98,157` on $D_{90}$). In the subsequent **Task 12 (`model_selection_task12.py`) 2-year holdout evaluation** (`backend/ml/models_task12/models_metadata.json`), untouched holdout validation spans **`42,106`** ($D_7$), **`57,906`** ($D_{15}$), **`100,527`** ($D_{30}$), and **`98,639`** ($D_{90}$) rows cleanly without target or price leakage.
- **Alternatives Considered:**
  - Forward-filling full dataset prices without cutoff (rejected: leaks future price regimes into early rows).
  - Dropping rows with $< 60$ days of history (rejected: causes unequal validation comparisons).
- **Impact on Other Modules:** Standardized specifically across Task 8, Task 10, and Task 12 SKU experimental pipelines (20-column input DataFrame in `ExperimentalPredictionService`), isolated behind `/api/v1/experimental/*`. Intermediate `models_experimental/` (15/17 features without `Has60dHistory`) and store-wide macro models (`store_wide_forecasting.py`) do not use this 20-column pipeline, and production baseline (`/api/v1/forecast/*`) remains on the 10-column `TD-013` contract without `UnitPrice`.

---

### TD-019: Full 2-Year Dataset Recovery & Non-Merchandise Service Code Isolation
- **Status:** `ACTIVE (IMPLEMENTED)` *(2-year consolidated raw dataset & Stage 2 service-code isolation active in `preprocessing.py` and `daily_product_demand.csv`; historical Task 10 panel/WAPE snapshot noted distinctly)*
- **Date:** 2026-11-20
- **Topic:** Multi-sheet XLSX-to-CSV recovery, non-merchandise service code isolation, and 2-year time-series expansion.
- **Context:** The initial Phase 1 `online_retail_II.csv` export contained only the single year 2010–2011 (`541,910` records) due to active-sheet export behavior from `online_retail_II.xlsx`. Year 2009–2010 (`525,461` records) was omitted, and non-merchandise codes (`POST`, `DOT`, `M`, `BANK CHARGES`, `PADS`, `AMAZONFEE`, `D`, `CRUK`, `ADJUST`, `TEST001`, `C2`) were mixed into gross sales.
- **Decision:**
  1. Consolidate both worksheets from `online_retail_II.xlsx` via `backend/ml/src/convert_xlsx_to_csv.py` into unified `backend/ml/data/raw/online_retail_II.csv` totaling `1,067,371` rows (`2009-12-01` to `2011-12-09`, standardized ISO timestamps). *(An early untracked/local backup reference `online_retail_II_2010_2011_backup.csv` is gitignored and absent from the repository; do not rely on its local availability.)*
  2. Isolate the 11 non-merchandise service codes (`4,581` records / `17,563` units) into `service_transactions.csv` directly during Stage 2 preprocessing (`backend/ml/src/preprocessing.py`, `ISSUE-015` Task 22), leaving `1,037,089` pure commercial merchandise rows in `clean_gross_sales.csv` (originally filtered inside `sku_level_optimization.py` before upstreaming into `preprocessing.py`).
  3. Regenerate continuous daily demand (`backend/ml/data/processed/daily_product_demand.csv`):
     - **Current Verified Panel (post-Task 24 / `ISSUE-016`):** **`2,287,495` product-day rows**, **`4,905` commercial SKUs**, **`11,402,742` total units**, `738` calendar days span (`739` inclusive calendar dates, `0` service codes).
     - **Historical Task 10 Snapshot (`2026-11-20`, pre-Task 24):** Originally aggregated **`2,292,587` product-days** across **`4,916` SKUs** prior to eliminating the `5,092` service-code SKU-day rows in Task 24.
- **Reasoning & Benchmark Separation:**
  1. Expands calendar history from 374 to `739` inclusive calendar dates (`500+` training dates), enabling multi-fold chronological CV with 91-day $D_{90}$ embargoes (`ISSUE-007`).
  2. Prevents non-inventory ledger codes (postage, bank fees) from distorting inventory forecasting and PIT pricing (`pit_sku_price_history.json` indexes `4,905` SKUs).
  3. **Benchmark Attribution (Do Not Conflate Across Generations):**
     - **Task 10 (`sku_level_optimization.py`, experimental benchmark):** $D_7$: `53.94%`, $D_{15}$: `44.87%`, $D_{30}$: `44.76%`, $D_{90}$: `51.73%`.
     - **Task 12 (`models_task12/models_metadata.json`, experimental holdout):** $D_7$: `54.20%`, $D_{15}$: `44.88%`, $D_{30}$: `45.10%`, $D_{90}$: `48.22%`.
     - **Production Phase 1 Baseline (`models/models_metadata.json`, 1-year `ml_feature_dataset.csv`):** $D_7$: `55.65%`, $D_{15}$: `50.00%`, $D_{30}$: `48.73%`, $D_{90}$: `53.22%`.
     - **Store-Wide Experimental Macro (`models_experimental/store_wide/store_metadata.json` across all 4 horizons):** **`5.61%`–`12.15%`** ($D_7$: `8.87%`, $D_{15}$: `12.15%`, $D_{30}$: `7.56%`, $D_{90}$: `5.61%`, reflecting the `2026-11-20` pre-Task-24 `11,420,305`-unit panel).
- **Alternatives Considered:**
  - Continuing with single-year dataset (rejected: omits half the training observations and holiday seasons).
  - Forecasting demand for "Bank Charges" and "Postage" as physical inventory (rejected: violates physical store logic).
- **Impact on Other Modules:** `HistoricalDataService` indexes all `2,287,495` rows / `4,905` SKUs across `739` inclusive calendar dates (`2009-12-01` to `2011-12-09`) for automatic lag/rolling feature extraction in both production (`/api/v1/forecast/*`) and experimental (`/api/v1/experimental/*`) inference, while Phase 1 `.joblib` models in `backend/ml/models/` retain their original Phase 1 weights (`TD-013`).

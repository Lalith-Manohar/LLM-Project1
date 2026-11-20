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

---

### TD-009: SKU Lifespan Boundary Imputation vs Global Calendar Imputation
- **Date:** 2026-11-16
- **Topic:** Continuous time-series generation, zero-demand imputation, and temporal boundary integrity.
- **Context:** In Phase 1 Task 3, daily retail sales needed to be padded with zero-demand records to support lag feature construction. Products in the UCI dataset were introduced, traded, and phased out at different points between 2009 and 2011.
- **Decision:** Impute continuous calendar days strictly within each individual SKU's observed lifespan boundaries ($[\text{min\_date}, \text{max\_date}]$). Do not impute dates prior to a product's first recorded sale or after its final recorded sale.
- **Reasoning:**
  1. A product cannot have "zero sales" before it exists in the catalog or after it has been permanently discontinued. Pre-launch zero-inflation would artificially bias moving averages downward and distort lag distributions.
  2. Imputing within $[\text{min\_date}, \text{max\_date}]$ accurately captures true intermittent demand during an active product lifecycle (e.g. 74.30% zero-demand days across active lifespans) without introducing artificial calendar leakage.
- **Alternatives Considered:**
  - Global calendar grid imputation across all SKUs from 2010-12-01 to 2011-12-09 (rejected: would inflate the dataset with over 1.4 million synthetic zero rows for products introduced late in 2011, contaminating demand velocity statistics).
  - Dropping days with zero sales (rejected: breaks time-series continuity, invalidating lag shifts $t-k$ and rolling windows).
- **Impact on Other Modules:** `daily_product_demand.csv` contains continuous date ranges per product; Phase 1 Task 4 will compute lags and rolling windows safely on this structured matrix.

---

### TD-010: Incomplete Multi-Horizon Target Handling via NaN Preservation
- **Date:** 2026-11-17
- **Topic:** Forward-looking target generation, incomplete horizon handling, and label leakage prevention.
- **Context:** In Phase 1 Task 4, multi-horizon cumulative targets ($D_7, D_{15}, D_{30}, D_{90}$) were constructed. Each product's series ends at its last observed sale date (`max_date`). For rows within $H$ days of `max_date`, complete future demand is unobserved.
- **Decision:** Strictly mark forward targets as missing (`NaN`) whenever the complete future window of $H$ days is unavailable. Never fill incomplete future windows with zero, partial sums, or forward-filled values.
- **Reasoning:**
  1. An unobserved future period is not evidence of zero consumer demand. Assuming zero sales for future dates beyond the observation window would artificially bias demand predictions downward, causing severe under-forecasting in operational models.
  2. Partial sums over fewer than $H$ days would create target scale distortion (e.g., comparing a 3-day sum to a full 7-day target), degrading regression loss functions.
  3. Preserving `NaN` allows model training in Task 5 to cleanly select valid instances (`df[target].notnull()`) independently for each horizon ($D_7$: 945,345 eligible rows; $D_{90}$: 661,228 eligible rows) without label contamination.
- **Alternatives Considered:**
  - Zero-padding future unobserved days (rejected: creates false zero-sales signals for high-velocity items).
  - Truncating all SKUs to a single arbitrary cut-off date (rejected: needlessly discards hundreds of thousands of valid training rows for shorter horizons like $D_7$ and $D_{15}$).
- **Impact on Other Modules:** Phase 1 Task 5 training scripts will filter non-null target masks independently per horizon model. Model evaluation backtests will strictly test against verified complete horizons.

---

### TD-011: Strict Chronological Purge/Embargo Window Splitting
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
- **Impact on Other Modules:** All future backtesting and evaluation modules (Module 2, 7, 10) must use `get_chronological_split()` or adhere to the purge/embargo rule.

---

### TD-012: Continuous TargetEncoder for High-Cardinality Retail Product SKUs
- **Date:** 2026-11-17
- **Topic:** Categorical encoding, pipeline architecture, and inference resilience.
- **Context:** The retail catalog contains 3,922 unique alphanumeric product SKUs (`StockCode`). One-hot encoding creates 3,922 sparse/dense columns, which causes memory exhaustion (>8 GB array allocations) and slow training for tree-based estimators like Random Forest over 800,000+ samples. Label/ordinal encoding artificially imposes ordinal arithmetic relationships on discrete products.
- **Decision:** Implement scikit-learn's `TargetEncoder(smooth="auto", cv=KFold(5, shuffle=False), target_type="continuous")` coupled with `StandardScaler` inside a unified `Pipeline`.
- **Reasoning:**
  1. Compresses high-cardinality SKUs into a single informative continuous feature representing empirical target demand conditioned on SKU, with out-of-fold cross-validation and Bayes smoothing to prevent target leakage.
  2. Ensures that unseen product SKUs at inference time automatically impute the global prior mean target without throwing exceptions or failing requests.
  3. Keeps preprocessing entirely self-contained inside the `.joblib` serialized pipeline, ensuring identical transformations during offline evaluation and live FastAPI serving.
- **Alternatives Considered:**
  - High-cardinality OneHotEncoder (rejected: causes memory exhaustion and excessive artifact size).
  - OrdinalEncoder (rejected: imposes arbitrary numerical distances between unrelated products).
- **Impact on Other Modules:** Superseded by TD-013 following the Phase 1 Task 5.1 Temporal Leakage Audit.

---

### TD-013: OneHotEncoder Infrequent Categorical Encoding vs TargetEncoder Temporal Leakage
- **Date:** 2026-11-17
- **Topic:** Temporal target leakage elimination in high-cardinality SKU encoding.
- **Context:** During the Phase 1 Task 5.1 technical audit, `TargetEncoder(smooth="auto", cv=KFold(5, shuffle=False))` was inspected for temporal leakage. Because `KFold` is non-temporal, target values from future dates (e.g., in fold 4) were used to compute SKU target encodings for earlier training observations (e.g., in folds 0-3). This introduced subtle internal cross-fitting target leakage into the training phase.
- **Decision:** Replace `TargetEncoder` with `OneHotEncoder(max_categories=50, handle_unknown="infrequent_if_exist", sparse_output=False)`. Top 50 frequent high-volume SKUs receive individual binary indicator columns; all remaining 3,872 SKUs (and unseen SKUs at inference) automatically collapse into a single `infrequent_SKU` category.
- **Reasoning:**
  1. **Zero Target Leakage:** `OneHotEncoder` is purely unsupervised; it maps category identifiers without ever reading target labels $y$. Future target values cannot leak into earlier feature representations.
  2. **Bounded Dimensionality:** Constraining `max_categories=50` adds exactly 51 columns (top 50 + 1 infrequent) regardless of total catalog size, preventing memory bloat and keeping Random Forest training within 20 seconds.
  3. **Robust Unseen SKU Handling:** `handle_unknown="infrequent_if_exist"` ensures any unseen SKU encountered during inference smoothly activates the infrequent indicator without raising an error.
  4. **Empirical Performance:** Ridge linear regression achieved 55.65% WAPE on $D_7$, and Random Forest achieved 50.00% on $D_{15}$, 48.73% on $D_{30}$, and 53.22% on $D_{90}$—all beating the Seasonal Naïve baseline without target leakage.
- **Alternatives Considered:**
  - Rolling target encoding (rejected: highly complex to maintain across sparse time series without lookahead risk).
  - Raw OrdinalEncoder (rejected: creates false numeric hierarchy among SKUs).
- **Impact on Other Modules:** Serialized pipelines in `backend/ml/models/` accept raw DataFrame inputs with string `StockCode` and output calibrated predictions directly. Preprocessing is 100% self-contained in the pipeline.

---

### TD-014: FastAPI Multi-Horizon Prediction Service & Lifespan Architecture
- **Date:** 2026-11-17
- **Topic:** ML model serving, lifespan memory management, and multi-horizon inference API.
- **Context:** Phase 1 Task 6 requires integrating the four trained multi-horizon model artifacts (`demand_model_{7,15,30,90}d.joblib`) into FastAPI. Key challenges: loading serialized models repeatedly on every HTTP request introduces massive disk I/O and latency spikes; Pydantic request models had legacy schema drift (`horizon_days: int` vs `horizons: List[int]`); and feature requirements must match the exact 10-column contract fitted during training.
- **Decision:**
  1. Implement a centralized singleton `PredictionService` initialized once at application startup using FastAPI's modern async `lifespan` event handler. Models and `models_metadata.json` remain resident in memory for instantaneous sub-millisecond inference.
  2. Implement flexible schema validation in `ForecastRequest` supporting both modern multi-horizon queries (`horizons: [7, 15, 30, 90]`) and legacy backward-compatible queries (`horizon_days: int`), with support for either nested `features: HistoricalFeatures` or flat historical attributes.
  3. Format incoming feature payloads into a strictly typed pandas DataFrame with exact column ordering matching the trained pipelines: `['StockCode', 'DayOfWeek', 'Month', 'DayOfMonth', 'Lag1', 'Lag7', 'Lag14', 'Lag28', 'RollingMean7', 'RollingMean28']`.
  4. Enforce non-negativity post-processing $\max(0, \hat{y})$ and non-finite sanitization on all raw model outputs.
  5. Check if requested `StockCode` is among known training categories; if not, log an informational warning while cleanly relying on `OneHotEncoder(handle_unknown="infrequent_if_exist")` to serve robust predictions for unseen/infrequent SKUs.
- **Reasoning:**
  - Prevents request-time disk I/O and ensures thread-safe, read-only inference.
  - Resolves `ISSUE-001` cleanly while providing zero breaking changes to existing client contracts.
  - Guarantees strict compliance with the Phase 1 zero-leakage pipeline contracts.
- **Alternatives Considered:**
  - On-demand lazy model loading (rejected: introduces latency jitter on first request and potential race conditions).
  - Training inside the API request cycle (rejected: strictly prohibited by `AGENTS.md`).
- **Impact on Other Modules:** Module 7 (Predictive Planner) and Module 8 (Purchase Planning Simulator) can query `/api/v1/forecast/` for multi-horizon demand forecasts. Operational inventory risk calculations can reliably consume the API output.

---

### TD-015: Dual-Hierarchical Retail Forecasting (Store-Wide Macro vs SKU-Level Micro)
- **Date:** 2026-11-20
- **Topic:** Forecasting hierarchy distinction and empirical WAPE disparity resolution.
- **Context:** During model benchmarking on `uni_api_experimental`, external student claims of ~10% WAPE on the UCI Online Retail II dataset were audited against NEXORA's ~50% SKU-level WAPE.
- **Decision:** Implement and formalize a dual-tier forecasting architecture distinguishing:
  1. **Tier 1 — Store-Wide (Macro) Demand:** Aggregated daily volume across all 3,922 SKUs. Cancels out intermittent Poisson noise and achieves **8.87% to 13.38% WAPE** across $D_7, D_{15}, D_{30}$.
  2. **Tier 2 — SKU-Level (Micro) Demand:** Disaggregated demand per individual SKU for inventory replenishment and stockout prevention, where intermittent sparsity dictates a higher theoretical variance floor (~45%–55% WAPE).
- **Reasoning:** Proves mathematically and empirically that external ~10% WAPE claims correspond to macro store total forecasting, not intermittent SKU forecasting. Exposes both tiers transparently via `/api/v1/forecast/evaluation-comparison` and `/api/v1/forecast/store-wide`.
- **Alternatives Considered:**
  - Claiming 10% WAPE on SKU-level by using random train/test splits (rejected: violates chronological causality and causes catastrophic data leakage).
  - Ignoring the external discrepancy (rejected: leaves students vulnerable during project viva defense).
- **Impact on Other Modules:** Executives can monitor store-wide macro revenue and inventory turnover; warehouse managers utilize SKU-level predictions for bin restocking.

---

### TD-016: Baseline-Anchored Residual Regressor Formulation for Multi-Horizon Demand
- **Date:** 2026-11-20
- **Topic:** Multi-horizon demand model architecture and tree-underfitting resolution.
- **Context:** Direct regression on multi-horizon cumulative sums ($D_{15}, D_{30}, D_{90}$) suffered from severe negative prediction bias (-25.14% on $D_{90}$) due to decision tree saturation in shallow Random Forests.
- **Decision:** Formulate forecasting as a baseline-anchored residual decomposition:
  $$\hat{y} = h \cdot \text{RollingMean} + \hat{r}$$
  Implemented via `ResidualRegressor`, where the physical moving-average run-rate anchors the forecast, and regularized estimators (`Ridge`) model the residual deviation $\hat{r}$.
- **Reasoning:**
  1. Guarantees physical scale consistency across changing operational windows.
  2. Reduces WAPE from 50.00% to **46.34% on $D_{15}$** (+3.66 pp) and from 48.73% to **45.37% on $D_{30}$** (+3.36 pp).
  3. Seamlessly integrates with scikit-learn Pipelines and Joblib serialization.
- **Alternatives Considered:**
  - Training deeper random forests with 500+ trees (rejected: slow training, memory bloat, and persistent bias during seasonal regime shifts).
  - Pure moving average without residual adjustments (rejected: misses short-term momentum and price elasticity).
- **Impact on Other Modules:** Serialized in `backend/ml/models_experimental/` for Phase 2 operational CRUD and predictive purchasing.

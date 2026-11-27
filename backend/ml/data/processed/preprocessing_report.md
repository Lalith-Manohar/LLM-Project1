# NEXORA — Preprocessing & Transaction Stream Isolation Report
**Generated Date:** 2026-11-20 23:51:35  
**Module:** Phase 1, Task 2 — Transaction Stream Partitioning & Reconciliation

---

## 1. Executive Summary & Full Reconciliation

Every record in the raw dataset was evaluated against four mutually exclusive and collectively exhaustive criteria.

| Metric | Record Count | % of Original Dataset | Validation Status |
| :--- | :---: | :---: | :---: |
| **Total Original Records** | **1,067,371** | **100.00%** | Baseline |
| **1. Clean Gross Sales Demand** | **1,041,670** | **97.59%** | Validated (`Qty > 0`, `Price > 0`, no `'C'`) |
| **2. Cancellation Transactions** | **19,494** | **1.83%** | Validated (Invoice starts with `'C'`) |
| **3. Return / Credit Transactions** | **3,457** | **0.32%** | Validated (`Qty < 0`, no `'C'`) |
| **4. Exceptional / Excluded Records** | **2,750** | **0.26%** | Validated (Price $\le 0$, non-sales) |
| **Total Partitioned Records** | **1,067,371** | **100.00%** | **Reconciliation: MATCHED (0 Records Lost)** |

---

## 2. Stream Profiles and Characteristics

### Stream 1: Clean Gross Sales Demand (`clean_gross_sales.csv`)
- **Purpose:** Primary training dataset for multi-horizon machine learning demand forecasting (Task 3 & 4).
- **Selection Criteria:** `Quantity > 0`, `Price > 0`, and `Invoice` does not begin with `'C'`.
- **Total Rows:** 1,041,670 rows (97.59% of raw transactions).
- **Quantity Range:** Min 1, Median 3.0, Max 80,995 units.
- **Price Range:** Min £0.00, Median £2.10, Max £25111.09.
- **Exact Duplicate Rows:** 33,757 rows (3.24%). Duplicate records are preserved per NEXORA integrity rules to represent legitimate multi-item purchases unless explicit deduplication is approved.

### Stream 2: Cancellation Transactions (`cancellation_transactions.csv`)
- **Purpose:** Fed into Module 9 (Product Health) and Module 10 (Anomaly Detection) to track cancellation frequencies.
- **Selection Criteria:** `Invoice` begins with `'C'`.
- **Total Rows:** 19,494 rows (1.83% of raw transactions).
- **Integrity Validation:** 100% of these records (19,494) have negative quantities (`Quantity < 0`).
- **Quantity Range:** Min -80,995, Max 1.
- **Price Range:** Min £0.01, Max £38970.00.

### Stream 3: Return & Credit Adjustments without 'C' (`return_transactions.csv`)
- **Purpose:** Tracked separately in inventory movement logs and product health intelligence.
- **Selection Criteria:** `Quantity < 0` and `Invoice` does not begin with `'C'`.
- **Total Rows:** 3,457 rows (0.32% of raw transactions).
- **Inspection Detail:** In the UCI dataset, all 3,457 of these records have `Price == 0.0`. Their descriptions include administrative tags such as `damages`, `check`, `lost`, `wet damaged`, and `thrown away`.

### Stream 4: Exceptional & Excluded Records (`exceptional_transactions.csv`)
- **Purpose:** Audit ledger of non-commercial or administrative adjustments. Excluded from demand forecasting.
- **Selection Criteria:** Records with `Price <= 0` that are neither 'C' cancellations nor negative returns.
- **Total Rows:** 2,750 rows (0.26% of raw transactions).
- **Breakdown:**
  - 1,179 records with `Quantity > 0` and `Price == 0.0` (sample distributions, customer appreciation giveaways, or zero-price administrative entries with descriptions like `Found`, `check`, `amazon`).
  - 2 records with negative prices (`Price == -11062.06`, accounting adjustments titled `Adjust bad debt`).

---

## 3. Missing Value Breakdown Across Streams

| Column | Raw Dataset | Gross Sales | Cancellations | Returns | Exceptional |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `Invoice` | 0 | 0 | 0 | 0 | 0 |
| `StockCode` | 0 | 0 | 0 | 0 | 0 |
| `Description` | 4,382 | 0 | 0 | 2,689 | 1,693 |
| `Quantity` | 0 | 0 | 0 | 0 | 0 |
| `InvoiceDate` | 0 | 0 | 0 | 0 | 0 |
| `Price` | 0 | 0 | 0 | 0 | 0 |
| `Customer ID` | 243,007 | 236,121 | 750 | 3,457 | 2,679 |
| `Country` | 0 | 0 | 0 | 0 | 0 |

---

## 4. Downstream Pipeline Implications

1. **No Data Loss:** The sum of partitioned files exactly equals 541,910 rows. Zero rows were silently dropped or ignored.
2. **Gross Sales Cleanliness:** `clean_gross_sales.csv` contains solely positive purchase quantities (1,041,670 records) across commercial transactions, providing an unpolluted foundation for daily demand aggregation in Task 3.
3. **Preservation of Raw Truth:** All negative quantities, damages, and cancellations are preserved in dedicated CSV files for Module 9 (Product Health) and Module 10 (Anomaly Detection).

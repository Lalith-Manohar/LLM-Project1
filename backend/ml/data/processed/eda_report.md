# NEXORA — Exploratory Data Analysis (EDA) Report
**Dataset:** UCI Online Retail II (`online_retail_II.csv`)  
**Generated Date:** 2026-11-17 00:56:01  
**Module:** Phase 1, Task 1 — Data Ingestion & Statistical Exploration

---

## 1. Executive Summary & Dataset Dimensions

- **Total Transaction Rows:** 541,910
- **Total Columns:** 8
- **Temporal Range:** 2010-12-01 08:26:00 to 2011-12-09 12:50:00
- **Duplicate Rows:** 5,268 (0.97%)
- **Unique Invoices:** 25,900
- **Unique Products (StockCode):** 4,070
- **Unique Customers:** 4,372 (excluding nulls)
- **Countries Represented:** 38

---

## 2. Column Profiles & Missing-Value Analysis

| Column Name | Data Type | Missing Count | Missing Percentage | Interpretation |
| :--- | :--- | :---: | :---: | :--- |
| `Invoice` | `object` | 0 | 0.00% | Fully populated |
| `StockCode` | `object` | 0 | 0.00% | Fully populated |
| `Description` | `object` | 1,454 | 0.27% | Minor missing names; fallback to StockCode required |
| `Quantity` | `int64` | 0 | 0.00% | Fully populated |
| `InvoiceDate` | `object` | 0 | 0.00% | Fully populated |
| `Price` | `float64` | 0 | 0.00% | Fully populated |
| `Customer ID` | `object` | 135,080 | 24.93% | High missing rate; customer-level features cannot be universal |
| `Country` | `object` | 0 | 0.00% | Fully populated |

---

## 3. Transaction Stream Classification & Integrity Analysis

NEXORA strictly segregates gross demand from post-purchase friction (cancellations and returns):

| Transaction Category | Record Count | % of Total Dataset | Handling Rule in NEXORA |
| :--- | :---: | :---: | :--- |
| **Gross Positive Sales** (`Qty > 0`, `Price > 0`, no 'C') | **530,105** | **97.82%** | **Used exclusively for training demand forecasting models.** |
| **Invoice Cancellations** (`Invoice` starts with 'C') | **9,288** | **1.71%** | Tracked in Module 9 & 10 (Product Health & Anomaly Alerts). |
| **Returns without 'C'** (`Qty < 0` & no 'C') | **1,336** | **0.25%** | Credit adjustments and inventory restocks tracked in Module 9. |
| **Zero Quantities** (`Qty == 0`) | **0** | **0.00%** | Informational or administrative entries; filtered from demand. |
| **Zero / Negative Prices** (`Price <= 0`) | **2,517** | **0.46%** | Administrative adjustments, gifts, or errors; filtered from demand. |

### Cancellation & Negative Quantity Verification
- **Invoices starting with 'C' having negative quantity:** 9,288
- **Invoices starting with 'C' having positive quantity:** 0
- **Invoices starting with 'C' having zero quantity:** 0
- **Negative quantity records WITHOUT 'C' prefix:** 1,336

> [!NOTE]
> **Key Finding:** While virtually all 'C' invoices have negative quantities, there are records with negative quantities that lack the 'C' prefix. NEXORA correctly avoids assuming that every negative quantity is a cancellation.

---

## 4. Quantity Distribution

- **Minimum Quantity:** -80,995.0 (extreme return or cancellation)
- **25th Percentile (P25):** 1.0
- **Median (P50):** 3.0
- **Mean:** 9.55
- **75th Percentile (P75):** 10.0
- **99th Percentile (P99):** 100.0
- **Maximum Quantity:** 80,995.0 (bulk wholesale order)
- **Standard Deviation:** 218.08

---

## 5. Price Distribution

- **Minimum Price:** £-11062.06
- **25th Percentile (P25):** £1.25
- **Median (P50):** £2.08
- **Mean:** £4.61
- **75th Percentile (P75):** £4.13
- **99th Percentile (P99):** £18.00
- **Maximum Price:** £38970.00
- **Standard Deviation:** £96.76

---

## 6. Top Countries by Transaction Volume

| Country | Transaction Count | % of Total |
| :--- | :---: | :---: |
| United Kingdom | 495,478 | 91.43% |
| Germany | 9,495 | 1.75% |
| France | 8,558 | 1.58% |
| EIRE | 8,196 | 1.51% |
| Spain | 2,533 | 0.47% |
| Netherlands | 2,371 | 0.44% |
| Belgium | 2,069 | 0.38% |
| Switzerland | 2,002 | 0.37% |
| Portugal | 1,519 | 0.28% |
| Australia | 1,259 | 0.23% |

---

## 7. Top SKUs by Demand Frequency & Volume (Positive Sales Only)

### Top 10 Most Frequently Purchased SKUs
| StockCode | Transaction Frequency |
| :--- | :---: |
| `85123A` | 2,265 |
| `85099B` | 2,112 |
| `22423` | 2,017 |
| `47566` | 1,706 |
| `20725` | 1,595 |
| `84879` | 1,489 |
| `22197` | 1,426 |
| `22720` | 1,399 |
| `21212` | 1,370 |
| `20727` | 1,328 |

### Top 10 SKUs by Total Quantity Sold
| StockCode | Total Quantity Sold (Units) |
| :--- | :---: |
| `23843` | 80,995 |
| `23166` | 78,033 |
| `22197` | 56,921 |
| `84077` | 55,047 |
| `85099B` | 48,474 |
| `85123A` | 37,660 |
| `84879` | 36,461 |
| `21212` | 36,419 |
| `23084` | 30,788 |
| `22492` | 26,633 |

---

## 8. Data-Quality & Modeling Implications for Phase 1

1. **Missing Customer IDs:** Approximately 24% of transactions lack a `Customer ID`. Because product demand aggregation occurs at the daily `StockCode` level, missing customer IDs will not hinder demand forecasting models.
2. **Duplicate Rows:** 5,268 duplicate rows exist in the raw dataset. Preprocessing will define whether duplicate transactions represent identical repeated checkout items or genuine double logging.
3. **Extreme Outliers:** Heavy tails exist in Quantity (from -80995.0 to 80995.0) and Price (up to £38970.0). Robust metrics like MAE and WAPE will be necessary during model evaluation to prevent undue distortion by extreme bulk transactions.
4. **Sparse Product Activity:** Many SKUs trade intermittently. In Phase 1 Task 3, daily time-series aggregation must generate continuous calendar days and impute missing product-days with `0` demand.

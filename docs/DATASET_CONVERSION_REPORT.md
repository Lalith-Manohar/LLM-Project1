# NEXORA — Original Dataset Recovery & Full 2-Year Conversion Report

**Project:** NEXORA – AI-Powered Retail Management & Intelligence System  
**Working Branch:** `uni_api_experimental`  
**Protected Branch:** `uni_api_submission` (Untouched at `596430fc6c53dd526b48b9d25d666611d71938a1`)  
**Audit & Conversion Date:** 20 November 2026  
**Status:** Completed & Empirically Verified (100% Zero-Loss Reconciliation)

---

## 1. Executive Summary

During the Task 9 audit, an inspection of `backend/ml/data/raw/online_retail_II.csv` revealed that it contained **541,910 records** covering only the single calendar year **2010–2011** (1 December 2010 to 9 December 2011). The original UCI Online Retail II dataset spans two complete years (2009–2011) with over 1 million transactions.

Investigation confirmed that the original dataset was provided as an Excel workbook (`online_retail_II.xlsx`, 45,622,278 bytes) containing two separate worksheets:
1. `Year 2009-2010` (525,461 records)
2. `Year 2010-2011` (541,910 records)

When the initial conversion to CSV was performed in earlier phases, the conversion tool or script defaulted to reading only the active/second worksheet (`Year 2010-2011`), discarding the entire first year (525,461 records, 49.23% of the dataset).

### Resolution
A dedicated, fully reproducible conversion pipeline (`backend/ml/src/convert_xlsx_to_csv.py`) was created to parse both worksheets, standardize date formats into unambiguous ISO format (`YYYY-MM-DD HH:MM:SS`), concatenate all records, preserve the original 1-year backup (`online_retail_II_2010_2011_backup.csv`), and generate the unified 2-year raw dataset (`online_retail_II.csv`) totaling **1,067,371 records**.

---

## 2. Worksheet Profiling & Root-Cause Diagnosis

### 2.1 Excel Workbook Inspection (`online_retail_II.xlsx`)
- **File Path:** `backend/ml/data/raw/online_retail_II.xlsx`
- **File Size:** 45,622,278 bytes (~43.5 MB)
- **Worksheet Count:** 2 sheets
- **Engine Used:** `openpyxl` via `pandas.read_excel()`

| Worksheet Index | Sheet Name | Row Count | Column Count | Date Range (Min $\rightarrow$ Max) |
| :--- | :--- | :---: | :---: | :--- |
| **Sheet 1** | `Year 2009-2010` | 525,461 | 8 | 2009-12-01 07:45:00 $\rightarrow$ 2010-12-09 20:01:00 |
| **Sheet 2** | `Year 2010-2011` | 541,910 | 8 | 2010-12-01 08:26:00 $\rightarrow$ 2011-12-09 12:50:00 |
| **Total (Sum)** | — | **1,067,371** | **8** | **2009-12-01 07:45:00 $\rightarrow$ 2011-12-09 12:50:00** |

### 2.2 Root-Cause Diagnosis
In Python's `pandas.read_excel(path)`, the default parameter for `sheet_name` is `0` (or whichever sheet was saved as active in the Excel UI). When exported without `sheet_name=None`, only one worksheet is extracted. Sheet 2 (`Year 2010-2011`) was the active worksheet when the file was saved, leading the previous export to produce exactly 541,910 rows.

Furthermore, date formatting in Sheet 1 and Sheet 2 had varied day/month orderings in Excel (`%d-%m-%y` vs `%Y-%m-%d`), which previously caused UK date inversion if parsed ambiguously.

---

## 3. Conversion Methodology & Zero-Loss Verification

The conversion script `backend/ml/src/convert_xlsx_to_csv.py` enforced the following safeguards:

1. **Explicit Multi-Sheet Ingestion:** Reads `Year 2009-2010` and `Year 2010-2011` independently using `openpyxl`.
2. **Date Normalization:** Every timestamp in `InvoiceDate` is coerced to standard datetime and serialized as unambiguous ISO `YYYY-MM-DD HH:MM:SS`.
3. **Column Order Uniformity:** Strictly enforces the canonical 8 columns: `['Invoice', 'StockCode', 'Description', 'Quantity', 'InvoiceDate', 'Price', 'Customer ID', 'Country']`.
4. **Preservation of Overlap:** A 9-day overlap window exists between 1 December 2010 and 9 December 2010 across both sheets. Per NEXORA dataset specifications, all transactional records are preserved without arbitrary deduping at the raw stage.
5. **Atomic Swap & Backup:**
   - The original 541,910-row CSV was preserved at `backend/ml/data/raw/online_retail_II_2010_2011_backup.csv` (45,005,779 bytes).
   - The unified dataset was staged to temporary storage, verified for exact row count and schema, and then moved to `backend/ml/data/raw/online_retail_II.csv` (94,268,769 bytes).

---

## 4. Reconciled Data Integrity Matrix

| Metric | Sheet 1 (`2009-2010`) | Sheet 2 (`2010-2011`) | Unified 2-Year Raw CSV | Reconciliation Status |
| :--- | :---: | :---: | :---: | :---: |
| **Row Count** | 525,461 | 541,910 | **1,067,371** | **EXACT MATCH ($525,461 + 541,910$)** |
| **File Size on Disk** | — | 45,005,779 bytes | **94,268,769 bytes** | Verified |
| **Unique Invoices** | 28,816 | 25,900 | **53,628** | Verified (1,088 invoices span boundary) |
| **Unique StockCodes** | 4,683 | 4,070 | **5,305** | Verified (+1,235 additional SKUs) |
| **Unique Customer IDs** | 4,383 | 4,372 | **5,942** | Verified (+1,570 additional customers) |
| **Unique Countries** | 40 | 38 | **43** | Verified |
| **Unique Calendar Dates** | 307 | 305 | **604** | Verified (from 305 to 604 transaction dates) |
| **Earliest Timestamp** | 2009-12-01 07:45:00 | 2010-12-01 08:26:00 | **2009-12-01 07:45:00** | Verified |
| **Latest Timestamp** | 2010-12-09 20:01:00 | 2011-12-09 12:50:00 | **2011-12-09 12:50:00** | Verified |

### Missing Values Profile (Unified Dataset)
- `Invoice`: 0 nulls (0.00%)
- `StockCode`: 0 nulls (0.00%)
- `Description`: 4,382 nulls (0.41%)
- `Quantity`: 0 nulls (0.00%)
- `InvoiceDate`: 0 nulls (0.00%)
- `Price`: 0 nulls (0.00%)
- `Customer ID`: 243,007 nulls (22.77% — guest checkout transactions)
- `Country`: 0 nulls (0.00%)

---

## 5. Downstream Pipeline Implications

1. **Expansion of Time Series Horizon:**
   - Previous single-year dataset: 373 total calendar days (December 2010 to December 2011).
   - Unified 2-year dataset: **738 total calendar days** (December 2009 to December 2011).
2. **Resolution of $D_{90}$ Time-Series Split Bottleneck:**
   - In Task 8 and Task 9, $D_{90}$ 3-fold rolling cross-validation suffered from a narrow 125-date training window with 91-day embargoes, forcing 7-day validation windows.
   - With 738 calendar days, training windows expand to $\ge 400$ days, permitting realistic 90-day out-of-time evaluation windows without embargo constriction.
3. **Zero Records Lost:**
   - Every single transaction recorded in the raw UCI Excel workbook is accounted for in `online_retail_II.csv`.

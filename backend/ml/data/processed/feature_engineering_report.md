# NEXORA — Feature Engineering & Multi-Horizon Demand Targets Report
**Generated Date:** 2026-11-17 00:03:57  
**Module:** Phase 1, Task 4 — Leakage-Free Feature Generation & Multi-Horizon Targets ($D_7, D_{15}, D_{30}, D_{90}$)

---

## 1. Executive Summary

The feature engineering pipeline converted the continuous daily time-series (`daily_product_demand.csv`) into a leakage-free, multi-horizon analytical dataset (`ml_feature_dataset.csv`).

| Metric | Measured Value | Notes |
| :--- | :---: | :--- |
| **Total Rows Processed** | 1,074,653 | 100% row preservation from Task 3 continuous series |
| **Unique Product SKUs** | 3,922 | Preserved as clean strings |
| **Total Features & Targets Generated** | 18 columns | Calendar (3), Lags (4), Rolling (2), Targets (4) |
| **Validation & Leakage Status** | **PASSED (Leakage-Free)** | Strict temporal isolation enforced |
| **Complete Feature Rows (All Lags + Rolling)** | 970,840 (90.34%) | Rows ready for model training |

---

## 2. Historical Feature Availability & Missing Values

Initial lag and rolling features naturally contain missing values (`NaN`) during the initial burn-in window of each SKU's lifespan. Per NEXORA architecture (`AGENTS.md`), these missing values are strictly preserved and never filled with future information or synthetic zeros.

| Feature Name | Feature Type | Time Window | Available Rows | Available % | Missing Rows (`NaN`) | Missing % | Primary Cause of Missing Values |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `Lag1` | Historical Demand | $t - k$ | 1,070,731 | 99.64% | 3,922 | 0.36% | Row 0 of each SKU (no $t-1$ history) |
| `Lag7` | Historical Demand | $t - k$ | 1,048,251 | 97.54% | 26,402 | 2.46% | First 7 days of each SKU lifespan |
| `Lag14` | Historical Demand | $t - k$ | 1,022,205 | 95.12% | 52,448 | 4.88% | First 14 days of each SKU lifespan |
| `Lag28` | Historical Demand | $t - k$ | 970,840 | 90.34% | 103,813 | 9.66% | First 28 days of each SKU lifespan |
| `RollingMean7` | Historical Demand | $t - k$ | 1,048,251 | 97.54% | 26,402 | 2.46% | First 7 days of each SKU lifespan |
| `RollingMean28` | Historical Demand | $t - k$ | 970,840 | 90.34% | 103,813 | 9.66% | First 28 days of each SKU lifespan |

---

## 3. Multi-Horizon Future Demand Target Availability

Target variables represent cumulative future customer demand over horizon $H$:

$$D_H(t) = \sum_{i=1}^{H} \text{daily\_demand}_{t+i}$$

### Critical Incomplete-Target Rule
For observations near the end of each product's observed trading lifespan, complete future target windows of $H$ days are unavailable. NEXORA strictly marks these targets as **missing (`NaN`)** rather than treating them as zero sales.

| Horizon Target | Forecast Window | Operational Purpose | Available Targets | Available % | Incomplete Targets (`NaN`) | Incomplete % | Eligible Rows for Training (Features + Target) | Eligible % |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `D_7` | $t+1$ to $t+7$ | Fast shelf restocking | 1,048,251 | 97.54% | 26,402 | 2.46% | 945,345 | 87.97% |
| `D_15` | $t+1$ to $t+15$ | Bi-weekly ordering | 1,018,506 | 94.78% | 56,147 | 5.22% | 916,376 | 85.27% |
| `D_30` | $t+1$ to $t+30$ | Monthly inventory budgeting | 963,538 | 89.66% | 111,115 | 10.34% | 862,938 | 80.30% |
| `D_90` | $t+1$ to $t+90$ | Quarterly vendor quotas | 753,054 | 70.07% | 321,599 | 29.93% | 661,228 | 61.53% |

---

## 4. Leakage Prevention & Temporal Integrity Architecture

To prevent optimistic bias and guarantee valid out-of-time generalizability:
1. **Calendar Features (`DayOfWeek`, `Month`, `DayOfMonth`):** Calculated strictly on date $t$.
2. **Lag Features (`Lag1`, `Lag7`, `Lag14`, `Lag28`):** Shifted $t - k$. Never references date $t$ or future dates.
3. **Rolling Window Features (`RollingMean7`, `RollingMean28`):** Pre-shifted by 1 day before rolling average calculation. Dates $t-7$ to $t-1$ and $t-28$ to $t-1$ are used; current date $t$ is strictly excluded.
4. **Future Target Variables ($D_7, D_{15}, D_{30}, D_{90}$):** Forward-looking rolling sums strictly spanning $t+1$ through $t+H$. Date $t$ is strictly excluded from target sums.
5. **Separation of Roles:** No target column is ever utilized as an input feature during feature creation or subsequent model training.

---

## 5. Dataset Profile & Historical Limitations

- **Dataset Historical Span:** Transactions span from December 2010 to December 2011.
- **Retail Realism Limitation:** The dataset reflects historical UK e-commerce behavior and does not represent live current retail demand.
- **Intermittency Profile:** Inactive calendar days within each SKU's active trading window represent true zero demand; however, dates beyond December 2011 are unobserved, which is why future targets near the end of the dataset are marked missing (`NaN`).

---

## 6. Next Steps for Phase 1, Task 5 (Model Training)

With `ml_feature_dataset.csv` generated and validated:
1. **Model Candidates:** Train Seasonal Naïve baseline, Linear Regression, and Random Forest Regressor models independently for each horizon ($D_7, D_{15}, D_{30}, D_{90}$).
2. **Chronological Splitting:** Filter rows where `~isnull()` for all input features and the specific target horizon, and apply rolling-origin or strict chronological train/test splits.
3. **Evaluation Metrics:** Measure MAE, RMSE, and WAPE out-of-time.

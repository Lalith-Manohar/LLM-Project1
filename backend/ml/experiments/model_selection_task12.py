"""NEXORA Task 12: Comprehensive ML Model Selection & Hyperparameter Optimization.

Executes rigorous expanding-window chronological cross-validation across all 4 operational
horizons (D_7, D_15, D_30, D_90) on the recovered 2-year Online Retail II dataset.

Model Families Evaluated:
1. Moving Average Baselines: MA7, MA14, MA28, MA60
2. Linear Models: OLS, Ridge, Lasso, ElasticNet
3. Polynomial Regression: Degree 2 and Degree 3 + Ridge
4. Random Forest: 50, 100, 150, 200 trees; depths: 5, 10, 15, 20, None
5. Extra Trees: 100, 200 trees; depths: 10, 20, None
6. Gradient Boosting: HistGradientBoostingRegressor (varied lr, max_iter, max_leaf_nodes)
7. Residual-Based Models: Baseline Anchor (MA28/MA60) + Residual Regressor

Enforces strict chronological fold boundaries, horizon embargoes, point-in-time pricing,
and chronological target encoding. Final holdouts remain untouched during model selection.
"""

import sys
import os
import json
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import numpy as np
import pandas as pd

from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib

# Ensure backend root is on Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from ml.src.evaluate import calculate_wape, calculate_mae, calculate_rmse
from ml.src.chronological_encoder import ChronologicalTargetEncoder
from ml.src.residual_model import ResidualRegressor
from ml.src.point_in_time_price import enrich_daily_with_pit_price
from ml.src.time_series_split import DateGroupedTimeSeriesSplit

# Non-merchandise service/administrative codes to isolate from inventory demand
NON_MERCHANDISE_CODES = {
    "POST", "DOT", "M", "BANK CHARGES", "PADS", "AMAZONFEE",
    "D", "CRUK", "ADJUST", "TEST001", "C2"
}

EVAL_SPLITS = {
    7: (datetime.date(2011, 11, 15), datetime.date(2011, 12, 2)),
    15: (datetime.date(2011, 11, 1), datetime.date(2011, 11, 24)),
    30: (datetime.date(2011, 10, 1), datetime.date(2011, 11, 9)),
    90: (datetime.date(2011, 8, 1), datetime.date(2011, 9, 10))
}


def load_and_prepare_panel(
    data_dir: Optional[Path] = None
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Loads 2-year daily demand panel, isolates service codes, and computes leakage-free features."""
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent.parent / "data" / "processed"

    daily_path = data_dir / "daily_product_demand.csv"
    sales_path = data_dir / "clean_gross_sales.csv"

    print(f"[Task 12 Data] Loading daily product demand from: {daily_path}...")
    df_daily = pd.read_csv(daily_path, dtype={"StockCode": str}, low_memory=False)
    df_daily["StockCode"] = df_daily["StockCode"].str.strip()
    df_daily["date"] = pd.to_datetime(df_daily["date"]).dt.date

    # Filter out service codes
    is_service = df_daily["StockCode"].str.strip().str.upper().isin(NON_MERCHANDISE_CODES)
    n_service = int(is_service.sum())
    df_daily = df_daily[~is_service].sort_values(["StockCode", "date"]).reset_index(drop=True)
    print(f"[Task 12 Data] Filtered {n_service:,} service rows. Commercial SKUs: {df_daily['StockCode'].nunique():,}, Rows: {len(df_daily):,}")

    # Point-in-time price enrichment
    df_daily, final_prices = enrich_daily_with_pit_price(df_daily, sales_path)

    print("[Task 12 Data] Generating historical lags, rolling statistics, and multi-horizon targets...")
    grouped = df_daily.groupby("StockCode")["daily_demand"]

    df_daily["Lag1"] = grouped.shift(1)
    df_daily["Lag7"] = grouped.shift(7)
    df_daily["Lag14"] = grouped.shift(14)
    df_daily["Lag28"] = grouped.shift(28)
    df_daily["Lag60"] = grouped.shift(60)

    df_daily["RollingMean7"] = grouped.shift(1).rolling(7, min_periods=7).mean().round(4)
    df_daily["RollingMean14"] = grouped.shift(1).rolling(14, min_periods=14).mean().round(4)
    df_daily["RollingMean28"] = grouped.shift(1).rolling(28, min_periods=28).mean().round(4)
    df_daily["RollingMean60"] = grouped.shift(1).rolling(60, min_periods=60).mean().round(4)

    df_daily["RollingStd7"] = grouped.shift(1).rolling(7, min_periods=7).std().round(4).fillna(0.0)
    df_daily["RollingStd28"] = grouped.shift(1).rolling(28, min_periods=28).std().round(4).fillna(0.0)

    is_zero = (df_daily["daily_demand"] == 0).astype(float)
    df_daily["is_zero"] = is_zero
    df_daily["ZeroFraction28"] = df_daily.groupby("StockCode")["is_zero"].shift(1).rolling(28, min_periods=28).mean().round(4).fillna(0.0)
    df_daily["MomentumRatio"] = (df_daily["RollingMean7"] / (df_daily["RollingMean28"] + 1.0)).round(4).fillna(0.0)

    # Coverage restoration for 60-day features
    df_daily["Has60dHistory"] = df_daily["Lag60"].notnull().astype(float)
    df_daily["Lag60"] = df_daily["Lag60"].fillna(df_daily["Lag28"])
    df_daily["RollingMean60"] = df_daily["RollingMean60"].fillna(df_daily["RollingMean28"])

    # Calendar features at date t
    dt_col = pd.to_datetime(df_daily["date"])
    df_daily["DayOfWeek"] = dt_col.dt.dayofweek
    df_daily["Month"] = dt_col.dt.month
    df_daily["DayOfMonth"] = dt_col.dt.day

    # Forward targets
    for h in [7, 15, 30, 90]:
        rev_grouped = df_daily.iloc[::-1].groupby("StockCode")["daily_demand"]
        df_daily[f"D_{h}"] = rev_grouped.shift(1).rolling(h, min_periods=h).sum().iloc[::-1]

    return df_daily, final_prices


def build_candidate_registry(
    horizon: int,
    num_cols: List[str]
) -> List[Dict[str, Any]]:
    """Builds the comprehensive candidate model registry for a specific forecast horizon."""
    h = horizon
    candidates: List[Dict[str, Any]] = []

    # --------------------------------------------------------------------------
    # 1. Moving Average Baselines (Non-trained)
    # --------------------------------------------------------------------------
    candidates.append({
        "family": "Baseline",
        "name": "Baseline_MA7",
        "model_type": "baseline",
        "feature": "RollingMean7",
        "multiplier": float(h),
        "params": {"window": 7, "multiplier": h}
    })
    candidates.append({
        "family": "Baseline",
        "name": "Baseline_MA14",
        "model_type": "baseline",
        "feature": "RollingMean14",
        "multiplier": float(h),
        "params": {"window": 14, "multiplier": h}
    })
    candidates.append({
        "family": "Baseline",
        "name": "Baseline_MA28",
        "model_type": "baseline",
        "feature": "RollingMean28",
        "multiplier": float(h),
        "params": {"window": 28, "multiplier": h}
    })
    candidates.append({
        "family": "Baseline",
        "name": "Baseline_MA60",
        "model_type": "baseline",
        "feature": "RollingMean60",
        "multiplier": float(h),
        "params": {"window": 60, "multiplier": h}
    })

    # Core continuous features for polynomial interactions
    poly_core_cols = [c for c in ["Lag1", "Lag7", "RollingMean7", "RollingMean28", "UnitPrice", "MomentumRatio"] if c in num_cols]
    poly_other_cols = [c for c in num_cols if c not in poly_core_cols]

    def make_preprocessor():
        return ColumnTransformer([
            ("cat", ChronologicalTargetEncoder(horizon=h, smooth=10.0, default_prior=0.0), ["StockCode", "date"]),
            ("num", StandardScaler(), num_cols)
        ])

    def make_poly_preprocessor(degree: int):
        poly_transformer = Pipeline([
            ("scaler", StandardScaler()),
            ("poly", PolynomialFeatures(degree=degree, include_bias=False))
        ])
        return ColumnTransformer([
            ("cat", ChronologicalTargetEncoder(horizon=h, smooth=10.0, default_prior=0.0), ["StockCode", "date"]),
            ("poly_num", poly_transformer, poly_core_cols),
            ("other_num", StandardScaler(), poly_other_cols)
        ])

    # --------------------------------------------------------------------------
    # 2. Linear Regression Family
    # --------------------------------------------------------------------------
    # Ordinary Least Squares
    candidates.append({
        "family": "Linear",
        "name": "Linear_OLS",
        "model_type": "pipeline",
        "estimator": Pipeline([
            ("preprocessor", make_preprocessor()),
            ("regressor", LinearRegression())
        ]),
        "params": {"fit_intercept": True}
    })

    # Ridge Regression (alphas: 0.01, 0.1, 1.0, 10.0, 50.0, 100.0)
    for alpha in [0.01, 0.1, 1.0, 10.0, 50.0, 100.0]:
        candidates.append({
            "family": "Linear",
            "name": f"Ridge_alpha_{alpha}",
            "model_type": "pipeline",
            "estimator": Pipeline([
                ("preprocessor", make_preprocessor()),
                ("regressor", Ridge(alpha=alpha, random_state=42))
            ]),
            "params": {"alpha": alpha}
        })

    # Lasso Regression (alphas: 0.001, 0.01, 0.1, 1.0, 10.0)
    for alpha in [0.001, 0.01, 0.1, 1.0, 10.0]:
        candidates.append({
            "family": "Linear",
            "name": f"Lasso_alpha_{alpha}",
            "model_type": "pipeline",
            "estimator": Pipeline([
                ("preprocessor", make_preprocessor()),
                ("regressor", Lasso(alpha=alpha, max_iter=2000, random_state=42))
            ]),
            "params": {"alpha": alpha}
        })

    # ElasticNet (alphas: 0.001, 0.01, 0.1, 1.0; l1_ratios: 0.2, 0.5, 0.8)
    for alpha in [0.001, 0.01, 0.1, 1.0]:
        for l1_ratio in [0.2, 0.5, 0.8]:
            candidates.append({
                "family": "Linear",
                "name": f"ElasticNet_a_{alpha}_l1_{l1_ratio}",
                "model_type": "pipeline",
                "estimator": Pipeline([
                    ("preprocessor", make_preprocessor()),
                    ("regressor", ElasticNet(alpha=alpha, l1_ratio=l1_ratio, max_iter=2000, random_state=42))
                ]),
                "params": {"alpha": alpha, "l1_ratio": l1_ratio}
            })

    # --------------------------------------------------------------------------
    # 3. Polynomial Regression Family (Degree 2 & 3 with Ridge)
    # --------------------------------------------------------------------------
    for degree in [2, 3]:
        for alpha in [0.1, 1.0, 10.0, 50.0, 100.0]:
            candidates.append({
                "family": "Polynomial",
                "name": f"Poly_deg{degree}_Ridge_a_{alpha}",
                "model_type": "pipeline",
                "estimator": Pipeline([
                    ("preprocessor", make_poly_preprocessor(degree=degree)),
                    ("regressor", Ridge(alpha=alpha, random_state=42))
                ]),
                "params": {"degree": degree, "alpha": alpha}
            })

    # --------------------------------------------------------------------------
    # 4. Random Forest Regression (50, 100, 150, 200 trees)
    # --------------------------------------------------------------------------
    # Test all required tree counts (50, 100, 150, 200) across representative depth & leaf combinations
    rf_configs = [
        # Tree count scaling (depth 10, leaf 5)
        (50, 10, 5, 5),
        (100, 10, 5, 5),
        (150, 10, 5, 5),
        (200, 10, 5, 5),
        # Depth scaling with 100 trees
        (100, 5, 5, 5),
        (100, 15, 2, 5),
        (100, 20, 2, 2),
        (100, None, 1, 2),
        # 200 trees variations (all required tree count)
        (200, 15, 2, 5),
        (200, 20, 5, 10),
        (200, None, 2, 5)
    ]
    for n_est, depth, leaf, split in rf_configs:
        candidates.append({
            "family": "RandomForest",
            "name": f"RF_n{n_est}_d{depth}_leaf{leaf}_split{split}",
            "model_type": "pipeline",
            "estimator": Pipeline([
                ("preprocessor", make_preprocessor()),
                ("regressor", RandomForestRegressor(
                    n_estimators=n_est,
                    max_depth=depth,
                    min_samples_leaf=leaf,
                    min_samples_split=split,
                    n_jobs=-1,
                    random_state=42
                ))
            ]),
            "params": {"n_estimators": n_est, "max_depth": depth, "min_samples_leaf": leaf, "min_samples_split": split}
        })

    # --------------------------------------------------------------------------
    # 5. Extra Trees Regression (100, 200 trees)
    # --------------------------------------------------------------------------
    et_configs = [
        (100, 10, 2),
        (100, 20, 1),
        (200, 10, 5),
        (200, 20, 2),
        (200, None, 2)
    ]
    for n_est, depth, leaf in et_configs:
        candidates.append({
            "family": "ExtraTrees",
            "name": f"ET_n{n_est}_d{depth}_leaf{leaf}",
            "model_type": "pipeline",
            "estimator": Pipeline([
                ("preprocessor", make_preprocessor()),
                ("regressor", ExtraTreesRegressor(
                    n_estimators=n_est,
                    max_depth=depth,
                    min_samples_leaf=leaf,
                    n_jobs=-1,
                    random_state=42
                ))
            ]),
            "params": {"n_estimators": n_est, "max_depth": depth, "min_samples_leaf": leaf}
        })

    # --------------------------------------------------------------------------
    # 6. Gradient Boosting (HistGradientBoostingRegressor)
    # --------------------------------------------------------------------------
    gb_configs = [
        (0.05, 100, 31, 1.0),
        (0.05, 150, 31, 1.0),
        (0.05, 200, 63, 10.0),
        (0.10, 100, 15, 0.0),
        (0.10, 150, 31, 1.0),
        (0.03, 200, 31, 5.0)
    ]
    for lr, max_iter, leaves, l2 in gb_configs:
        candidates.append({
            "family": "GradientBoosting",
            "name": f"HGB_lr{lr}_iter{max_iter}_leaves{leaves}_l2_{l2}",
            "model_type": "pipeline",
            "estimator": Pipeline([
                ("preprocessor", make_preprocessor()),
                ("regressor", HistGradientBoostingRegressor(
                    learning_rate=lr,
                    max_iter=max_iter,
                    max_leaf_nodes=leaves,
                    l2_regularization=l2,
                    random_state=42
                ))
            ]),
            "params": {"learning_rate": lr, "max_iter": max_iter, "max_leaf_nodes": leaves, "l2_regularization": l2}
        })

    # --------------------------------------------------------------------------
    # 7. Residual-Based Models (Baseline Anchor + Residual Estimator)
    # --------------------------------------------------------------------------
    base_feat = "RollingMean28" if h in [7, 15, 30] else "RollingMean60"
    base_mult = float(h)

    # Residual + Ridge (alphas: 10.0, 50.0, 100.0)
    for alpha in [10.0, 50.0, 100.0]:
        inner_pipe = Pipeline([
            ("preprocessor", make_preprocessor()),
            ("regressor", Ridge(alpha=alpha, random_state=42))
        ])
        candidates.append({
            "family": "Residual",
            "name": f"Residual_{base_feat}_Ridge_a_{alpha}",
            "model_type": "residual",
            "estimator": ResidualRegressor(base_feature=base_feat, multiplier=base_mult, estimator=inner_pipe),
            "params": {"base_feature": base_feat, "multiplier": base_mult, "inner_model": "Ridge", "alpha": alpha}
        })

    # Residual + Linear OLS
    inner_ols = Pipeline([
        ("preprocessor", make_preprocessor()),
        ("regressor", LinearRegression())
    ])
    candidates.append({
        "family": "Residual",
        "name": f"Residual_{base_feat}_Linear_OLS",
        "model_type": "residual",
        "estimator": ResidualRegressor(base_feature=base_feat, multiplier=base_mult, estimator=inner_ols),
        "params": {"base_feature": base_feat, "multiplier": base_mult, "inner_model": "LinearRegression"}
    })

    # Residual + HistGradientBoosting
    inner_hgb = Pipeline([
        ("preprocessor", make_preprocessor()),
        ("regressor", HistGradientBoostingRegressor(learning_rate=0.05, max_iter=100, max_leaf_nodes=31, random_state=42))
    ])
    candidates.append({
        "family": "Residual",
        "name": f"Residual_{base_feat}_HGB",
        "model_type": "residual",
        "estimator": ResidualRegressor(base_feature=base_feat, multiplier=base_mult, estimator=inner_hgb),
        "params": {"base_feature": base_feat, "multiplier": base_mult, "inner_model": "HistGradientBoosting"}
    })

    # Pure Moving Average via ResidualRegressor (estimator=None)
    candidates.append({
        "family": "Residual",
        "name": f"Residual_{base_feat}_Pure_Anchor",
        "model_type": "residual",
        "estimator": ResidualRegressor(base_feature=base_feat, multiplier=base_mult, estimator=None),
        "params": {"base_feature": base_feat, "multiplier": base_mult, "inner_model": None}
    })

    return candidates


def run_model_search_for_horizon(
    df_panel: pd.DataFrame,
    horizon: int,
    subsample_limit: int = 50000
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Runs 3-fold chronological cross-validation across all candidates for one horizon."""
    h = horizon
    val_start, val_end = EVAL_SPLITS[h]
    t_col = f"D_{h}"

    num_cols = [
        "DayOfWeek", "Month", "DayOfMonth",
        "Lag1", "Lag7", "Lag14", "Lag28", "Lag60",
        "RollingMean7", "RollingMean14", "RollingMean28", "RollingMean60",
        "RollingStd7", "RollingStd28",
        "ZeroFraction28", "MomentumRatio", "UnitPrice", "Has60dHistory"
    ]

    all_req = ["StockCode", "date"] + num_cols + [t_col]
    train_cutoff = val_start - datetime.timedelta(days=h + 1)
    train_mask = (~df_panel[all_req].isnull().any(axis=1)) & (df_panel["date"] <= train_cutoff)
    X_train_full = df_panel.loc[train_mask, ["StockCode", "date"] + num_cols].reset_index(drop=True)
    y_train_full = df_panel.loc[train_mask, t_col].values.astype(float)

    splitter = DateGroupedTimeSeriesSplit(n_splits=3, horizon=h)
    fold_summaries = splitter.get_fold_summary(X_train_full)
    splits = list(splitter.split(X_train_full))

    candidates = build_candidate_registry(h, num_cols)
    print(f"\n==========================================================================")
    print(f"STARTING COMPREHENSIVE MODEL SEARCH FOR HORIZON D_{h}")
    print(f"Total Candidates: {len(candidates)} across 7 model families")
    print(f"Training History: {len(X_train_full):,} rows ({fold_summaries[0]['train_date_min']} to {fold_summaries[-1]['train_date_max']})")
    print(f"Chronological Folds: {len(splits)} with embargo >= {h+1} days")
    print(f"==========================================================================")

    fold_metrics_records = []
    comparison_records = []

    for cand_idx, cand in enumerate(candidates):
        cand_name = cand["name"]
        cand_family = cand["family"]
        m_type = cand["model_type"]

        fold_wapes = []
        fold_maes = []
        fold_rmses = []
        fold_biases = []

        all_actuals = []
        all_preds = []

        total_fit_time = 0.0
        total_pred_time = 0.0

        for fold_idx, (train_idx, val_idx) in enumerate(splits):
            f_info = fold_summaries[fold_idx]
            X_tr = X_train_full.iloc[train_idx]
            y_tr = y_train_full[train_idx]
            X_va = X_train_full.iloc[val_idx]
            y_va = y_train_full[val_idx]

            # Fit-time subsampling for heavy models to maintain fast turnaround
            if len(X_tr) > subsample_limit and cand_family in ["RandomForest", "ExtraTrees"]:
                sub_idx = np.random.RandomState(42).choice(len(X_tr), size=subsample_limit, replace=False)
                X_tr_fit = X_tr.iloc[sub_idx]
                y_tr_fit = y_tr[sub_idx]
            else:
                X_tr_fit = X_tr
                y_tr_fit = y_tr

            t0 = time.time()
            if m_type == "baseline":
                feat_col = cand["feature"]
                mult = cand["multiplier"]
                preds = np.clip(mult * X_va[feat_col].values.astype(float), 0.0, None)
                fit_t = 0.0
            elif m_type in ["pipeline", "residual"]:
                est = cand["estimator"]
                # Clone/re-instantiate estimator fresh for each fold
                import copy
                fold_est = copy.deepcopy(est)
                fold_est.fit(X_tr_fit, y_tr_fit)
                fit_t = time.time() - t0

                t_pred0 = time.time()
                preds = fold_est.predict(X_va)
                if isinstance(preds, (pd.Series, pd.DataFrame)):
                    preds = preds.values
                preds = np.clip(np.nan_to_num(preds, nan=0.0, posinf=1e6, neginf=0.0), 0.0, None)
                pred_t = time.time() - t_pred0
                total_pred_time += pred_t

            total_fit_time += fit_t

            actual_sum = float(np.sum(y_va))
            pred_sum = float(np.sum(preds))
            w = calculate_wape(y_va, preds)
            m = calculate_mae(y_va, preds)
            r = calculate_rmse(y_va, preds)
            b = (pred_sum - actual_sum) / actual_sum * 100.0 if actual_sum > 0 else 0.0

            fold_wapes.append(w)
            fold_maes.append(m)
            fold_rmses.append(r)
            fold_biases.append(b)

            all_actuals.append(y_va)
            all_preds.append(preds)

            fold_metrics_records.append({
                "horizon": f"D_{h}",
                "model_name": cand_name,
                "model_family": cand_family,
                "fold": fold_idx + 1,
                "train_dates": f"{f_info['train_date_min']} to {f_info['train_date_max']}",
                "train_rows": len(X_tr),
                "val_dates": f"{f_info['val_date_min']} to {f_info['val_date_max']}",
                "val_rows": len(X_va),
                "val_unique_skus": X_va["StockCode"].nunique(),
                "actual_sum": round(actual_sum, 1),
                "wape": round(float(w), 2),
                "mae": round(float(m), 2),
                "rmse": round(float(r), 2),
                "bias_pct": round(float(b), 2),
                "fit_time_sec": round(fit_t, 2)
            })

        # Calculate pooled out-of-fold metrics
        cat_actuals = np.concatenate(all_actuals)
        cat_preds = np.concatenate(all_preds)
        pooled_wape = calculate_wape(cat_actuals, cat_preds)
        pooled_mae = calculate_mae(cat_actuals, cat_preds)
        pooled_rmse = calculate_rmse(cat_actuals, cat_preds)
        pooled_act_sum = float(np.sum(cat_actuals))
        pooled_pred_sum = float(np.sum(cat_preds))
        pooled_bias = (pooled_pred_sum - pooled_act_sum) / pooled_act_sum * 100.0 if pooled_act_sum > 0 else 0.0

        comparison_records.append({
            "horizon": f"D_{h}",
            "model_name": cand_name,
            "model_family": cand_family,
            "pooled_wape": round(float(pooled_wape), 2),
            "pooled_mae": round(float(pooled_mae), 2),
            "pooled_rmse": round(float(pooled_rmse), 2),
            "pooled_bias_pct": round(float(pooled_bias), 2),
            "fold_1_wape": round(float(fold_wapes[0]), 2),
            "fold_2_wape": round(float(fold_wapes[1]), 2),
            "fold_3_wape": round(float(fold_wapes[2]), 2),
            "cv_wape_std": round(float(np.std(fold_wapes)), 2),
            "total_val_rows": len(cat_actuals),
            "actual_sum": round(pooled_act_sum, 1),
            "fit_time_sec": round(total_fit_time, 2),
            "pred_time_sec": round(total_pred_time, 2),
            "params": str(cand["params"])
        })

        if (cand_idx + 1) % 5 == 0 or (cand_idx + 1) == len(candidates):
            print(f"  [{cand_idx+1:02d}/{len(candidates)}] Evaluated {cand_name} ({cand_family}): Pooled WAPE = {pooled_wape:.2f}%, Bias = {pooled_bias:+.2f}%")

    df_comp = pd.DataFrame(comparison_records).sort_values("pooled_wape").reset_index(drop=True)
    df_folds = pd.DataFrame(fold_metrics_records)

    best_record = df_comp.iloc[0].to_dict()
    print(f"\n>>> Best Candidate for D_{h}: {best_record['model_name']} ({best_record['model_family']}) with Pooled WAPE = {best_record['pooled_wape']:.2f}% <<<")

    return df_comp, df_folds, best_record


def evaluate_final_holdout_and_persist(
    df_panel: pd.DataFrame,
    horizon: int,
    best_candidate_name: str,
    output_dir: Path
) -> Dict[str, Any]:
    """Retrains the best candidate on the complete training history and evaluates on the untouched holdout."""
    h = horizon
    val_start, val_end = EVAL_SPLITS[h]
    t_col = f"D_{h}"

    num_cols = [
        "DayOfWeek", "Month", "DayOfMonth",
        "Lag1", "Lag7", "Lag14", "Lag28", "Lag60",
        "RollingMean7", "RollingMean14", "RollingMean28", "RollingMean60",
        "RollingStd7", "RollingStd28",
        "ZeroFraction28", "MomentumRatio", "UnitPrice", "Has60dHistory"
    ]

    all_req = ["StockCode", "date"] + num_cols + [t_col]
    train_cutoff = val_start - datetime.timedelta(days=h + 1)
    train_mask = (~df_panel[all_req].isnull().any(axis=1)) & (df_panel["date"] <= train_cutoff)
    val_mask = (~df_panel[all_req].isnull().any(axis=1)) & (df_panel["date"] >= val_start) & (df_panel["date"] <= val_end)

    X_train = df_panel.loc[train_mask, ["StockCode", "date"] + num_cols].reset_index(drop=True)
    y_train = df_panel.loc[train_mask, t_col].values.astype(float)
    X_val = df_panel.loc[val_mask, ["StockCode", "date"] + num_cols].reset_index(drop=True)
    y_val = df_panel.loc[val_mask, t_col].values.astype(float)

    candidates = build_candidate_registry(h, num_cols)
    selected_cand = next(c for c in candidates if c["name"] == best_candidate_name)

    print(f"\n--- Retraining Selected Model for Horizon D_{h}: {best_candidate_name} ---")
    print(f"Training Samples: {len(X_train):,}, Validation Samples: {len(X_val):,}")

    t0 = time.time()
    m_type = selected_cand["model_type"]

    if m_type == "baseline":
        feat_col = selected_cand["feature"]
        mult = selected_cand["multiplier"]
        preds = np.clip(mult * X_val[feat_col].values.astype(float), 0.0, None)
        model_artifact = ResidualRegressor(base_feature=feat_col, multiplier=mult, estimator=None)
        fit_t = 0.0
    else:
        # For training final model on large dataset, use representative 200k subsample if > 200k
        if len(X_train) > 200000:
            sub = np.random.RandomState(42).choice(len(X_train), size=200000, replace=False)
            X_tr_fit = X_train.iloc[sub]
            y_tr_fit = y_train[sub]
        else:
            X_tr_fit = X_train
            y_tr_fit = y_train

        model_artifact = selected_cand["estimator"]
        model_artifact.fit(X_tr_fit, y_tr_fit)
        fit_t = time.time() - t0
        preds = np.clip(model_artifact.predict(X_val), 0.0, None)

    pred_t = time.time() - (t0 + fit_t)
    actual_sum = float(np.sum(y_val))
    pred_sum = float(np.sum(preds))

    wape = calculate_wape(y_val, preds)
    mae = calculate_mae(y_val, preds)
    rmse = calculate_rmse(y_val, preds)
    bias = (pred_sum - actual_sum) / actual_sum * 100.0 if actual_sum > 0 else 0.0

    # Task 10 benchmark reference
    t10_meta_path = Path("backend/ml/models_experimental_corrected/models_metadata.json")
    if t10_meta_path.is_file():
        with open(t10_meta_path) as f:
            t10_m = json.load(f)["models"][f"D_{h}"]
            t10_wape = t10_m["corrected_wape"]
            t10_mae = t10_m["corrected_mae"]
            t10_bias = t10_m["corrected_bias_pct"]
    else:
        t10_wape, t10_mae, t10_bias = None, None, None

    delta_wape = (t10_wape - wape) if t10_wape is not None else 0.0

    print(f"Holdout Evaluation: WAPE={wape:.2f}% (MAE={mae:.2f}, RMSE={rmse:.2f}, Bias={bias:+.2f}%)")
    if t10_wape is not None:
        print(f"Task 10 Benchmark WAPE: {t10_wape:.2f}% -> Task 12 WAPE: {wape:.2f}% ({delta_wape:+.2f} pp)")

    # Save model artifact
    artifact_path = output_dir / f"demand_model_{h}d.joblib"
    joblib.dump(model_artifact, artifact_path)
    print(f"Saved artifact to: {artifact_path}")

    return {
        "horizon_days": h,
        "selected_model": best_candidate_name,
        "model_family": selected_cand["family"],
        "parameters": selected_cand["params"],
        "holdout_wape": round(float(wape), 2),
        "holdout_mae": round(float(mae), 2),
        "holdout_rmse": round(float(rmse), 2),
        "holdout_bias_pct": round(float(bias), 2),
        "validation_rows": len(y_val),
        "validation_target_sum": round(actual_sum, 1),
        "validation_unique_skus": X_val["StockCode"].nunique(),
        "task10_benchmark_wape": t10_wape,
        "task10_benchmark_mae": t10_mae,
        "task10_benchmark_bias": t10_bias,
        "wape_delta_vs_task10": round(float(delta_wape), 2),
        "fit_time_sec": round(fit_t, 2),
        "pred_time_sec": round(pred_t, 2),
        "features": ["StockCode"] + num_cols,
        "feature_count": len(num_cols) + 1,
        "artifact_file": f"demand_model_{h}d.joblib"
    }


def main():
    base_dir = Path(__file__).resolve().parent.parent
    eval_dir = base_dir / "evaluation"
    models_dir = base_dir / "models_task12"
    eval_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    df_panel, final_prices = load_and_prepare_panel()

    all_comparison_dfs = []
    all_fold_dfs = []
    final_metadata = {
        "project": "NEXORA Task 12 Model Selection & Hyperparameter Optimization",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "dataset_rows": 1067371,
        "dataset_span": "2009-12-01 to 2011-12-09 (738 calendar days)",
        "cross_validation": "3-Fold DateGroupedTimeSeriesSplit with Horizon Embargoes",
        "models": {}
    }

    selected_models_summary = []

    for h in [7, 15, 30, 90]:
        df_comp, df_folds, best_rec = run_model_search_for_horizon(df_panel, horizon=h)
        all_comparison_dfs.append(df_comp)
        all_fold_dfs.append(df_folds)

        # Evaluate best candidate on untouched holdout
        holdout_meta = evaluate_final_holdout_and_persist(
            df_panel,
            horizon=h,
            best_candidate_name=best_rec["model_name"],
            output_dir=models_dir
        )
        holdout_meta["cv_pooled_wape"] = best_rec["pooled_wape"]
        holdout_meta["cv_wape_std"] = best_rec["cv_wape_std"]
        final_metadata["models"][f"D_{h}"] = holdout_meta

        selected_models_summary.append({
            "Horizon": f"D_{h}",
            "Selected Algorithm": best_rec["model_name"],
            "Family": best_rec["model_family"],
            "CV Pooled WAPE": f"{best_rec['pooled_wape']:.2f}%",
            "Holdout WAPE": f"{holdout_meta['holdout_wape']:.2f}%",
            "Task 10 Benchmark": f"{holdout_meta['task10_benchmark_wape']:.2f}%",
            "Holdout Improvement": f"{holdout_meta['wape_delta_vs_task10']:+.2f} pp",
            "Holdout Bias": f"{holdout_meta['holdout_bias_pct']:+.2f}%",
            "Validation Rows": f"{holdout_meta['validation_rows']:,}"
        })

    # Concatenate and save comparison results
    full_comp_df = pd.concat(all_comparison_dfs, ignore_index=True)
    full_folds_df = pd.concat(all_fold_dfs, ignore_index=True)

    comp_csv_path = eval_dir / "task12_model_comparison.csv"
    folds_csv_path = eval_dir / "task12_fold_metrics.csv"
    best_json_path = eval_dir / "task12_best_models.json"
    meta_json_path = models_dir / "models_metadata.json"

    full_comp_df.to_csv(comp_csv_path, index=False)
    full_folds_df.to_csv(folds_csv_path, index=False)

    with open(best_json_path, "w", encoding="utf-8") as f:
        json.dump(final_metadata["models"], f, indent=2)

    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(final_metadata, f, indent=2)

    print("\n==========================================================================")
    print("TASK 12 MODEL SELECTION COMPLETED SUCCESSFULLY!")
    print("==========================================================================")
    df_summary = pd.DataFrame(selected_models_summary)
    print(df_summary.to_string(index=False))
    print(f"\nArtifacts generated:")
    print(f"  - Model comparison CSV: {comp_csv_path} ({len(full_comp_df)} rows)")
    print(f"  - Fold metrics CSV:     {folds_csv_path} ({len(full_folds_df)} rows)")
    print(f"  - Best models JSON:     {best_json_path}")
    print(f"  - Models metadata JSON: {meta_json_path}")
    print(f"  - Model binaries:       {models_dir}/demand_model_*d.joblib")


if __name__ == "__main__":
    main()

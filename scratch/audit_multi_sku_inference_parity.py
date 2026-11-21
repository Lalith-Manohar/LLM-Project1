import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

import datetime
import joblib
import pandas as pd
import numpy as np

from app.services.historical_data_service import historical_data_service
from app.services.experimental_prediction_service import experimental_prediction_service
from app.schemas.forecast import ForecastRequest
from ml.src.point_in_time_price import pit_price_service

print("=== TASK 25: MULTI-SKU MULTI-HORIZON TRAINING & SERVING PARITY AUDIT ===")

historical_data_service.ensure_loaded()
experimental_prediction_service.ensure_loaded()
pit_price_service.ensure_loaded()

# Load all 4 Task 12 pipelines directly
horizons = [7, 15, 30, 90]
pipelines = {h: joblib.load(Path(f"backend/ml/models_task12/demand_model_{h}d.joblib")) for h in horizons}

test_skus = ["85123A", "21777", "22423", "84879", "47566"]

for sku in test_skus:
    print(f"\n--- Testing SKU: {sku} ---")
    features, context = historical_data_service.get_features_for_sku(sku)
    obs_date = datetime.date.fromisoformat(context["observation_date"])
    
    # Construct exact 20-feature DataFrame expected by Task 12 pipelines
    df_features = pd.DataFrame({
        "StockCode": [sku],
        "date": [obs_date],
        "DayOfWeek": [features.day_of_week],
        "Month": [features.month],
        "DayOfMonth": [features.day_of_month],
        "Lag1": [features.lag_1],
        "Lag7": [features.lag_7],
        "Lag14": [features.lag_14],
        "Lag28": [features.lag_28],
        "Lag60": [features.lag_60],
        "RollingMean7": [features.rolling_mean_7],
        "RollingMean14": [features.rolling_mean_14],
        "RollingMean28": [features.rolling_mean_28],
        "RollingMean60": [features.rolling_mean_60],
        "RollingStd7": [features.rolling_std_7],
        "RollingStd28": [features.rolling_std_28],
        "ZeroFraction28": [features.zero_fraction_28],
        "MomentumRatio": [features.momentum_ratio],
        "UnitPrice": [features.unit_price],
        "Has60dHistory": [features.has_60d_history]
    })
    
    # API service prediction
    req = ForecastRequest(stock_code=sku, horizons=horizons)
    api_resp = experimental_prediction_service.get_forecast(req)
    
    for h in horizons:
        pipe = pipelines[h]
        direct_pred = float(np.clip(pipe.predict(df_features)[0], 0.0, None))
        api_pred = api_resp.predictions[str(h)]
        
        diff = abs(direct_pred - api_pred)
        print(f"  Horizon D_{h:2d}: Direct={direct_pred:.4f}, API={api_pred:.4f}, Delta={diff:.6f}")
        assert diff < 1e-4, f"Mismatch on {sku} D_{h}: direct {direct_pred} vs api {api_pred}"

print("\n=== PRICE CUTOFF & TEMPORAL INTEGRITY CHECK ===")
# Verify SKU 85123A price behavior under cutoff
p_op = pit_price_service.get_price("85123A", as_of_date=None)
p_cutoff = pit_price_service.get_price("85123A", as_of_date="2011-12-09")
p_prior = pit_price_service.get_price("85123A", as_of_date="2010-12-09")
print(f"SKU 85123A Latest (operational):               {p_op}")
print(f"SKU 85123A Cutoff 2011-12-09 (excluding Dec 9): {p_cutoff}")
print(f"SKU 85123A Cutoff 2010-12-09 (prior year):      {p_prior}")
assert p_op == 3.0749
assert p_cutoff == 3.0744
assert p_prior == 3.0538

print("\n=== SECTION 6: TRAINING & SERVING PARITY AUDIT PASSED 100% ===")

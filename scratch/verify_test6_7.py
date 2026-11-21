import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

import datetime
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from ml.src.chronological_encoder import ChronologicalTargetEncoder
from ml.src.point_in_time_price import compute_point_in_time_prices

# Test 6 verification
dates = [datetime.date(2011, 1, 1) + datetime.timedelta(days=i) for i in range(40)]
skus = ["SKU_1", "SKU_2", "SKU_3"]
rows = []
for d in dates:
    for s in skus:
        val = 5.0 if s == "SKU_1" else (15.0 if s == "SKU_2" else 25.0)
        rows.append({
            "date": d,
            "StockCode": s,
            "feature_val": val * 1.5,
            "target": val * 7.0
        })
df_orig = pd.DataFrame(rows)

cutoff_date = datetime.date(2011, 1, 25)
df_perturbed = df_orig.copy()
df_perturbed.loc[df_perturbed["date"] >= cutoff_date, "target"] = 77777.0

def make_preprocessor():
    return ColumnTransformer([
        ("cat", ChronologicalTargetEncoder(horizon=7, smooth=10.0, default_prior=0.0), ["StockCode", "date"]),
        ("num", StandardScaler(), ["feature_val"])
    ])

prep1 = make_preprocessor()
prep2 = make_preprocessor()

t1 = prep1.fit_transform(df_orig[["StockCode", "date", "feature_val"]], df_orig["target"])
t2 = prep2.fit_transform(df_perturbed[["StockCode", "date", "feature_val"]], df_perturbed["target"])

past_mask = df_orig["date"] < cutoff_date
diff = np.abs(t1[past_mask] - t2[past_mask])
print("Test 6 max diff:", np.max(diff))
assert np.max(diff) == 0.0

# Test 7 verification with continuous dates
continuous_dates = [datetime.date(2011, 1, 1) + datetime.timedelta(days=i) for i in range(50)]
txs = pd.DataFrame([
    {"date": datetime.date(2011, 1, 10), "StockCode": "SKU_PTEST", "Price": 3.50},
    {"date": datetime.date(2011, 2, 10), "StockCode": "SKU_PTEST", "Price": 9.00}
])

sku_prices, global_prices = compute_point_in_time_prices(txs, continuous_dates, default_price=2.10)
print("Jan 5 price:", sku_prices.loc[datetime.date(2011, 1, 5), "SKU_PTEST"])
print("Jan 15 price:", sku_prices.loc[datetime.date(2011, 1, 15), "SKU_PTEST"])
print("Feb 1 price:", sku_prices.loc[datetime.date(2011, 2, 1), "SKU_PTEST"])
print("Feb 15 price:", sku_prices.loc[datetime.date(2011, 2, 15), "SKU_PTEST"])

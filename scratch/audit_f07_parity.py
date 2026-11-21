import joblib
from pathlib import Path
import inspect
import pandas as pd

backend_dir = Path("backend")
prod_models_dir = backend_dir / "ml" / "models"

print("=== INSPECTING PRODUCTION MODEL FEATURE CONTRACT ===")
for h in [7, 15, 30, 90]:
    p_path = prod_models_dir / f"demand_model_{h}d.joblib"
    pipe = joblib.load(p_path)
    print(f"\nHorizon D_{h}:")
    print(f"  Pipeline steps: {[s[0] for s in pipe.steps]}")
    prep = pipe.named_steps.get("preprocessor")
    if prep:
        for trans_name, trans_obj, cols in prep.transformers:
            print(f"    Transformer '{trans_name}': cols={cols}")

import sys
sys.path.insert(0, str(backend_dir))
from app.services.prediction_service import PredictionService

svc = PredictionService()
print("\nPredictionService expected features:")
if hasattr(svc, "feature_columns"):
    print(f"  feature_columns: {svc.feature_columns}")
print("PredictionService inspection complete.")

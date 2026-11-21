import joblib
import json
from pathlib import Path

backend_dir = Path("backend").resolve()

# 1. Check production models
print("=== CHECKING PRODUCTION MODELS (backend/ml/models/) ===")
prod_pipe = joblib.load(backend_dir / "ml" / "models" / "demand_model_7d.joblib")
prep = prod_pipe.named_steps["preprocessor"]
cat_trans = prep.named_transformers_["cat"]
categories = list(cat_trans.categories_[0])
print(f"Top 50 categories in production OneHotEncoder ({len(categories)}):")
service_in_prod_ohe = [c for c in categories if c in {'POST', 'DOT', 'M', 'BANK CHARGES', 'PADS', 'AMAZONFEE', 'D', 'CRUK', 'ADJUST', 'TEST001', 'C2'}]
print(f"Service codes in production top-50 OHE: {service_in_prod_ohe}")

# Check all categories in production OHE
for c in categories:
    if any(s in c for s in ['POST', 'DOT', 'M', 'BANK', 'PADS', 'AMAZON', 'CRUK', 'ADJUST', 'TEST']):
        print(f"  Suspicious category: {c}")

# 2. Check Task 12 experimental models
print("\n=== CHECKING TASK 12 EXPERIMENTAL MODELS (backend/ml/models_task12/) ===")
for h in [7, 15, 30, 90]:
    exp_pipe = joblib.load(backend_dir / "ml" / "models_task12" / f"demand_model_{h}d.joblib")
    print(f"Horizon {h}d: {type(exp_pipe)}")
    if hasattr(exp_pipe, "named_steps"):
        exp_prep = exp_pipe.named_steps.get("preprocessor")
        if exp_prep:
            exp_encoder = exp_prep.named_transformers_.get("cat")
            if hasattr(exp_encoder, "final_encodings_"):
                encs = exp_encoder.final_encodings_
                service_in_encs = [k for k in encs.keys() if k in {'POST', 'DOT', 'M', 'BANK CHARGES', 'PADS', 'AMAZONFEE', 'D', 'CRUK', 'ADJUST', 'TEST001', 'C2'}]
                print(f"  Service codes in ChronologicalTargetEncoder encodings: {service_in_encs}")
    elif hasattr(exp_pipe, "estimator") and exp_pipe.estimator:
        # ResidualRegressor
        inner = exp_pipe.estimator
        if hasattr(inner, "named_steps"):
            exp_prep = inner.named_steps.get("preprocessor")
            exp_encoder = exp_prep.named_transformers_.get("cat")
            if hasattr(exp_encoder, "final_encodings_"):
                encs = exp_encoder.final_encodings_
                service_in_encs = [k for k in encs.keys() if k in {'POST', 'DOT', 'M', 'BANK CHARGES', 'PADS', 'AMAZONFEE', 'D', 'CRUK', 'ADJUST', 'TEST001', 'C2'}]
                print(f"  Service codes in Residual inner ChronologicalTargetEncoder encodings: {service_in_encs}")

print("\nModel provenance check complete.")

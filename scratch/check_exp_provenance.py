import sys
from pathlib import Path
backend_dir = Path("backend").resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import joblib

NON_MERCHANDISE_CODES = {'POST', 'DOT', 'M', 'BANK CHARGES', 'PADS', 'AMAZONFEE', 'D', 'CRUK', 'ADJUST', 'TEST001', 'C2'}

print("=== CHECKING TASK 12 EXPERIMENTAL MODELS (backend/ml/models_task12/) ===")
for h in [7, 15, 30, 90]:
    p = backend_dir / "ml" / "models_task12" / f"demand_model_{h}d.joblib"
    model = joblib.load(p)
    print(f"\nHorizon D_{h} ({type(model).__name__}):")
    
    preprocessor = None
    if hasattr(model, "named_steps"):
        preprocessor = model.named_steps.get("preprocessor")
    elif hasattr(model, "estimator") and hasattr(model.estimator, "named_steps"):
        preprocessor = model.estimator.named_steps.get("preprocessor")
        
    if preprocessor:
        cat_trans = preprocessor.named_transformers_.get("cat")
        if cat_trans:
            encs = getattr(cat_trans, "final_encodings_", {})
            service_found = [k for k in encs.keys() if k in NON_MERCHANDISE_CODES]
            print(f"  Total SKUs encoded in ChronologicalTargetEncoder: {len(encs):,}")
            print(f"  Service codes found in encodings: {service_found}")

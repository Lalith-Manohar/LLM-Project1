import json
from pathlib import Path

backend_dir = Path("backend")
prod_f = backend_dir / "ml" / "models" / "models_metadata.json"
exp_f = backend_dir / "ml" / "models_task12" / "models_metadata.json"

print("=== PRODUCTION METADATA ===")
if prod_f.exists():
    with open(prod_f) as fp:
        p_data = json.load(fp)
        print("Keys:", list(p_data.keys()))
        for k, v in p_data.items():
            if isinstance(v, dict):
                print(f"\n[{k}]")
                for sub_k in ["selected_model", "best_family", "metrics", "test_metrics", "features", "feature_columns", "holdout_period", "train_period", "embargo_days"]:
                    if sub_k in v:
                        print(f"  {sub_k}: {v[sub_k]}")
            else:
                print(f"Top {k}: {v}")

print("\n=== TASK 12 EXPERIMENTAL METADATA ===")
if exp_f.exists():
    with open(exp_f) as fp:
        e_data = json.load(fp)
        print("Keys:", list(e_data.keys()))
        for k, v in e_data.items():
            if isinstance(v, dict):
                print(f"\n[{k}]")
                for sub_k in ["selected_model", "selected_model_name", "family", "metrics", "test_metrics", "cv_wape", "holdout_wape", "features", "feature_names", "evaluation_split", "train_date_range"]:
                    if sub_k in v:
                        print(f"  {sub_k}: {v[sub_k]}")
            else:
                print(f"Top {k}: {v}")

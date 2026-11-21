import json
from pathlib import Path

backend_dir = Path("backend")
prod_meta_dir = backend_dir / "ml" / "models"
exp_meta_dir = backend_dir / "ml" / "models_task12"

print("--- PRODUCTION MODELS METADATA (backend/ml/models/) ---")
for h in [7, 15, 30, 90]:
    f = prod_meta_dir / f"metadata_{h}d.json"
    if f.exists():
        with open(f) as fp:
            meta = json.load(fp)
            print(f"Horizon {h}d:")
            print(f"  Selected Model: {meta.get('selected_model')}")
            print(f"  Best Family: {meta.get('best_family')}")
            print(f"  Train samples: {meta.get('train_samples')}")
            print(f"  Test samples: {meta.get('test_samples')}")
            print(f"  Holdout period: {meta.get('holdout_start')} to {meta.get('holdout_end')}")
            print(f"  Metrics: {meta.get('metrics')}")
            print(f"  Features ({len(meta.get('feature_columns', []))}): {meta.get('feature_columns')}")

print("\n--- TASK 12 EXPERIMENTAL MODELS METADATA (backend/ml/models_task12/) ---")
for h in [7, 15, 30, 90]:
    f = exp_meta_dir / f"metadata_{h}d.json"
    if f.exists():
        with open(f) as fp:
            meta = json.load(fp)
            print(f"Horizon {h}d:")
            print(f"  Selected Model: {meta.get('selected_model_name') or meta.get('model_name')}")
            print(f"  Family: {meta.get('family')}")
            print(f"  Evaluation Split: {meta.get('evaluation_split')}")
            print(f"  Metrics: {meta.get('test_metrics') or meta.get('metrics')}")
            print(f"  Features ({len(meta.get('feature_names', []))}): {meta.get('feature_names')}")

import json
from pathlib import Path

backend_dir = Path("backend")
prod_f = backend_dir / "ml" / "models" / "models_metadata.json"
exp_f = backend_dir / "ml" / "models_task12" / "models_metadata.json"

print("=== PRODUCTION MODELS DETAILS ===")
with open(prod_f) as fp:
    p = json.load(fp)["models"]
    for k, v in p.items():
        print(f"\n[{k}]:")
        for sub_k, sub_v in v.items():
            if sub_k == "comparison":
                print(f"  comparison count: {len(sub_v)}")
                for row in sub_v:
                    print(f"    - {row.get('model_name')}: MAE={row.get('mae')}, RMSE={row.get('rmse')}, WAPE={row.get('wape')}%")
            else:
                print(f"  {sub_k}: {sub_v}")

print("\n=== TASK 12 EXPERIMENTAL MODELS DETAILS ===")
with open(exp_f) as fp:
    e = json.load(fp)["models"]
    for k, v in e.items():
        print(f"\n[{k}]:")
        for sub_k, sub_v in v.items():
            if sub_k == "all_candidates_summary":
                print(f"  candidates tested: {len(sub_v)}")
            else:
                print(f"  {sub_k}: {sub_v}")

import hashlib
from pathlib import Path

backend_dir = Path("backend")

expected_prod_hashes = {
    "demand_model_7d.joblib": "C33D53FBECD7A22A06ABDA91FEDB7E5B2A7823FF8E9AA313324079CA0CC2309E",
    "demand_model_15d.joblib": "A33A26C0F57291F2A97968EF57FB5017578E638DAC9A688A7A65EEB1814062B2",
    "demand_model_30d.joblib": "AF7C91232FBB8C0B799B64017CE35188D949E7D280D50000DF16D9DFC4EB7409",
    "demand_model_90d.joblib": "26959280F18675EA977397E4861C1E8CABC3CBFE379B9670471E2DD0353E5A81"
}

expected_exp_hashes = {
    "demand_model_7d.joblib": "F0DE9357FED2FB9E2497AEC26475EAC958C8CB969E9FA1B19BF4A95A76869B7F",
    "demand_model_15d.joblib": "B5FA0E912612F180B8F9F6CACE8AA39CC180714556AB2A4B2867B4C0600B463B",
    "demand_model_30d.joblib": "3735467A4B9ADAC04563EF352CE61B71A51B97BC174BFCEB67A6ACD0B90202A5",
    "demand_model_90d.joblib": "A7AD19C2C20F871669C7810EB8E35232910A24568A4802DF4410827E9A6F590D"
}

print("=== CHECKING PRODUCTION MODEL HASHES ===")
for fname, exp_hash in expected_prod_hashes.items():
    p = backend_dir / "ml" / "models" / fname
    h = hashlib.sha256(p.read_bytes()).hexdigest().upper()
    match = (h == exp_hash)
    print(f"Prod {fname}: {h[:16]}... MATCH={match}")
    assert match

print("\n=== CHECKING EXPERIMENTAL TASK 12 MODEL HASHES ===")
for fname, exp_hash in expected_exp_hashes.items():
    p = backend_dir / "ml" / "models_task12" / fname
    h = hashlib.sha256(p.read_bytes()).hexdigest().upper()
    match = (h == exp_hash)
    print(f"Exp {fname}: {h[:16]}... MATCH={match}")
    assert match

print("\nAll 8 model binaries are 100% BITWISE INTACT!")

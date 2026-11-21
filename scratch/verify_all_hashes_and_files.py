import hashlib
import os

model_dir = "backend/ml/models"
horizons = [7, 15, 30, 90]
expected_hashes = {
    7: "C33D53FBECD7A22A06ABDA91FEDB7E5B2A7823FF8E9AA313324079CA0CC2309E",
    15: "A33A26C0F57291F2A97968EF57FB5017578E638DAC9A688A7A65EEB1814062B2",
    30: "AF7C91232FBB8C0B799B64017CE35188D949E7D280D50000DF16D9DFC4EB7409",
    90: "26959280F18675EA977397E4861C1E8CABC3CBFE379B9670471E2DD0353E5A81"
}

print("=== SHA-256 HASH VERIFICATION OF PRODUCTION MODELS ===")
all_match = True
for h in horizons:
    fpath = os.path.join(model_dir, f"demand_model_{h}d.joblib")
    if not os.path.exists(fpath):
        print(f"D{h}: NOT FOUND at {fpath}")
        all_match = False
        continue
    with open(fpath, "rb") as f:
        hval = hashlib.sha256(f.read()).hexdigest().upper()
    exp = expected_hashes[h]
    match = (hval == exp)
    print(f"D{h} ({fpath}):")
    print(f"  Calculated: {hval}")
    print(f"  Expected:   {exp}")
    print(f"  Match:      {match}")
    if not match:
        all_match = False

print(f"\nAll Production Model Hashes Match Expected: {all_match}")

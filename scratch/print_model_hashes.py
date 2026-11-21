import hashlib
from pathlib import Path

print("=== ACTUAL MODEL HASHES ===")
for p in sorted(Path("backend/ml").glob("*models*/*.joblib")):
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    print(f'"{p.as_posix()}": "{h}",')

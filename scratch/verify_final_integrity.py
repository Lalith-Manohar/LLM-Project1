import hashlib
import subprocess
from pathlib import Path

print("=== FINAL GIT & MODEL INTEGRITY VERIFICATION ===")

# 1. Git branch and HEAD
branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
print(f"Active branch: {branch}")
print(f"HEAD commit: {head}")
assert branch == "uni_api_experimental", f"Wrong branch: {branch}"
assert head == "657ee56e82a19bab646ee74a14fbed3bec903e03", f"Wrong HEAD: {head}"

# 2. Protected branches
sub_rev = subprocess.check_output(["git", "rev-parse", "uni_api_submission"], text=True).strip()
main_rev = subprocess.check_output(["git", "rev-parse", "main"], text=True).strip()
print(f"uni_api_submission commit: {sub_rev}")
print(f"main commit: {main_rev}")
assert sub_rev == "596430fc6c53dd526b48b9d25d666611d71938a1", f"uni_api_submission altered: {sub_rev}"
assert main_rev == "f0e56bad2e0673d651a92f622b349de53203c0fc", f"main altered: {main_rev}"

# 3. Model hashes
EXPECTED_HASHES = {
    "backend/ml/models/demand_model_7d.joblib": "c33d53fbecd7a22a06abda91fedb7e5b2a7823ff8e9aa313324079ca0cc2309e",
    "backend/ml/models/demand_model_15d.joblib": "a33a26c0f57291f2a97968ef57fb5017578e638dac9a688a7a65eeb1814062b2",
    "backend/ml/models/demand_model_30d.joblib": "af7c91232fbb8c0b799b64017ce35188d949e7d280d50000df16d9dfc4eb7409",
    "backend/ml/models/demand_model_90d.joblib": "26959280f18675ea977397e4861c1e8cabc3cbfe379b9670471e2dd0353e5a81",
    "backend/ml/models_task12/demand_model_7d.joblib": "f0de9357fed2fb9e2497aec26475eac958c8cb969e9fa1b19bf4a95a76869b7f",
    "backend/ml/models_task12/demand_model_15d.joblib": "b5fa0e912612f180b8f9f6cace8aa39cc180714556ab2a4b2867b4c0600b463b",
    "backend/ml/models_task12/demand_model_30d.joblib": "3735467a4b9adac04563ef352ce61b71a51b97bc174bfceb67a6acd0b90202a5",
    "backend/ml/models_task12/demand_model_90d.joblib": "a7ad19c2c20f871669c7810eb8e35232910a24568a4802df4410827e9a6f590d",
}

print("\nVerifying model binary SHA-256 hashes:")
for path_str, exp_hash in EXPECTED_HASHES.items():
    p = Path(path_str)
    assert p.is_file(), f"Model file missing: {p}"
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    assert h == exp_hash, f"Hash mismatch for {p}!\nGot:      {h}\nExpected: {exp_hash}"
    print(f"  [INTACT] {p.name} ({p.parent.name}): {h}")

# 4. Git status & diff summary
status = subprocess.check_output(["git", "status", "--short"], text=True)
print(f"\nGit status:\n{status}")

diff_stat = subprocess.check_output(["git", "diff", "--stat"], text=True)
print(f"Git diff --stat:\n{diff_stat}")

print("\n=== ALL INTEGRITY CHECKS PASSED 100% ===")

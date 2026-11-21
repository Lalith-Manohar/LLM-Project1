import hashlib
import subprocess
import sys
from pathlib import Path

print("=== TASK 27: PRE-COMMIT PRECONDITION CHECKS ===")

# 1. Active branch
branch = subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
print(f"Active branch: {branch}")
assert branch == "uni_api_experimental", f"Wrong branch: {branch}"

# 2. HEAD commit
head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
print(f"HEAD commit: {head}")
assert head == "657ee56e82a19bab646ee74a14fbed3bec903e03", f"Wrong HEAD: {head}"

# 3. uni_api_submission commit
sub_rev = subprocess.check_output(["git", "rev-parse", "uni_api_submission"], text=True).strip()
print(f"uni_api_submission: {sub_rev}")
assert sub_rev == "596430fc6c53dd526b48b9d25d666611d71938a1", f"uni_api_submission changed: {sub_rev}"

# 4. main commit
main_rev = subprocess.check_output(["git", "rev-parse", "main"], text=True).strip()
print(f"main: {main_rev}")
assert main_rev == "f0e56bad2e0673d651a92f622b349de53203c0fc", f"main changed: {main_rev}"

# 5. Exactly 10 authorized files
AUTHORIZED_FILES = [
    "backend/app/core/config.py",
    "backend/app/main.py",
    "backend/app/services/experimental_prediction_service.py",
    "backend/ml/data/processed/daily_product_demand.csv",
    "backend/ml/src/preprocessing.py",
    "backend/tests/test_leakage_corrections.py",
    "docs/DEVELOPMENT_LOG.md",
    "docs/KNOWN_ISSUES.md",
    "docs/postman/NEXORA_Experimental_API.postman_collection.json",
    "start.ps1",
]

# Check modified tracked files
status_raw = subprocess.check_output(["git", "status", "--porcelain"], text=True).splitlines()
modified_files = []
untracked_files = []
for line in status_raw:
    status_code = line[:2]
    filename = line[3:].strip()
    if status_code.strip() == "M":
        modified_files.append(filename)
    elif status_code.strip() == "??":
        untracked_files.append(filename)

print(f"\nModified tracked files ({len(modified_files)}):")
for f in modified_files:
    print(f"  {f}")
assert sorted(modified_files) == sorted(AUTHORIZED_FILES), f"Modified files do not match authorized files!\nExpected: {sorted(AUTHORIZED_FILES)}\nGot: {sorted(modified_files)}"

print(f"\nUntracked files/dirs: {untracked_files}")
assert untracked_files == ["scratch/"], f"Unexpected untracked files: {untracked_files}"

print("\n--- ALL PRECONDITIONS PASSED 100% ---")

# 6. Stage exactly the 10 authorized files
print("\nStaging the 10 authorized files individually...")
for f in AUTHORIZED_FILES:
    subprocess.check_call(["git", "add", f])
    print(f"  Staged: {f}")

# Verify staged files in git index
staged_diff = subprocess.check_output(["git", "diff", "--cached", "--name-only"], text=True).splitlines()
print(f"\nStaged files in Git index ({len(staged_diff)}):")
for f in staged_diff:
    print(f"  {f}")
assert sorted(staged_diff) == sorted(AUTHORIZED_FILES), f"Staged files mismatch!\nExpected: {sorted(AUTHORIZED_FILES)}\nGot: {sorted(staged_diff)}"

# Ensure nothing from scratch/ is staged
for f in staged_diff:
    assert not f.startswith("scratch/"), f"Scratch file accidentally staged: {f}"

# 7. Create commit
COMMIT_MSG = "feat(experimental): complete dataset regeneration, CORS lockdown, leakage test hardening, and demonstration freeze"
print(f"\nCreating commit with message: '{COMMIT_MSG}'...")
subprocess.check_call(["git", "commit", "-m", COMMIT_MSG])

# 8. Post-commit verification
new_head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
new_parent = subprocess.check_output(["git", "rev-parse", "HEAD~1"], text=True).strip()
commit_msg_actual = subprocess.check_output(["git", "log", "-1", "--pretty=%B"], text=True).strip()
commit_files = subprocess.check_output(["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], text=True).splitlines()
status_after = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()

print("\n=== POST-COMMIT VERIFICATION ===")
print(f"1. New Commit Hash:    {new_head}")
print(f"2. Parent Commit Hash: {new_parent}")
assert new_parent == "657ee56e82a19bab646ee74a14fbed3bec903e03", f"Wrong parent: {new_parent}"
print(f"3. Commit Message:     {commit_msg_actual}")
assert commit_msg_actual == COMMIT_MSG, f"Wrong commit message: {commit_msg_actual}"
print(f"4. Files in Commit ({len(commit_files)}):")
for f in commit_files:
    print(f"     {f}")
assert sorted(commit_files) == sorted(AUTHORIZED_FILES), f"Committed files mismatch!"

print(f"\n5. Git Status after commit:\n{status_after if status_after else '(completely clean)'}")
assert status_after == "?? scratch/", f"Working tree not clean: {status_after}"

# 6. Verify protected branches
sub_rev_after = subprocess.check_output(["git", "rev-parse", "uni_api_submission"], text=True).strip()
main_rev_after = subprocess.check_output(["git", "rev-parse", "main"], text=True).strip()
print(f"\n6. uni_api_submission hash: {sub_rev_after}")
assert sub_rev_after == "596430fc6c53dd526b48b9d25d666611d71938a1"
print(f"7. main hash:               {main_rev_after}")
assert main_rev_after == "f0e56bad2e0673d651a92f622b349de53203c0fc"

# 8. Model hashes
EXPECTED_HASHES = {
    "backend/ml/models/demand_model_7d.joblib": "C33D53FBECD7A22A06ABDA91FEDB7E5B2A7823FF8E9AA313324079CA0CC2309E",
    "backend/ml/models/demand_model_15d.joblib": "A33A26C0F57291F2A97968EF57FB5017578E638DAC9A688A7A65EEB1814062B2",
    "backend/ml/models/demand_model_30d.joblib": "AF7C91232FBB8C0B799B64017CE35188D949E7D280D50000DF16D9DFC4EB7409",
    "backend/ml/models/demand_model_90d.joblib": "26959280F18675EA977397E4861C1E8CABC3CBFE379B9670471E2DD0353E5A81",
    "backend/ml/models_task12/demand_model_7d.joblib": "F0DE9357FED2FB9E2497AEC26475EAC958C8CB969E9FA1B19BF4A95A76869B7F",
    "backend/ml/models_task12/demand_model_15d.joblib": "B5FA0E912612F180B8F9F6CACE8AA39CC180714556AB2A4B2867B4C0600B463B",
    "backend/ml/models_task12/demand_model_30d.joblib": "3735467A4B9ADAC04563EF352CE61B71A51B97BC174BFCEB67A6ACD0B90202A5",
    "backend/ml/models_task12/demand_model_90d.joblib": "A7AD19C2C20F871669C7810EB8E35232910A24568A4802DF4410827E9A6F590D",
}

print("\n8. Model Hash Verification:")
for path_str, exp_hash in EXPECTED_HASHES.items():
    h = hashlib.sha256(Path(path_str).read_bytes()).hexdigest().upper()
    assert h == exp_hash, f"Hash mismatch for {path_str}!"
    print(f"  [INTACT] {Path(path_str).name} ({Path(path_str).parent.name})")

# 9. Recovery files
patch_file = Path("scratch/task22_working_changes.patch")
backup_dir = Path("scratch/backup_task22_pre_regeneration")
print(f"\n9. Recovery files:")
print(f"  Patch exists: {patch_file.is_file()} (Size: {patch_file.stat().st_size} bytes)")
print(f"  Backup directory count: {len(list(backup_dir.glob('*')))} files")
assert patch_file.is_file() and patch_file.stat().st_size == 46870
assert len(list(backup_dir.glob("*"))) == 9

print("\n=== TASK 27 COMMIT EXECUTION & VERIFICATION COMPLETE: 100% SUCCESS ===")

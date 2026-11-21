import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

origins_to_test = [
    ("http://localhost:5173", True, "Local Vite Frontend"),
    ("http://127.0.0.1:5173", True, "Local IP Vite Frontend"),
    ("http://localhost:3000", True, "Local CRA Frontend"),
    ("http://127.0.0.1:3000", True, "Local IP CRA Frontend"),
    ("http://localhost:8000", True, "Local Swagger/Docs"),
    ("http://127.0.0.1:8000", True, "Local IP Swagger/Docs"),
    ("https://malicious-attacker.com", False, "Disallowed External Origin"),
    ("http://evil-site.org", False, "Disallowed Evil Origin"),
]

print("=== CORS PREFLIGHT OPTIONS & CREDENTIALS AUDIT ===")
for origin, expected_allowed, desc in origins_to_test:
    res = client.options("/api/v1/forecast/health", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET"
    })
    
    allow_origin = res.headers.get("access-control-allow-origin")
    allow_creds = res.headers.get("access-control-allow-credentials")
    
    if expected_allowed:
        status_ok = (res.status_code == 200)
        origin_ok = (allow_origin == origin)
        creds_ok = (allow_creds == "true")
        print(f"[ALLOWED] {origin} ({desc}): HTTP {res.status_code} | allow-origin={allow_origin} | allow-credentials={allow_creds} -> {'PASS' if (status_ok and origin_ok and creds_ok) else 'FAIL'}")
        assert status_ok and origin_ok and creds_ok
    else:
        status_ok = (res.status_code == 400 or allow_origin is None)
        print(f"[REJECTED] {origin} ({desc}): HTTP {res.status_code} | allow-origin={allow_origin} -> {'PASS (Blocked)' if status_ok else 'FAIL (Leaked)'}")
        assert status_ok

print("\nCORS Audit: 100% PASSED!")

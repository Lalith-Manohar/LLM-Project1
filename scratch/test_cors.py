import sys
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

res = client.options("/api/v1/forecast/health", headers={
    "Origin": "http://localhost:5173",
    "Access-Control-Request-Method": "GET"
})
print("OPTIONS localhost:5173 status:", res.status_code)
print("Headers:", {k: v for k, v in res.headers.items() if "access-control" in k.lower()})

res2 = client.options("/api/v1/forecast/health", headers={
    "Origin": "https://malicious-site.com",
    "Access-Control-Request-Method": "GET"
})
print("\nOPTIONS malicious-site.com status:", res2.status_code)
print("Headers:", {k: v for k, v in res2.headers.items() if "access-control" in k.lower()})

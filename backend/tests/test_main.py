"""Basic test suite for FastAPI health check and routing."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify that the root endpoint returns 200 OK and valid metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "project" in data
    assert data["status"] == "online"


def test_health_check_endpoint():
    """Verify that the health-check endpoint reports service health."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_forecast_horizons_endpoint():
    """Verify that supported forecast horizons are available."""
    response = client.get("/api/v1/forecast/horizons")
    assert response.status_code == 200
    data = response.json()
    assert "supported_horizons_days" in data
    assert 30 in data["supported_horizons_days"]

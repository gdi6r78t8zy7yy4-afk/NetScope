# NetScope API Endpoints Tests

"""
Tests for API endpoints to ensure they return correct responses.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app
    
    with TestClient(app) as test_client:
        yield test_client


def test_root_endpoint(client):
    """Test root endpoint returns correct version."""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["status"] == "running"
    
    # Verify version format
    version = data["version"]
    assert isinstance(version, str)
    parts = version.split(".")
    assert len(parts) == 3


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_api_info_endpoint(client):
    """Test API information endpoint."""
    response = client.get("/api-info")
    
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "routes" in data
    assert len(data["routes"]) > 0
    
    # Verify expected routes exist
    expected_routes = [
        "/api/v1/networks",
        "/api/v1/discovery",
        "/api/v1/scans",
        "/api/v1/assets",
        "/api/v1/vulnerabilities"
    ]
    
    for route in expected_routes:
        assert route in data["routes"]


def test_root_response_format(client):
    """Test root endpoint response format."""
    response = client.get("/")
    
    assert response.status_code == 200
    
    data = response.json()
    
    # Check required fields
    assert isinstance(data["name"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["status"], str)


def test_api_version_format(client):
    """Test API version format."""
    response = client.get("/api-info")
    
    data = response.json()
    version = data["version"]
    
    # Check semantic versioning format
    parts = version.split(".")
    assert len(parts) == 3
    
    for part in parts:
        assert part.isdigit()


def test_health_endpoint_structure(client):
    """Test health endpoint response structure."""
    response = client.get("/health")
    
    assert response.status_code == 200
    
    data = response.json()
    
    # Check required fields
    assert "status" in data
    assert isinstance(data["status"], str)


def test_api_routes_not_empty(client):
    """Test that API routes list is not empty."""
    response = client.get("/api-info")
    
    data = response.json()
    routes = data["routes"]
    
    assert isinstance(routes, list)
    assert len(routes) > 0
    
    # Verify each route is a string
    for route in routes:
        assert isinstance(route, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

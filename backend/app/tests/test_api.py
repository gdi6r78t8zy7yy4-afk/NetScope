# NetScope API Tests

"""
Unit tests for the API endpoints.
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


def test_root_response_format(client):
    """Test root endpoint response format."""
    response = client.get("/")
    
    assert response.status_code == 200
    
    data = response.json()
    
    # Check required fields
    assert isinstance(data["name"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["status"], str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

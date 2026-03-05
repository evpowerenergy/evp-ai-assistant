"""
Authentication tests
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth import verify_jwt_token, get_user_from_token

client = TestClient(app)


def test_health_without_auth():
    """Test health endpoint without auth"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_chat_without_auth():
    """Test chat endpoint without auth should fail"""
    response = client.post(
        "/api/v1/chat",
        json={"message": "test"}
    )
    assert response.status_code == 403  # Forbidden


def test_chat_with_invalid_token():
    """Test chat endpoint with invalid token"""
    response = client.post(
        "/api/v1/chat",
        json={"message": "test"},
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401  # Unauthorized


# Note: Full auth tests require valid JWT tokens from Supabase
# These will be added when we have test fixtures

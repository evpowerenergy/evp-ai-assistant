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


# LINE webhook: invalid signature when configured
def test_line_webhook_invalid_signature(monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.line.settings.LINE_CHANNEL_SECRET",
        "test_secret",
    )
    body = b'{"events":[]}'
    response = client.post(
        "/api/v1/line/webhook",
        content=body,
        headers={"X-Line-Signature": "invalid"},
    )
    assert response.status_code == 400


def test_line_webhook_not_configured():
    response = client.post(
        "/api/v1/line/webhook",
        content=b'{"events":[]}',
        headers={"X-Line-Signature": "x"},
    )
    # 503 if LINE_CHANNEL_SECRET empty in test env, or 400 if invalid sig
    assert response.status_code in (400, 503)


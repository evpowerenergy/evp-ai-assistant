from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.core.execution_auth import require_execution_scope, verify_execution_token
from app.core.execution_token import create_execution_token
from app.engines.base import ActorContext


def _keys():
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


def test_execution_capability_round_trip(monkeypatch):
    private, public = _keys()
    monkeypatch.setattr("app.core.execution_token.settings.EVP_EXECUTION_PRIVATE_KEY", private)
    monkeypatch.setattr("app.core.execution_auth.settings.EVP_EXECUTION_PUBLIC_KEY", public)
    token = create_execution_token(
        ActorContext(
            user_id="user-1",
            user_role="manager_sale",
            session_id="session-1",
            source="test",
            request_id="00000000-0000-0000-0000-000000000001",
        )
    )

    payload = verify_execution_token(token)

    assert payload["sub"] == "user-1"
    assert payload["session_id"] == "session-1"
    require_execution_scope(payload, "crm.read")
    assert "marketing.read" not in payload["scopes"]


def test_execution_capability_rejects_wrong_key(monkeypatch):
    private, _ = _keys()
    _, unrelated_public = _keys()
    monkeypatch.setattr("app.core.execution_token.settings.EVP_EXECUTION_PRIVATE_KEY", private)
    monkeypatch.setattr("app.core.execution_auth.settings.EVP_EXECUTION_PUBLIC_KEY", unrelated_public)
    token = create_execution_token(
        ActorContext("user-1", "manager_hr", "session-1", "test", "request-1")
    )

    try:
        verify_execution_token(token)
        assert False, "wrong signing key must be rejected"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 401

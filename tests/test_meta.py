import hashlib
import hmac
import json

from app.config import get_settings
from app.providers import MetaMessagingProvider


def test_meta_provider_uses_bearer_token_without_logging(monkeypatch, capsys):
    token = "test-secret-token"
    monkeypatch.setenv("MESSAGING_PROVIDER", "meta")
    monkeypatch.setenv("META_ACCESS_TOKEN", token)
    monkeypatch.setenv("META_PHONE_NUMBER_ID", "123")
    get_settings.cache_clear()
    provider = MetaMessagingProvider()
    assert provider.headers["Authorization"] == f"Bearer {token}"
    assert "******" not in provider.headers["Authorization"]
    assert token not in capsys.readouterr().out
    get_settings.cache_clear()


def test_whatsapp_signature_validation(client, monkeypatch):
    secret = "app-secret"
    monkeypatch.setenv("META_APP_SECRET", secret)
    get_settings.cache_clear()
    body = {
        "message_id": "signed-1",
        "phone_number": "+15550003",
        "text": "Q1: cache replicas and rate limiting",
    }
    raw = json.dumps(body).encode()
    signature = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    assert client.post("/webhooks/whatsapp", content=raw).status_code == 403
    response = client.post(
        "/webhooks/whatsapp",
        content=raw,
        headers={"X-Hub-Signature-256": signature},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    get_settings.cache_clear()



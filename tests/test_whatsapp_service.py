import hashlib
import hmac
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import backend.main as main_module
from backend.config import settings
from backend.services.whatsapp_service import (
    format_whatsapp_text,
    whatsapp_service,
)


@pytest.fixture
def client():
    return TestClient(main_module.app)


def configure_whatsapp(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_ENABLED", True)
    monkeypatch.setattr(settings, "WHATSAPP_TOKEN", "access-token")
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "123456")
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "verify-token")
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "app-secret")


def signature_for(body):
    digest = hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_format_whatsapp_text():
    raw = "### Resumen de IPS\n**Bogotá** tiene _500_ camas.\n\n- Opción 1"
    formatted = format_whatsapp_text(raw)
    assert "*Resumen de IPS*" in formatted
    assert "*Bogotá*" in formatted
    assert "_500_" in formatted


def test_webhook_verification_success(client, monkeypatch):
    configure_whatsapp(monkeypatch)
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "verify-token",
            "hub.challenge": "1122334455",
        },
    )
    assert response.status_code == 200
    assert response.text == "1122334455"


def test_webhook_verification_failure_does_not_log_token(
    client, monkeypatch, caplog
):
    configure_whatsapp(monkeypatch)
    response = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-secret-value",
            "hub.challenge": "1122334455",
        },
    )
    assert response.status_code == 403
    assert "wrong-secret-value" not in caplog.text


def test_webhook_post_rejects_invalid_signature(client, monkeypatch):
    configure_whatsapp(monkeypatch)
    response = client.post(
        "/api/v1/whatsapp/webhook",
        content=b'{"object":"whatsapp_business_account","entry":[]}',
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )
    assert response.status_code == 403


def test_webhook_post_processes_signed_message(
    client, monkeypatch
):
    configure_whatsapp(monkeypatch)
    sent_messages = []

    async def fake_query(user_query, session_id=None, use_documents=False):
        assert user_query == "¿Cuántas camas hay en Antioquia?"
        assert session_id == "wa_573009998877"
        return SimpleNamespace(formatted_message="Hay 12 camas.")

    async def fake_send(to_number, text):
        sent_messages.append((to_number, text))
        return True

    monkeypatch.setattr(main_module, "_execute_query", fake_query)
    monkeypatch.setattr(whatsapp_service, "send_message", fake_send)

    payload = (
        b'{"object":"whatsapp_business_account","entry":[{"changes":[{"value":'
        b'{"contacts":[{"wa_id":"573009998877","profile":{"name":"Carlos"}}],'
        b'"messages":[{"from":"573009998877","id":"wamid.123","type":"text",'
        b'"text":{"body":"\\u00bfCu\\u00e1ntas camas hay en Antioquia?"}}]}}]}]}'
    )
    response = client.post(
        "/api/v1/whatsapp/webhook",
        content=payload,
        headers={"X-Hub-Signature-256": signature_for(payload)},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "messages_queued": 1}
    assert sent_messages == [("573009998877", "Hay 12 camas.")]


def test_extract_messages_ignores_malformed_items():
    payload = {
        "entry": [
            None,
            {
                "changes": [
                    {"value": {"messages": [None, {"from": "abc", "id": "x"}]}}
                ]
            },
        ]
    }
    assert whatsapp_service.extract_messages(payload) == []


def test_public_config_requires_enabled_and_complete_webhook(
    client, monkeypatch
):
    configure_whatsapp(monkeypatch)
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER", "+57 300 123 4567")
    response = client.get("/api/v1/whatsapp/config")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is True
    assert data["webhook_configured"] is True
    assert "wa.me/573001234567" in data["wa_link"]

    monkeypatch.setattr(settings, "WHATSAPP_ENABLED", False)
    response = client.get("/api/v1/whatsapp/config")
    assert response.json()["enabled"] is False

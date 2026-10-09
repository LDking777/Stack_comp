import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
from backend.services.whatsapp_service import whatsapp_service, format_whatsapp_text


@pytest.fixture
def client():
    return TestClient(app)


def test_format_whatsapp_text():
    raw = "### Resumen de IPS\n**Bogotá** tiene _500_ camas.\n\n- Opción 1"
    formatted = format_whatsapp_text(raw)
    assert "*Resumen de IPS*" in formatted
    assert "*Bogotá*" in formatted
    assert "_500_" in formatted


def test_whatsapp_webhook_verification_success(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "test_token_1234")
    res = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test_token_1234",
            "hub.challenge": "1122334455",
        },
    )
    assert res.status_code == 200
    assert res.text == "1122334455"


def test_whatsapp_webhook_verification_failure(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "correct_token")
    res = client.get(
        "/api/v1/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token",
            "hub.challenge": "1122334455",
        },
    )
    assert res.status_code == 403


def test_whatsapp_webhook_extract_message():
    sample_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "123456",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"display_phone_number": "573001234567"},
                            "contacts": [{"profile": {"name": "Carlos"}, "wa_id": "573009998877"}],
                            "messages": [
                                {
                                    "from": "573009998877",
                                    "id": "wamid.HBgL",
                                    "timestamp": "1710000000",
                                    "text": {"body": "¿Cuántas camas hay en Antioquia?"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    extracted = whatsapp_service.extract_messages(sample_payload)
    assert len(extracted) == 1
    assert extracted[0]["sender_id"] == "573009998877"
    assert extracted[0]["sender_name"] == "Carlos"
    assert "¿Cuántas camas hay en Antioquia?" in extracted[0]["text"]


def test_whatsapp_webhook_post_endpoint(client, monkeypatch):
    # Mock send_message to avoid actual network call
    async def mock_send(to_number, text):
        return True

    monkeypatch.setattr(whatsapp_service, "send_message", mock_send)

    sample_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "573001112233",
                                    "id": "wamid.123",
                                    "type": "text",
                                    "text": {"body": "Hola"},
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    res = client.post("/api/v1/whatsapp/webhook", json=sample_payload)
    assert res.status_code == 200
    assert res.json().get("status") == "ok"
    assert res.json().get("messages_queued") == 1


def test_whatsapp_config_endpoint(client, monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_PHONE_NUMBER", "573001234567")
    res = client.get("/api/v1/whatsapp/config")
    assert res.status_code == 200
    data = res.json()
    assert data["enabled"] is True
    assert "573001234567" in data["phone_number"]
    assert "wa.me/573001234567" in data["wa_link"]

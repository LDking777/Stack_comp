"""Helpers for Meta WhatsApp Cloud API webhooks and outbound messages."""

import hashlib
import hmac
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


def format_whatsapp_text(markdown_text: str) -> str:
    """Convert the Markdown subset used by Nexo IA to WhatsApp formatting."""
    if not markdown_text:
        return ""

    text = markdown_text.strip()
    text = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class WhatsAppService:
    """Verifies Meta webhook requests and sends Cloud API messages."""

    @property
    def is_configured(self) -> bool:
        return bool(
            settings.WHATSAPP_ENABLED
            and settings.WHATSAPP_TOKEN
            and settings.WHATSAPP_PHONE_NUMBER_ID
        )

    @property
    def webhook_configured(self) -> bool:
        return bool(
            self.is_configured
            and settings.WHATSAPP_VERIFY_TOKEN
            and settings.WHATSAPP_APP_SECRET
        )

    @property
    def api_url(self) -> str:
        return (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )

    def verify_webhook(
        self,
        hub_mode: Optional[str],
        hub_verify_token: Optional[str],
        hub_challenge: Optional[str],
    ) -> Optional[str]:
        expected_token = settings.WHATSAPP_VERIFY_TOKEN
        if (
            not expected_token
            or hub_mode != "subscribe"
            or not hub_verify_token
            or not hmac.compare_digest(hub_verify_token, expected_token)
        ):
            logger.warning("Fallo de verificación del webhook de WhatsApp.")
            return None
        return hub_challenge or ""

    def verify_signature(self, body: bytes, signature: str) -> bool:
        app_secret = settings.WHATSAPP_APP_SECRET
        if not app_secret or not signature:
            return False

        expected = "sha256=" + hmac.new(
            app_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def extract_messages(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract supported text and interactive replies from a Meta event."""
        extracted: List[Dict[str, Any]] = []
        entries = payload.get("entry")
        if not isinstance(entries, list):
            return extracted

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            changes = entry.get("changes")
            if not isinstance(changes, list):
                continue
            for change in changes:
                if not isinstance(change, dict):
                    continue
                value = change.get("value")
                if not isinstance(value, dict):
                    continue

                contacts = value.get("contacts")
                contacts_by_id = {}
                if isinstance(contacts, list):
                    for contact in contacts:
                        if not isinstance(contact, dict):
                            continue
                        profile = contact.get("profile")
                        profile = profile if isinstance(profile, dict) else {}
                        wa_id = contact.get("wa_id")
                        if isinstance(wa_id, str):
                            contacts_by_id[wa_id] = profile.get("name")

                messages = value.get("messages")
                if not isinstance(messages, list):
                    continue
                for message in messages:
                    if not isinstance(message, dict):
                        continue
                    sender_id = message.get("from")
                    message_id = message.get("id")
                    if not isinstance(sender_id, str) or not sender_id.isdigit():
                        continue
                    if not isinstance(message_id, str) or not message_id:
                        continue

                    text = ""
                    if message.get("type") == "text":
                        text_data = message.get("text")
                        if isinstance(text_data, dict):
                            body = text_data.get("body")
                            if isinstance(body, str):
                                text = body.strip()
                    elif message.get("type") == "interactive":
                        interactive = message.get("interactive")
                        if isinstance(interactive, dict):
                            for reply_type in ("button_reply", "list_reply"):
                                reply = interactive.get(reply_type)
                                if isinstance(reply, dict) and isinstance(
                                    reply.get("title"), str
                                ):
                                    text = reply["title"].strip()
                                    break
                    elif message.get("type") == "button":
                        button = message.get("button")
                        if isinstance(button, dict) and isinstance(
                            button.get("text"), str
                        ):
                            text = button["text"].strip()

                    if text:
                        extracted.append(
                            {
                                "sender_id": sender_id,
                                "sender_name": contacts_by_id.get(sender_id)
                                or sender_id,
                                "text": text,
                                "message_id": message_id,
                            }
                        )
        return extracted

    async def send_message(self, to_number: str, text: str) -> bool:
        if not self.is_configured:
            logger.error(
                "No se puede enviar WhatsApp: faltan credenciales o el canal está deshabilitado."
            )
            return False

        clean_text = format_whatsapp_text(text)
        if len(clean_text) > 4000:
            clean_text = (
                clean_text[:3980]
                + "\n\n_...[Respuesta recortada por límite de WhatsApp]_"
            )

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"preview_url": False, "body": clean_text},
        }
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    self.api_url, json=payload, headers=headers
                )
        except httpx.HTTPError:
            logger.exception("Error de red al enviar mensaje por WhatsApp.")
            return False

        if response.is_success:
            return True
        logger.error(
            "Meta rechazó el mensaje de WhatsApp: status=%s.",
            response.status_code,
        )
        return False

    def get_public_url(self) -> Optional[str]:
        phone = re.sub(r"\D", "", settings.WHATSAPP_PHONE_NUMBER or "")
        if not phone:
            return None
        return (
            f"https://wa.me/{phone}"
            "?text=Hola%20Nexo%20IA%2C%20deseo%20consultar%20capacidad%20de%20IPS"
        )


whatsapp_service = WhatsAppService()

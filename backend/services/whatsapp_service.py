"""
Servicio de integración con WhatsApp Cloud API (Meta Graph API).

Permite recibir mensajes entrantes de WhatsApp vía Webhook y responder
utilizando el pipeline de Nexo IA (Fast Path + SoQL determinista + Heavy Path),
conservando la memoria de conversación por número de remitente.
"""
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


def format_whatsapp_text(markdown_text: str) -> str:
    """
    Adapta el formato Markdown estándar a la sintaxis nativa de WhatsApp:
    - Encabezados #, ##, ### se convierten a *texto en negrita*
    - **negrita** se mantiene como *negrita* de WhatsApp
    - _cursiva_ se mantiene
    - Listas numeradas y viñetas se limpian
    """
    if not markdown_text:
        return ""

    text = markdown_text.strip()

    # Convertir encabezados Markdown (ej: ### Título) a *Título*
    text = re.sub(r"^#{1,6}\s*(.+)$", r"*\1*", text, flags=re.MULTILINE)

    # WhatsApp usa *texto* para negrita (en markdown suele ser **texto**)
    # Reemplazamos **dobles asteriscos** por *un solo asterisco*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

    # Limpiar saltos de línea excesivos
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


class WhatsAppService:
    """Maneja la verificación de webhooks y el envío de mensajes a la Cloud API de Meta."""

    @property
    def is_configured(self) -> bool:
        """Indica si las credenciales de Meta WhatsApp están configuradas en el entorno."""
        return bool(settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)

    @property
    def api_url(self) -> str:
        return f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

    def verify_webhook(
        self,
        hub_mode: Optional[str],
        hub_verify_token: Optional[str],
        hub_challenge: Optional[str],
    ) -> Optional[str]:
        """
        Verifica el handshake inicial que Meta envía vía GET al configurar el webhook.
        Si coincide el token, devuelve el challenge para responder con HTTP 200.
        """
        expected_token = settings.WHATSAPP_VERIFY_TOKEN
        if not expected_token:
            logger.warning("WHATSAPP_VERIFY_TOKEN no está configurado en .env.")
            return None

        if hub_mode == "subscribe" and hub_verify_token == expected_token:
            logger.info("✅ Handshake de Webhook de WhatsApp verificado exitosamente.")
            return hub_challenge or ""

        logger.warning(
            "Fallo de verificación de Webhook de WhatsApp: modo=%s, token_recibido=%s",
            hub_mode,
            hub_verify_token,
        )
        return None

    def extract_messages(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extrae los mensajes de texto entrantes desde el payload JSON de Meta Webhooks.
        Soporta formato estándar de WhatsApp Business Cloud API.
        """
        messages_extracted = []
        try:
            entries = payload.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    contacts = {c.get("wa_id"): c.get("profile", {}).get("name") for c in value.get("contacts", [])}
                    messages = value.get("messages", [])
                    for msg in messages:
                        # Procesar mensajes de texto
                        msg_type = msg.get("type")
                        sender_id = msg.get("from")
                        msg_id = msg.get("id")

                        if msg_type == "text":
                            text_body = msg.get("text", {}).get("body", "").strip()
                            if text_body and sender_id:
                                messages_extracted.append({
                                    "sender_id": sender_id,
                                    "sender_name": contacts.get(sender_id) or sender_id,
                                    "text": text_body,
                                    "message_id": msg_id,
                                    "timestamp": msg.get("timestamp"),
                                })
                        elif msg_type in ("interactive", "button"):
                            # Soporte para respuestas de botones
                            btn_text = (
                                msg.get("interactive", {}).get("button_reply", {}).get("title")
                                or msg.get("button", {}).get("text")
                            )
                            if btn_text and sender_id:
                                messages_extracted.append({
                                    "sender_id": sender_id,
                                    "sender_name": contacts.get(sender_id) or sender_id,
                                    "text": btn_text.strip(),
                                    "message_id": msg_id,
                                    "timestamp": msg.get("timestamp"),
                                })
        except Exception as exc:
            logger.error("Error analizando payload entrante de WhatsApp: %s", exc)

        return messages_extracted

    async def send_message(self, to_number: str, text: str) -> bool:
        """
        Envía un mensaje de texto saliente a un usuario de WhatsApp mediante Meta Graph API.
        """
        if not self.is_configured:
            logger.warning("No se puede enviar mensaje de WhatsApp: WHATSAPP_TOKEN o PHONE_NUMBER_ID no configurados.")
            return False

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
            "Content-Type": "application/json",
        }

        clean_text = format_whatsapp_text(text)

        # Meta limita el mensaje a 4096 caracteres
        if len(clean_text) > 4000:
            clean_text = clean_text[:3980] + "\n\n_...[Respuesta recortada por límite de WhatsApp]_"

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": clean_text,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                if response.status_code in (200, 201):
                    logger.info("Mensaje de WhatsApp enviado exitosamente a %s", to_number)
                    return True
                else:
                    logger.error(
                        "Error de Meta API enviando mensaje a %s: status=%s, body=%s",
                        to_number,
                        response.status_code,
                        response.text,
                    )
                    return False
        except Exception as exc:
            logger.error("Excepción enviando mensaje de WhatsApp a %s: %s", to_number, exc)
            return False

    def get_public_url(self) -> Optional[str]:
        """Devuelve el enlace wa.me público con mensaje precargado para la web."""
        phone = re.sub(r"[^\d]", "", settings.WHATSAPP_PHONE_NUMBER or "")
        if not phone:
            return None
        return f"https://wa.me/{phone}?text=Hola%20Nexo%20IA,%20deseo%20consultar%20informaci%C3%B3n%20sobre%20IPS%20de%20Colombia"


whatsapp_service = WhatsAppService()

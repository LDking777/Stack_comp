"""
Credenciales efímeras para Gemini Live API (voz bidireccional).

La API key permanente (`GEMINI_API_KEY`) nunca sale del backend. Este servicio
mintea un token de corta vida que el navegador usa como si fuera una api key,
pero que solo sirve para abrir una sesión Live (Gemini Developer API, v1alpha).

Mecanismo oficial (documentación vigente de Google):
    client.auth_tokens.create(config={...})  # google-genai, v1alpha
    o REST POST https://generativelanguage.googleapis.com/v1beta/auth_tokens

Requiere el SDK `google-genai`. El `google-generativeai` que usa el resto del
backend no expone `auth_tokens`, así que se importa de forma perezosa para no
afectar a los proveedores de texto (Groq/OpenAI) cuando Live no se usa.
"""
import asyncio
import datetime
import logging
from typing import Any, Dict, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


def _iso(value: Any) -> Optional[str]:
    """Normaliza un datetime o string a ISO-8601, o None si no aplica."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    return str(value)


class LiveTokenService:
    """Mintea credenciales efímeras de Live desde el servidor."""

    @property
    def available(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    def _create_sync(self) -> Any:
        # Import perezoso: si Live no se usa, el backend no carga google-genai.
        from google import genai

        client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options={"api_version": "v1alpha"},
        )
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        return client.auth_tokens.create(
            config={
                # El token solo puede iniciar una sesión: reduce el riesgo si
                # se filtra desde el navegador.
                "uses": 1,
                "expire_time": now
                + datetime.timedelta(minutes=settings.GEMINI_LIVE_TOKEN_TTL_MIN),
                "new_session_expire_time": now
                + datetime.timedelta(minutes=settings.GEMINI_LIVE_NEW_SESSION_TTL_MIN),
            }
        )

    async def create_token(self) -> Dict[str, Any]:
        """
        Devuelve un dict con `ok=True` y la credencial, o `ok=False` y el
        motivo. Nunca lanza: el endpoint traduce el fallo a HTTP 503 y el
        frontend mantiene el chat de texto.
        """
        if not self.available:
            return {
                "ok": False,
                "error": "GEMINI_API_KEY no configurada en el backend.",
            }
        try:
            token = await asyncio.to_thread(self._create_sync)
        except ImportError:
            return {
                "ok": False,
                "error": "SDK google-genai no instalado en el backend (pip install google-genai).",
            }
        except Exception as exc:
            logger.error("No se pudo mintear credencial efimera de Live: %s", exc)
            return {
                "ok": False,
                "error": f"No se pudo crear la credencial efímera: {type(exc).__name__}: {exc}",
            }

        name = getattr(token, "name", None) or str(token)
        return {
            "ok": True,
            "token": name,
            "model": settings.GEMINI_LIVE_MODEL,
            "expires_at": _iso(getattr(token, "expire_time", None)),
            "new_session_expires_at": _iso(getattr(token, "new_session_expire_time", None)),
        }


live_token_service = LiveTokenService()

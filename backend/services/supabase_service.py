"""Small async PostgREST/Storage client using the backend-only service role key."""
import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    @property
    def _server_key(self) -> str:
        return settings.SUPABASE_SECRET_KEY or settings.SUPABASE_SERVICE_ROLE_KEY

    @property
    def available(self) -> bool:
        return bool(settings.SUPABASE_URL and self._server_key)

    def require_configured(self) -> None:
        if not self.available:
            raise RuntimeError(
                "La persistencia requiere SUPABASE_URL y "
                "SUPABASE_SECRET_KEY (o SUPABASE_SERVICE_ROLE_KEY legado) "
                "configuradas en el backend."
            )

    @staticmethod
    def validate_session_id(session_id: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", session_id):
            raise ValueError("El identificador de sesión no tiene un formato válido.")

    async def healthcheck(self) -> Dict[str, Any]:
        if not self.available:
            return {
                "configured": False,
                "ready": False,
                "provider": None,
                "error": "Configura Supabase en el backend.",
            }
        try:
            await self.rest(
                "GET",
                "/rest/v1/chat_sessions",
                params={"select": "id", "limit": "0"},
            )
            await self.rest(
                "GET",
                "/rest/v1/document_chunks",
                params={"select": "id", "limit": "0"},
            )
            await self.rest(
                "POST",
                "/rest/v1/rpc/match_document_chunks",
                json={
                    "match_session_id": "health-check",
                    "query_embedding": "["
                    + ",".join(["0"] * settings.GEMINI_EMBEDDING_DIMENSIONS)
                    + "]",
                    "match_count": 1,
                    "min_similarity": 1.0,
                },
            )
            await self.rest(
                "GET",
                f"/storage/v1/bucket/{quote(settings.SUPABASE_STORAGE_BUCKET, safe='')}",
            )
        except RuntimeError:
            return {
                "configured": True,
                "ready": False,
                "provider": "Supabase",
                "error": "No se pudo verificar el esquema o bucket privado requerido.",
            }
        return {
            "configured": True,
            "ready": True,
            "provider": "Supabase Postgres + Storage",
            "error": None,
        }

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        self.require_configured()
        headers = {
            "apikey": self._server_key,
            "Authorization": f"Bearer {self._server_key}",
        }
        if extra:
            headers.update(extra)
        return headers

    async def rest(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, str]] = None,
        json: Any = None,
        content: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        self.require_configured()
        if params:
            for field in ("session_id", "id"):
                value = params.get(field, "")
                if value.startswith("eq."):
                    self.validate_session_id(value[3:])
        url = f"{settings.SUPABASE_URL.rstrip('/')}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    content=content,
                    headers=self._headers(headers),
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Supabase respondió HTTP %s en %s %s: %s",
                exc.response.status_code,
                method,
                path,
                exc.response.text[:500],
            )
            raise RuntimeError(
                f"Supabase respondió HTTP {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("No se pudo conectar con Supabase en %s %s: %s", method, path, exc)
            raise RuntimeError("No se pudo conectar con Supabase.") from exc

        if not response.content:
            return None
        return response.json()

    async def ensure_session(self, session_id: str) -> None:
        self.validate_session_id(session_id)
        await self.rest(
            "POST",
            "/rest/v1/chat_sessions",
            params={"on_conflict": "id"},
            json={"id": session_id},
            headers={"Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"},
        )

    async def upload_object(self, path: str, data: bytes, content_type: str) -> None:
        encoded_path = quote(path, safe="/")
        await self.rest(
            "POST",
            f"/storage/v1/object/{quote(settings.SUPABASE_STORAGE_BUCKET, safe='')}/{encoded_path}",
            content=data,
            headers={
                "Content-Type": content_type,
                "x-upsert": "false",
            },
        )

    async def delete_objects(self, paths: list[str]) -> None:
        if not paths:
            return
        await self.rest(
            "DELETE",
            f"/storage/v1/object/{quote(settings.SUPABASE_STORAGE_BUCKET, safe='')}",
            json={"prefixes": paths},
            headers={"Content-Type": "application/json"},
        )


supabase_service = SupabaseService()

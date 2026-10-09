"""Embeddings de texto con Gemini (`google-genai`).

La fuente de datos de cifras sigue siendo SoQL; los embeddings solo indexan los
documentos que el usuario sube. Import perezoso de `google.genai` para no cargar
el SDK cuando la función de documentos no se usa.
"""
import asyncio
import logging
from typing import List

from backend.config import settings

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Genera vectores para indexar y consultar documentos (RAG)."""

    def __init__(self):
        self._client = None

    @property
    def available(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    def _ensure_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def _embed_sync(self, texts: List[str], task_type: str) -> List[List[float]]:
        client = self._ensure_client()
        result = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=texts,
            config={
                "task_type": task_type,
                "output_dimensionality": settings.GEMINI_EMBEDDING_DIMENSIONS,
            },
        )
        return [list(embedding.values) for embedding in result.embeddings]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        if not self.available:
            raise RuntimeError(
                "GEMINI_API_KEY no configurada: no se pueden generar embeddings."
            )
        return await asyncio.to_thread(self._embed_sync, texts, "RETRIEVAL_DOCUMENT")

    async def embed_query(self, text: str) -> List[float]:
        if not self.available:
            raise RuntimeError(
                "GEMINI_API_KEY no configurada: no se pueden generar embeddings."
            )
        vectors = await asyncio.to_thread(
            self._embed_sync, [text], "RETRIEVAL_QUERY"
        )
        return vectors[0]


embeddings_service = EmbeddingsService()

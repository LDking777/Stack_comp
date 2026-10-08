"""
Knowledge de auditoría parametrizable.

Lee la tabla `knowledge_auditoria` de Supabase y selecciona las entradas que
aplican a una consulta. Sustituye al dict de `knowledge_base.py` (v1), pero con
un cambio de fondo: aquí el knowledge NO cortaba antes del LLM, solo aporta
directrices de análisis al prompt.

Si la tabla no existe o Supabase no responde, el servicio degrada a contexto
vacío. Eso no rompe el pipeline: el Heavy Path sigue funcionando, simplemente
sin las directrices de auditoría.
"""

import logging
import re
from typing import List, Optional, Sequence

import httpx

from backend.config import settings
from backend.schemas.knowledge_schemas import KnowledgeContext, KnowledgeEntry
from backend.services.normalization import strip_accents

logger = logging.getLogger(__name__)

KNOWLEDGE_TABLE = "knowledge_auditoria"

# Máximo de entradas que se inyectan al prompt. Más de esto es contexto sin
# señal: diluye el foco del modelo y encarece cada llamada del Heavy Path.
MAX_ENTRIES_IN_PROMPT = 4


def _fold(value: str) -> str:
    """Minúsculas y sin diacríticos, para comparar consultas y trigger_key."""
    return strip_accents(str(value or "")).strip().lower()


class KnowledgeAuditService:
    """
    Consulta y matchea el knowledge de auditoría contra la consulta del usuario.
    """

    def __init__(self):
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        # La secret key evita los bloqueos de RLS en la lectura.
        self.api_key = settings.SUPABASE_SECRET_KEY or settings.SUPABASE_KEY
        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.api_key)

    async def _fetch_entries(self) -> List[KnowledgeEntry]:
        """
        Trae las entradas activas. Cualquier fallo devuelve lista vacía: el
        knowledge es opcional, nunca debe tumbar la consulta.
        """
        if not self.available:
            logger.warning("Knowledge de auditoría no disponible: credenciales ausentes.")
            return []

        url = f"{self.base_url}/rest/v1/{KNOWLEDGE_TABLE}?select=*&activo=eq.true&order=prioridad.asc,id.asc"
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(url, headers=self.headers)
                if response.status_code != 200:
                    logger.warning(
                        f"Fallo al leer {KNOWLEDGE_TABLE} ({response.status_code}). "
                        "El Heavy Path seguirá sin directrices de auditoría."
                    )
                    return []
                return [KnowledgeEntry.model_validate(row) for row in response.json()]
        except Exception as exc:
            logger.warning(f"Excepción consultando {KNOWLEDGE_TABLE}: {exc}")
            return []

    @staticmethod
    def _matches(entry: KnowledgeEntry, folded_query: str) -> bool:
        """
        Match por frase completa, no por subcadena.

        Es deliberado: 'pais' como subcadena aparece dentro de 'paisaje', y
        `match_country` ya documentó por qué el matching laxo por subcadena
        produjo falsos positivos.
        """
        trigger = _fold(entry.trigger_key)
        if not trigger:
            return False
        return bool(re.search(rf"(?<!\w){re.escape(trigger)}(?!\w)", folded_query))

    @staticmethod
    def _scoped_to(entry: KnowledgeEntry, folded_query: str) -> bool:
        """
        Una entrada de mercado 'GLOBAL' siempre aplica; una específica solo
        si su mercado aparece en la consulta.
        """
        mercado = _fold(entry.mercado)
        if not mercado or mercado == "global":
            return True
        return bool(re.search(rf"(?<!\w){re.escape(mercado)}(?!\w)", folded_query))

    async def build_context(
        self,
        query: str,
        categorias: Optional[Sequence[str]] = None,
        max_entries: int = MAX_ENTRIES_IN_PROMPT,
    ) -> KnowledgeContext:
        """
        Devuelve las entradas que aplican a `query`.

        `categorias` acota la búsqueda para no cargar el catálogo completo; si se
        omite, se consideran todas.
        """
        # La consulta se valida antes de tocar la red: sin texto no hay nada que
        # matchear y la lectura sería un gasto inútil.
        folded_query = _fold(query)
        if not folded_query:
            return KnowledgeContext(entradas=[], consulta=query)

        try:
            entradas = await self._fetch_entries()
        except Exception as exc:
            # Defensa en profundidad: `_fetch_entries` ya atrapa sus propios
            # errores, pero el knowledge es opcional y nunca debe tumbar el
            # pipeline del Heavy Path.
            logger.warning(f"Knowledge de auditoría no disponible: {exc}")
            return KnowledgeContext(entradas=[], consulta=query)

        if not entradas:
            return KnowledgeContext(entradas=[], consulta=query)

        permitidas = {_fold(c) for c in categorias} if categorias else None
        aplicadas = [
            entry
            for entry in entradas
            if (permitidas is None or _fold(entry.categoria.value) in permitidas)
            and self._scoped_to(entry, folded_query)
            and self._matches(entry, folded_query)
        ]

        # `prioridad.asc` ya viene del ORDER BY, pero se reordena aquí porque
        # `max_entries` recorta y el corte debe favorece la mayor prioridad.
        aplicadas.sort(key=lambda e: (e.prioridad, e.id))

        if len(aplicadas) > max_entries:
            logger.info(
                f"Knowledge: {len(aplicadas)} entradas aplican a la consulta; "
                f"se inyectan las {max_entries} de mayor prioridad."
            )
            aplicadas = aplicadas[:max_entries]

        return KnowledgeContext(entradas=aplicadas, consulta=query)


knowledge_service = KnowledgeAuditService()
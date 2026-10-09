"""
Knowledge de auditoría del asistente de IPS.

La fuente de verdad es el archivo local `backend/data/knowledge_ips.json`
(conjunto de directrices propio del asistente). Este servicio lee ese archivo y
selecciona las entradas que aplican a una consulta.

El knowledge NO corta antes del LLM: solo aporta directrices de análisis al
prompt. Si el archivo falta o está corrupto, el servicio degrada a contexto
vacío y el Heavy Path sigue funcionando, simplemente sin las directrices.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Optional, Sequence

from backend.schemas.knowledge_schemas import KnowledgeContext, KnowledgeEntry
from backend.services.normalization import strip_accents

logger = logging.getLogger(__name__)

KNOWLEDGE_FILE = Path(__file__).resolve().parents[1] / "data" / "knowledge_ips.json"

# Máximo de entradas que se inyectan al prompt. Más de esto es contexto sin
# señal: diluye el foco del modelo y encarece cada llamada del Heavy Path.
MAX_ENTRIES_IN_PROMPT = 4


def _fold(value: str) -> str:
    """Minúsculas y sin diacríticos, para comparar consultas y trigger_key."""
    return strip_accents(str(value or "")).strip().lower()


class KnowledgeAuditService:
    """
    Lee y matchea el knowledge de auditoría contra la consulta del usuario.
    """

    def __init__(self, path: Path = KNOWLEDGE_FILE):
        self.path = path
        self._cache: Optional[List[KnowledgeEntry]] = None
        self._cache_mtime: Optional[float] = None

    @property
    def available(self) -> bool:
        return self.path.is_file()

    def _load_entries(self) -> List[KnowledgeEntry]:
        """
        Lee las entradas del archivo local. Cualquier fallo devuelve lista
        vacía: el knowledge es opcional, nunca debe tumbar la consulta.

        Se cachea por mtime para releer solo si el archivo cambió entre
        despliegues o ediciones.
        """
        if not self.available:
            logger.warning("Knowledge no disponible: falta %s.", self.path)
            return []

        try:
            mtime = self.path.stat().st_mtime
            if self._cache is not None and self._cache_mtime == mtime:
                return self._cache

            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._cache = [KnowledgeEntry.model_validate(row) for row in data]
            self._cache_mtime = mtime
            return self._cache
        except Exception as exc:
            logger.warning("Excepción leyendo %s: %s", self.path, exc)
            return []

    @staticmethod
    def _matches(entry: KnowledgeEntry, folded_query: str) -> bool:
        """
        Match por frase completa, no por subcadena.

        Es deliberado: 'pais' como subcadena aparece dentro de 'paisaje', y un
        matching laxo por subcadena produce falsos positivos.
        """
        trigger = _fold(entry.trigger_key)
        if not trigger:
            return False
        return bool(re.search(rf"(?<!\w){re.escape(trigger)}(?!\w)", folded_query))

    @staticmethod
    def _scoped_to(entry: KnowledgeEntry, folded_query: str) -> bool:
        """
        Una entrada 'GLOBAL' siempre aplica; una de ámbito específico
        (departamento) solo si ese ámbito aparece en la consulta.
        """
        ambito = _fold(entry.ambito)
        if not ambito or ambito == "global":
            return True
        return bool(re.search(rf"(?<!\w){re.escape(ambito)}(?!\w)", folded_query))

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
        # La consulta se valida antes de tocar el disco: sin texto no hay nada
        # que matchear y la lectura sería un gasto inútil.
        folded_query = _fold(query)
        if not folded_query:
            return KnowledgeContext(entradas=[], consulta=query)

        entradas = self._load_entries()
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

        # `max_entries` recorta: el orden debe favorecer la mayor prioridad.
        aplicadas.sort(key=lambda e: (e.prioridad, e.id))

        if len(aplicadas) > max_entries:
            logger.info(
                "Knowledge: %s entradas aplican a la consulta; se inyectan las %s "
                "de mayor prioridad.",
                len(aplicadas),
                max_entries,
            )
            aplicadas = aplicadas[:max_entries]

        return KnowledgeContext(entradas=aplicadas, consulta=query)


knowledge_service = KnowledgeAuditService()

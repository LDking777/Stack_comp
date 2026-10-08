"""
Fixtures compartidas.

Dos cosas importantes para la suite:

1. `_ROUTE_STATS` es estado global del modulo `intent_router`. Sin resetearlo
   entre tests, los contadores de `route_stats()` se contaminan y las aserciones
   sobre `llm_responses` / `fallback_responses` dejan de significar nada.

2. `FALLBACK_CONFIDENCES` son las confianzas fijas de `_heuristic_fallback`.
   Es la unica senal de que el LLM no se uso (ver AGENTS.md, trampa 2), asi que
   la suite la reutiliza como detector en lugar de codificarla de nuevo.
"""

import asyncio
import os

import pytest

from backend.services import intent_router as intent_router_module


# Confianzas que SOLO produce `_heuristic_fallback`. El LLM devuelve valores
# intermedios (0.88-0.95). Ver AGENTS.md seccion 6, trampa 2.
FALLBACK_CONFIDENCES = {0.85, 0.88, 0.90}


@pytest.fixture(autouse=True)
def reset_route_stats():
    """Aislar los contadores globales antes y despues de cada test."""
    intent_router_module._ROUTE_STATS["llm"] = 0
    intent_router_module._ROUTE_STATS["fallback"] = 0
    intent_router_module._ROUTE_STATS["fallback_reasons"] = {}
    yield
    intent_router_module._ROUTE_STATS["llm"] = 0
    intent_router_module._ROUTE_STATS["fallback"] = 0
    intent_router_module._ROUTE_STATS["fallback_reasons"] = {}


@pytest.fixture
def route_stats():
    """Atajo de solo lectura a los contadores."""
    return intent_router_module.route_stats()


class FakeLLM:
    """Doble de `llm_client` para probar ramas sin tocar la red."""

    def __init__(self, result=None, error=None, available=True, init_error=None):
        self._result = result
        self._error = error
        self.available = available
        self.init_error = init_error
        self.provider = "gemini"
        self.calls = 0

    def router_model(self):
        return "fake-model"

    def insights_model(self):
        return "fake-model"

    async def structured(self, **kwargs):
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._result


@pytest.fixture
def patch_llm(monkeypatch):
    """
    Sustituye `intent_router.llm_client` por un `FakeLLM` y devuelve el doble,
    para poder inyectar resultados o errores sin llamar a Gemini.
    """
    def _install(fake: FakeLLM) -> FakeLLM:
        monkeypatch.setattr(intent_router_module, "llm_client", fake)
        return fake
    return _install


@pytest.fixture
def live_llm_enabled() -> bool:
    """
    Las pruebas contra el proveedor real son opt-in. Se activan con
    `NEXO_TEST_LIVE_LLM=1` porque consumen cuota y son intermitentes por latencia.
    """
    return os.getenv("NEXO_TEST_LIVE_LLM", "").strip() in {"1", "true", "True"}


@pytest.fixture
def timeout_error():
    """`asyncio.TimeoutError` con `str()` vacio, igual que el del runtime."""
    return asyncio.TimeoutError()
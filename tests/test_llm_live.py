"""
Pruebas contra el proveedor real. Son opt-in:

    $env:NEXO_TEST_LIVE_LLM=1; .\\venv\\Scripts\\python.exe -m pytest tests/test_llm_live.py -v

No corren por defecto porque consumen cuota y su latencia es intermitente.

 Estas pruebas son las unicas que pueden detectar el fallo original: el router
devolvia una respuesta aparentemente correcta mientras el LLM nunca se habia
consultado. Un test que solo verifique el contrato de la respuesta NO lo
detecta, porque el fallback produce un `IntentRouterDecision` valido.
"""

import logging

import pytest

from backend.config import settings
from backend.schemas.router_schemas import IntentTrigger
from backend.services.llm_client import llm_client
from backend.services.intent_router import intent_router, route_stats

from tests.conftest import FALLBACK_CONFIDENCES

pytestmark = pytest.mark.live_llm


@pytest.fixture(autouse=True)
def _exigir_llm_real(live_llm_enabled):
    if not live_llm_enabled:
        pytest.skip("Requiere NEXO_TEST_LIVE_LLM=1 y GEMINI_API_KEY configurada")
    if not llm_client.available:
        pytest.skip(f"Proveedor no disponible: {llm_client.init_error}")


async def test_el_router_realmente_consulta_al_llm():
    """
    La asercion clave. `route_stats()['llm_responses']` solo sube si el proveedor
    respondio, y la confianza no debe caer en los valores fijos del fallback.
    """
    decision, latency_ms = await intent_router.route_intent(
        "Por que se frustran los usuarios de Mexico en celular"
    )

    stats = route_stats()
    assert stats["llm_responses"] == 1, "el proveedor no llego a responder"
    assert stats["fallback_responses"] == 0, (
        f"cayo al fallback por {stats['fallback_reasons']}"
    )
    assert decision.confidence_score not in FALLBACK_CONFIDENCES, (
        f"confianza {decision.confidence_score} es un valor fijo del fallback: "
        "el LLM no se uso"
    )


async def test_el_llm_extrae_paises_y_dispositivos():
    """El fallback tambien extrae filtros, asi que hay que mirar la confianza."""
    decision, _ = await intent_router.route_intent(
        "Cuantos usuarios tenemos en Colombia desde el celular"
    )

    assert route_stats()["llm_responses"] == 1
    assert decision.rpc_intent.country_filter == "colombia"
    assert decision.rpc_intent.device_filter == "Mobile"


async def test_el_llm_distingue_insights_de_kpis():
    """Una pregunta causal debe ir al Heavy Path, no al fallback determinista."""
    decision, _ = await intent_router.route_intent(
        "Por que se frustran los usuarios de Mexico en celular"
    )

    assert route_stats()["llm_responses"] == 1
    assert decision.trigger == IntentTrigger.TRIGGER_INSIGHTS
    assert decision.requires_heavy_path is True


async def test_la_latencia_del_router_cabe_en_el_presupuesto(caplog):
    """
    Si esto falla de forma intermitente, el timeout volvio a quedarse corto.
    Se registra la latencia para poder ver la distribucion real del proveedor.
    """
    with caplog.at_level(logging.INFO):
        decision, latency_ms = await intent_router.route_intent(
            "Analiza el comportamiento de los usuarios en Peru"
        )

    assert latency_ms < settings.ROUTER_TIMEOUT_S * 1000
    assert route_stats()["llm_responses"] == 1, (
        f"el router tardo {latency_ms:.0f}ms y cayo al fallback"
    )
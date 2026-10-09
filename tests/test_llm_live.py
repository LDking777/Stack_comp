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
        pytest.skip("Requiere NEXO_TEST_LIVE_LLM=1 y una API key configurada")
    if not llm_client.available:
        pytest.skip(f"Proveedor no disponible: {llm_client.init_error}")


async def test_el_router_realmente_consulta_al_llm():
    """
    La asercion clave. `route_stats()['llm_responses']` solo sube si el proveedor
    respondio, y la confianza no debe caer en los valores fijos del fallback.
    """
    decision, latency_ms = await intent_router.route_intent(
        "Cuantas IPS publicas hay en Antioquia"
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


async def test_el_llm_extrae_filtros_del_dominio():
    """El fallback tambien extrae filtros, asi que hay que mirar la confianza."""
    decision, _ = await intent_router.route_intent(
        "Cuantas camas hay en las IPS publicas de Antioquia"
    )

    assert route_stats()["llm_responses"] == 1
    assert decision.query_intent.departamento_filter == "Antioquia"
    assert decision.query_intent.naturaleza_filter == "Pública"
    assert decision.query_intent.grupo_capacidad_filter == "CAMAS"


async def test_el_llm_distingue_insights_de_kpis():
    """Una pregunta causal debe ir al Heavy Path, no al fallback determinista."""
    decision, _ = await intent_router.route_intent(
        "Por que algunos departamentos concentran la mayoria de la capacidad hospitalaria"
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
            "Analiza la cobertura de IPS en Caldas"
        )

    assert latency_ms < settings.ROUTER_TIMEOUT_S * 1000
    assert route_stats()["llm_responses"] == 1, (
        f"el router tardo {latency_ms:.0f}ms y cayo al fallback"
    )


async def test_el_heavy_path_genera_narrativa_con_el_proveedor():
    """
    El Heavy Path tambien va al LLM con `QualitativeInsightResponse`. Como el
    fallback produce un insight valido (AGENTS.md, trampa 1), la asercion clave
    es que `data_verified` sea True y la narrativa no sea la de `_mock_fallback_insight`.
    """
    from backend.services.insights_service import insights_generator

    kpis = {
        "total_registros": 41427,
        "total_prestadores": 9320,
        "grupos": [
            {"valor": "Antioquia", "registros": 4245},
            {"valor": "Bogotá D.C", "registros": 4647},
        ],
    }
    insight, latency_ms = await insights_generator.generate_insight(
        user_query="Por que algunos departamentos concentran la mayoria de la capacidad hospitalaria",
        kpis=kpis,
        toon_context=(
            "sede:IPS_X|dept:Antioquia|mun:Bogotá D.C|nat:Privada|nivel:2|cap:120\n"
            "sede:Hospital_Y|dept:Antioquia|mun:Medellín|nat:Pública|nivel:3|cap:340"
        ),
    )

    assert latency_ms < settings.INSIGHTS_TIMEOUT_S * 1000
    assert insight.data_verified is True
    assert "Análisis cualitativo generado a partir de las métricas deterministas" not in (
        insight.executive_summary
    ), "cayo a la narrativa de fallback: el LLM no se uso"
    assert insight.observations, "debe haber al menos una observacion"

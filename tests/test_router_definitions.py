"""
Definiciones y preguntas fuera de dominio.

Antes, "¿qué es engagement?" se clasificaba como consulta de KPIs y devolvía
números que no contestaban la pregunta. Ahora se resuelve de forma
determinista: explica el término y guía al usuario. Estas pruebas fijan ese
comportamiento y evitan que vuelva a caer en los KPIs genéricos.
"""

from backend.schemas.router_schemas import IntentRouterDecision, IntentTrigger
from backend.services.intent_router import intent_router

from tests.conftest import FakeLLM


async def test_definicion_conocida_no_consulta_al_llm(patch_llm):
    fake = patch_llm(FakeLLM(available=False))

    decision, _ = await intent_router.route_intent("¿qué es engagement?")

    assert fake.calls == 0, "la definición se resuelve sin gastar una llamada al LLM"
    assert decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION
    assert decision.is_safe is True
    assert "Engagement" in decision.security_reasoning
    assert "Prueba" in decision.security_reasoning


async def test_definicion_desconocida_guia_al_usuario(patch_llm):
    patch_llm(FakeLLM(available=False))

    decision, _ = await intent_router.route_intent("¿qué es CTR?")

    assert decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION
    assert decision.is_safe is True
    assert "No reconozco" in decision.security_reasoning
    assert "engagement" in decision.security_reasoning.lower()


async def test_pregunta_de_analisis_no_se_secuestra(patch_llm):
    """
    "¿qué es lo que más afecta el engagement?" es una consulta de análisis,
    no una definición: debe seguir el flujo normal (LLM).
    """
    fake = patch_llm(
        FakeLLM(
            result=(
                IntentRouterDecision(
                    trigger=IntentTrigger.TRIGGER_INSIGHTS,
                    confidence_score=0.92,
                    rpc_intent={"rpc_name": "rpc_get_engagement_summary"},
                    requires_heavy_path=True,
                ),
                9.0,
            )
        )
    )

    decision, _ = await intent_router.route_intent("¿qué es lo que más afecta el engagement?")

    assert fake.calls == 1, "una pregunta de análisis no debe tratarse como definición"
    assert decision.trigger == IntentTrigger.TRIGGER_INSIGHTS


async def test_clarificacion_fuera_de_dominio_incluye_ejemplos(patch_llm):
    patch_llm(FakeLLM(available=False))

    decision, _ = await intent_router.route_intent("quién ganó el mundial")

    assert decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION
    assert decision.is_safe is True
    assert "rage clicks" in decision.security_reasoning
    assert "frustración" in decision.security_reasoning

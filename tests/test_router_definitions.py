"""
Definiciones, saludos y preguntas fuera de dominio.

Antes, "¿qué es una IPS?" se clasificaba como consulta de KPIs y devolvía
números que no contestaban la pregunta. Ahora se resuelve de forma
determinista: explica el término (glosario) o el alcance del asistente y guía
al usuario, sin gastar una llamada al LLM. Estas pruebas fijan ese
comportamiento.
"""

from backend.schemas.router_schemas import IntentTrigger, QueryOperation
from backend.services.intent_router import intent_router

from tests.conftest import FakeLLM, make_decision


# ============================================================
# GLOSARIO
# ============================================================

async def test_definicion_conocida_no_consulta_al_llm(patch_llm):
    fake = patch_llm(FakeLLM(available=False))

    decision, _ = await intent_router.route_intent("¿qué es una IPS?")

    assert fake.calls == 0, "la definición se resuelve sin gastar una llamada al LLM"
    assert decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION
    assert decision.is_safe is True
    assert "IPS" in decision.security_reasoning
    assert "Prueba" in decision.security_reasoning


async def test_definicion_de_capacidad(patch_llm):
    patch_llm(FakeLLM(available=False))

    decision, _ = await intent_router.route_intent("¿qué es la capacidad instalada?")

    assert decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION
    assert "capacidad instalada" in decision.security_reasoning.lower()


async def test_definicion_desconocida_guia_al_usuario(patch_llm):
    patch_llm(FakeLLM(available=False))

    decision, _ = await intent_router.route_intent("¿qué es el RUAF?")

    assert decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION
    assert decision.is_safe is True
    assert "No reconozco" in decision.security_reasoning
    assert "IPS" in decision.security_reasoning


async def test_pregunta_de_analisis_no_se_secuestra(patch_llm):
    """
    "¿qué es lo que más afecta la cobertura?" es una consulta de análisis,
    no una definición: debe seguir el flujo normal (LLM).
    """
    fake = patch_llm(
        FakeLLM(
            result=(
                make_decision(
                    trigger=IntentTrigger.TRIGGER_INSIGHTS,
                    confidence=0.92,
                    operation=QueryOperation.GROUP_COUNT,
                    group_by="departamento",
                    requires_heavy_path=True,
                ),
                9.0,
            )
        )
    )

    decision, _ = await intent_router.route_intent(
        "¿qué es lo que más afecta la cobertura de IPS?"
    )

    assert fake.calls == 1, "una pregunta de análisis no debe tratarse como definición"
    assert decision.trigger == IntentTrigger.TRIGGER_INSIGHTS


# ============================================================
# SALUDOS Y CAPACIDADES
# ============================================================

async def test_saludo_no_consulta_al_llm(patch_llm):
    fake = patch_llm(FakeLLM(available=False))

    decision, _ = await intent_router.route_intent("hola")

    assert fake.calls == 0
    assert decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION
    assert decision.is_safe is True
    assert "Nexo IA" in decision.security_reasoning


async def test_pregunta_de_capacidades_lista_que_sabe_hacer(patch_llm):
    fake = patch_llm(FakeLLM(available=False))

    decision, _ = await intent_router.route_intent("¿qué puedes hacer?")

    assert fake.calls == 0
    assert "IPS colombianas" in decision.security_reasoning
    assert "Antioquia" in decision.security_reasoning


# ============================================================
# FUERA DE DOMINIO
# ============================================================

async def test_clarificacion_fuera_de_dominio_incluye_ejemplos(patch_llm):
    patch_llm(FakeLLM(available=False))

    decision, _ = await intent_router.route_intent("quién ganó el mundial")

    assert decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION
    assert decision.is_safe is True
    assert "IPS" in decision.security_reasoning
    assert "Antioquia" in decision.security_reasoning

import asyncio
import json
import re
import time
import logging
from typing import Any, Dict, Optional

from contextlib import asynccontextmanager
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.schemas.api_schemas import (
    LiveTokenResponse,
    LiveToolRequest,
    LiveToolResponse,
    QueryRequest,
    QueryResponse,
    LatencyMetrics,
)
from backend.schemas.document_schemas import (
    Citation,
    DocumentListResponse,
    DocumentUploadResponse,
)
from backend.schemas.router_schemas import (
    IntentRouterDecision,
    IntentTrigger,
    QueryIntentParams,
    QueryOperation,
)
from backend.services.intent_router import intent_router, is_conversational, route_stats
from backend.services.datosgov_service import (
    CAPACITY_COLUMN,
    IDENTIFIER_FILTER_COLUMNS,
    OPERATIONS,
    datosgov_service,
)
from backend.services.normalization import (
    DEPARTAMENTO_LOOKUP,
    DESCRIPCION_CAPACIDAD_LOOKUP,
    GRUPO_LOOKUP,
    fold,
)
from backend.services.toon_service import toon_compressor
from backend.services.insights_service import insights_generator
from backend.services.knowledge_service import knowledge_service
from backend.services.llm_client import llm_client
from backend.services.live_token_service import live_token_service
from backend.services.conversation_service import conversation_service
from backend.services.document_service import document_service
from backend.services.embeddings_service import embeddings_service
from backend.services.supabase_service import supabase_service
from backend.services.whatsapp_service import whatsapp_service

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("nexo_fastapi")

# Operación determinista por defecto por trigger, solo cuando el router no
# devolvió una operación concreta.
_DEFAULT_OPERATION_BY_TRIGGER = {
    IntentTrigger.TRIGGER_KPIS: QueryOperation.COUNT_REGISTROS.value,
    IntentTrigger.TRIGGER_INSIGHTS: QueryOperation.GROUP_COUNT.value,
    IntentTrigger.TRIGGER_MATH: QueryOperation.MATH.value,
}
_FACILITY_TERM_RE = re.compile(
    r"\b(?:ips|clinica|hospital|centro de salud|centro medico|prestador(?:es)?)\b"
)
_FACILITY_SEARCH_RE = re.compile(
    r"\b(?:cerca|cercan[oa]s?|busca|buscar|busqueda|localiza|localizar|"
    r"encuentra|encontrar|filtra|filtrar|compara|comparar|lista|listar|"
    r"recomiend[ae]|opciones|necesito|donde puedo ir|a donde puedo ir|"
    r"que lugares|donde hay|listame|muestrame|direccion|donde queda)\b"
)
_FACILITY_IDENTIFIER_SEARCH_RE = re.compile(
    r"\b(?:nit|c[oó]digo(?:\s+de\s+prestador)?|nombre\s+de\s+(?:la\s+)?ips)\b",
    re.IGNORECASE,
)
_FACILITY_SEARCH_RE_ACCENTED = re.compile(
    r"\b(?:d[oó]nde puedo ir|a d[oó]nde puedo ir|"
    r"recomi[eé]nd(?:a|ame|e)|mu[eé]strame)\b",
    re.IGNORECASE,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando Nexo IA sobre datos.gov.co (IPS de Colombia)...")
    logger.info("⚡ Router Fast Path: %s", settings.ROUTER_MODEL)
    logger.info("🧠 Heavy Path Insights: %s", settings.INSIGHTS_MODEL)
    logger.info("🗄️ Fuente de datos: %s", settings.DATOS_GOV_RESOURCE_URL)
    logger.info("📚 Knowledge local: %s", knowledge_service.available)
    logger.info("💾 Persistencia de sesión/documentos en Supabase: %s", supabase_service.available)
    yield
    logger.info("🛑 Deteniendo servicios...")


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Backend de baja latencia con separación estricta: Fast Path (router LLM), "
        "Determinismo (agregación SoQL en datos.gov.co) y Heavy Path (síntesis narrativa + TOON)."
    ),
    version="3.0.0",
    lifespan=lifespan,
)

# 1. Configuración de CORS para Frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_query_spec(decision) -> Dict[str, Any]:
    """
    Traduce la decisión del router al `spec` que entiende datosgov_service.

    Los filtros se canonizan dentro del servicio (normalize_filters), así que
    aquí solo se mapean los nombres del contrato al de las columnas del dataset.
    """
    params = decision.query_intent
    filters = {
        "departamento": params.departamento_filter,
        "municipio": params.municipio_filter,
        "naturaleza": params.naturaleza_filter,
        "num_nivel_atencion": params.nivel_atencion_filter,
        "nom_grupo_capacidad": params.grupo_capacidad_filter,
        "nom_descripcion_capacidad": params.descripcion_capacidad_filter,
    }
    return {
        "operation": params.operation.value,
        "group_by": params.group_by,
        "math_operation": params.math_operation.value if params.math_operation else None,
        "metric": params.target_metric or CAPACITY_COLUMN,
        "filters": {
            **{k: v for k, v in filters.items() if v},
            **{
                column: value
                for column, value in (
                    ("nit_ips", params.nit_filter),
                    ("c_digo_prestador", params.codigo_prestador_filter),
                    ("nombre_prestador", params.nombre_prestador_filter),
                )
                if value
            },
        },
    }


def _is_facility_search_query(query: str) -> bool:
    folded_query = fold(query)
    has_facility = bool(_FACILITY_TERM_RE.search(folded_query))
    has_search_intent = bool(
        _FACILITY_SEARCH_RE.search(folded_query)
        or _FACILITY_SEARCH_RE_ACCENTED.search(query)
        or re.search(r"\bips?\s+en\b", folded_query)
        or re.search(r"\b(?:que|cuales?)\s+(?:ips|clinica|hospital|sedes?)\b", folded_query)
        or _FACILITY_IDENTIFIER_SEARCH_RE.search(query)
    )
    return has_facility and has_search_intent


def _last_user_query(history: str) -> str:
    user_turns = re.findall(r"(?m)^Usuario:\s*(.+)$", history)
    return user_turns[-1].strip() if user_turns else ""


def _is_facility_follow_up(query: str, history: str) -> bool:
    is_follow_up = bool(
        re.search(
            r"\b(?:cual(?:es)?|otra(?:s)?|esas|estos|estas|compar\w*|"
            r"tiene mas|cual me queda|alguna de esas|direcciones?|"
            r"cercan?\w*|mejor(?:es)?)\b",
            fold(query),
        )
    )
    role_headers = re.findall(r"(?m)^(Usuario|Nexo):", history)
    last_assistant = history.rsplit("\nNexo:", 1)[-1] if "\nNexo:" in history else ""
    return (
        is_follow_up
        and bool(role_headers)
        and role_headers[-1] == "Nexo"
        and "Sedes encontradas" in last_assistant
        and bool(_last_user_query(history))
    )


def _facility_capacity_filters(query: str) -> Dict[str, str]:
    folded_query = fold(query)
    filters: Dict[str, str] = {}
    for lookup, field in (
        (DESCRIPCION_CAPACIDAD_LOOKUP, "descripcion_capacidad_filter"),
        (GRUPO_LOOKUP, "grupo_capacidad_filter"),
    ):
        for alias, canonical in sorted(lookup.items(), key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", folded_query):
                filters[field] = canonical
                break
    if re.search(r"\b(publica|publico|estatal|oficial)\b", folded_query):
        filters["naturaleza_filter"] = "Pública"
    elif re.search(r"\b(privada|privado|particular)\b", folded_query):
        filters["naturaleza_filter"] = "Privada"
    elif re.search(r"\bmixta\b", folded_query):
        filters["naturaleza_filter"] = "Mixta"

    if re.search(r"\b(nivel\s*1|primari[oa]|basico)\b", folded_query):
        filters["nivel_atencion_filter"] = "1"
    elif re.search(r"\b(nivel\s*2|secundari[oa])\b", folded_query):
        filters["nivel_atencion_filter"] = "2"
    elif re.search(r"\b(nivel\s*3|terciari[oa]|alto)\b", folded_query):
        filters["nivel_atencion_filter"] = "3"
    return filters


def _facility_identifier_filters(query: str) -> Dict[str, str]:
    filters: Dict[str, str] = {}
    identifier_patterns = (
        ("nit_ips", r"\bnit(?:\s+de\s+(?:la\s+)?ips)?\s*(?:es|:|#)?\s*([\d.\-\s]{6,})"),
        (
            "c_digo_prestador",
            r"\bc[oó]digo(?:\s+de\s+prestador)?\s*(?:es|:|#)?\s*([\d.\-\s]{6,})",
        ),
    )
    for column, pattern in identifier_patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            digits = re.sub(r"\D", "", match.group(1))
            if digits:
                filters[column] = digits

    if not filters:
        name_match = re.search(
            r"\b(?:ips|prestador)\s+(?:cuyo\s+nombre\s+es\s+|"
            r"llamad[oa]\s+|con\s+nombre\s+|de\s+nombre\s+)"
            r"(?:es|:)?\s+(.+?)(?=\s+(?:en|del?|cerca|con|por)\b|$)",
            query,
            re.IGNORECASE,
        ) or re.search(
            r"\bnombre(?:\s+de\s+(?:la\s+)?(?:ips|prestador))?\s*"
            r"(?:es|:)?\s+(.+?)(?=\s+(?:en|del?|cerca|con|por)\b|$)",
            query,
            re.IGNORECASE,
        ) or re.search(
            r"\b(?:ips|prestador|cl[ií]nica|hospital)\s+"
            r"(?!(?:en|del?|cerca|por|con|que|hay|ofrece|ofrezca)\b)"
            r"(.+?)(?=\s+(?:en|del?|cerca|con|por)\b|$)",
            query,
            re.IGNORECASE,
        )
        if name_match:
            name = name_match.group(1).strip(" \t:,-")
            if name and fold(name) not in {"cerca", "por nit", "por codigo"}:
                filters["nombre_prestador"] = name[:160]
    return filters


def _department_mention(query: str) -> Optional[str]:
    folded_query = fold(query)
    for alias, canonical in sorted(
        DEPARTAMENTO_LOOKUP.items(), key=lambda item: len(item[0]), reverse=True
    ):
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", folded_query):
            return canonical
    return None


async def _facility_search_decision(query: str, history: str = ""):
    try:
        municipio, departamento, ambiguous = await datosgov_service.resolve_municipio_mention(query)
    except Exception as exc:
        logger.exception("No se pudo resolver la ubicación de la búsqueda de IPS: %s", exc)
        return None, (
            "No pude consultar el registro público para resolver esa ubicación. "
            "Inténtalo de nuevo en unos momentos."
        )
    if departamento is None:
        departamento = _department_mention(query)

    if not municipio and not departamento and not ambiguous:
        previous_query = _last_user_query(history)
        if previous_query:
            try:
                municipio, departamento, ambiguous = (
                    await datosgov_service.resolve_municipio_mention(previous_query)
                )
            except Exception as exc:
                logger.exception("No se pudo resolver la ubicación recordada de IPS: %s", exc)
                return None, (
                    "No pude consultar el registro público para recuperar la ubicación. "
                    "Inténtalo de nuevo en unos momentos."
                )
            if departamento is None:
                departamento = _department_mention(previous_query)

    if ambiguous:
        return None, (
            "Mencionaste más de un municipio o hay nombres repetidos. "
            "Dime el municipio y, si hace falta, el departamento para ubicar las sedes."
        )
    identifier_filters = _facility_identifier_filters(query)
    if not municipio and not departamento and not identifier_filters:
        return None, (
            "¿En qué municipio o departamento de Colombia estás buscando? "
            "También puedes buscar por nombre, NIT o código. Por ahora puedo "
            "filtrar por municipio; el dataset no trae coordenadas para calcular "
            "distancias o radios."
        )

    schema_filters = {
        "nit_ips": "nit_filter",
        "c_digo_prestador": "codigo_prestador_filter",
        "nombre_prestador": "nombre_prestador_filter",
    }
    filters = {
        schema_filters[column]: value
        for column, value in identifier_filters.items()
    }
    params = QueryIntentParams(
        operation=QueryOperation.LIST_IPS,
        municipio_filter=municipio,
        departamento_filter=departamento,
        **filters,
        **_facility_capacity_filters(query),
    )
    decision = IntentRouterDecision(
        trigger=IntentTrigger.TRIGGER_KPIS,
        confidence_score=1.0,
        query_intent=params,
        requires_heavy_path=False,
        is_safe=True,
    )
    return decision, None


def _format_fast_path(kpis_result: Dict[str, Any]) -> str:
    """Renderiza el resultado determinista en markdown legible."""
    header = "### ⚡ Datos deterministas verificados (Fast Path)\n\n"

    if "establecimientos" in kpis_result:
        establecimientos = kpis_result["establecimientos"]
        if not establecimientos:
            return (
                f"{header}No encontré sedes que coincidan con esos filtros "
                "en el registro público consultado. Puedes probar con otro "
                "municipio o quitar un filtro.\n\n"
                "Fuente: datos.gov.co (REPS), con corte al 21 de noviembre de 2022."
            )

        lineas = []
        for establecimiento in establecimientos:
            nombre = establecimiento.get("nombre") or "Prestador sin nombre publicado"
            sede = establecimiento.get("sede")
            titulo = f"**{nombre}**" + (f" — {sede}" if sede and sede != nombre else "")
            detalles = []
            if establecimiento.get("direccion"):
                detalles.append(establecimiento["direccion"])
            if establecimiento.get("niveles_atencion"):
                niveles = ", ".join(map(str, establecimiento["niveles_atencion"]))
                detalles.append(f"nivel(es) {niveles}")
            if establecimiento.get("naturaleza"):
                detalles.append(", ".join(establecimiento["naturaleza"]))
            capacidades = [
                f"{item.get('tipo') or item.get('grupo')}: {item.get('cantidad')}"
                for item in establecimiento.get("capacidades", [])
                if item.get("cantidad") is not None
            ]
            detail_text = " · ".join(detalles)
            if capacidades:
                detail_text += (" · " if detail_text else "") + "; ".join(capacidades)
            lineas.append(f"- {titulo}" + (f"\n  {detail_text}" if detail_text else ""))

        notice = (
            "\n\nEstas son sedes registradas en REPS; el dataset tiene corte "
            "al 21 de noviembre de 2022. No confirma que hoy estén abiertas, "
            "tengan cupos, acepten tu aseguradora o presten cada servicio. "
            "Confirma directamente antes de desplazarte. La búsqueda por "
            "«cerca» se limita al municipio indicado: la fuente no incluye coordenadas."
        )
        filters = kpis_result.get("filtros_aplicados") or {}
        if {"nom_grupo_capacidad", "nom_descripcion_capacidad"}.intersection(filters):
            notice += (
                "\n\nLas sedes están ordenadas de mayor a menor cantidad "
                "registrada para la capacidad filtrada; esto no mide calidad "
                "ni disponibilidad de citas."
            )
        if kpis_result.get("resultados_limitados") or kpis_result.get("fuente_registros_limitada"):
            notice += "\n\nLa lista puede estar limitada; precisa un tipo de atención o capacidad."
        return (
            f"{header}**Sedes encontradas ({kpis_result.get('total_establecimientos', len(establecimientos))}):**\n"
            + "\n".join(lineas)
            + notice
        )

    if kpis_result.get("status") in {
        "sin_datos",
        "sin_coincidencias",
        "filtro_ambiguo",
    }:
        detalle = kpis_result.get("detalle") or "No obtuve datos para esa consulta."
        return f"{header}{detalle}\n\n✅ **Sin cifras inventadas.**"

    if "total_registros" in kpis_result:
        body = f"**Registros (sedes de IPS):** {kpis_result['total_registros']:,}"
    elif "total_prestadores" in kpis_result:
        body = f"**Prestadores (IPS distintas):** {kpis_result['total_prestadores']:,}"
    elif "total_capacidad" in kpis_result and "grupos" not in kpis_result:
        body = f"**Capacidad instalada total:** {kpis_result['total_capacidad']:,}"
    elif "grupos" in kpis_result:
        valor_key = "capacidad" if "capacidad" in (kpis_result["grupos"][0] if kpis_result["grupos"] else {}) else "registros"
        lineas = [
            f"- **{g.get('valor')}:** {g.get(valor_key, 0):,}"
            for g in kpis_result["grupos"]
        ]
        total = kpis_result.get("total_capacidad")
        encabezado = f"**Desglose por {kpis_result.get('grupo_por')}:**"
        if total is not None:
            encabezado += f" (total {total:,})"
        body = encabezado + "\n" + "\n".join(lineas)
    elif "valores_distintos" in kpis_result:
        body = (
            f"**{kpis_result.get('categoria')}** "
            f"({kpis_result.get('total_valores')} valores):\n"
            f"{kpis_result['valores_distintos']}"
        )
    elif "valor" in kpis_result:
        body = (
            f"**{kpis_result.get('operacion')}** de "
            f"`{kpis_result.get('metrica')}`: {kpis_result['valor']:,}"
        )
    else:
        body = f"```json\n{kpis_result}\n```"

    filtros = kpis_result.get("filtros_aplicados") or {}
    filtro_txt = f"\n\n_Filtros aplicados: {filtros}_" if filtros else ""
    return (
        f"{header}{body}{filtro_txt}\n\n"
        f"✅ **Verificado por datos.gov.co vía SoQL (0% alucinación numérica).**"
    )


def _safe_query_label(
    user_query: str, filters: Dict[str, Any], operation: Optional[str] = None
) -> str:
    if IDENTIFIER_FILTER_COLUMNS.intersection(filters):
        if operation == QueryOperation.LIST_IPS.value:
            return "Búsqueda de sede de IPS por identificador."
        return "Consulta agregada sobre una IPS específica."
    return user_query


def _to_plain_text(markdown: str) -> str:
    """Quita el marcado markdown para que el TTS de Live no lea asteriscos."""
    text = re.sub(r"^#{1,6}\s*", "", markdown, flags=re.MULTILINE)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)
    text = text.replace("_", "")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _empathy_prefix(user_query: str) -> str:
    """Respond empathetically only to explicit self-reported distress."""
    query = fold(user_query)
    if re.search(
        r"\b(?:no\s+(?:estoy|me siento)\s+(?:muy\s+)?"
        r"(?:preocupad[oa]|angustiad[oa]|asustad[oa]|frustrad[oa]))\b",
        query,
    ):
        return ""
    if re.search(
        r"\b(?:estoy|me siento|me encuentro|tengo)\s+(?:muy\s+)?"
        r"(?:preocupad[oa]|angustiad[oa]|asustad[oa]|miedo|con miedo)\b|"
        r"\b(?<!no )me preocupa\b",
        query,
    ):
        return "Entiendo que esta situación puede preocupar. Te ayudo con información clara y sus límites."
    if re.search(
        r"\b(?:estoy|me siento|me encuentro)\s+(?:muy\s+)?frustrad[oa]\b|"
        r"\bno puedo encontrar\b",
        query,
    ):
        return "Entiendo que puede ser frustrante buscar esta información. Vamos paso a paso."
    return ""


def _with_empathy(user_query: str, message: str) -> str:
    prefix = _empathy_prefix(user_query)
    return f"{prefix}\n\n{message}" if prefix else message


async def _document_response(
    user_query: str,
    answer,
    hits,
    session_id: Optional[str],
    total_start: float,
) -> QueryResponse:
    """Empaqueta una respuesta RAG (documentos del usuario) con sus citas."""
    citations = [
        Citation(source=chunk.source, fragmento=chunk.text[:280])
        for chunk, _ in hits[: settings.RAG_TOP_K]
    ]
    formatted = _with_empathy(user_query, (
        "### 📄 Respuesta desde tus documentos (RAG)\n\n"
        f"{answer.respuesta}\n\n"
        "_Fuente: documentos cargados en esta sesión. Las cifras del dataset de IPS "
        "siguen saliendo de datos.gov.co vía SoQL._"
    ))
    total_lat_ms = (time.perf_counter() - total_start) * 1000
    await conversation_service.add_turn(session_id, "user", user_query)
    await conversation_service.add_turn(session_id, "assistant", answer.respuesta)
    return QueryResponse(
        query=user_query,
        trigger=IntentTrigger.TRIGGER_INSIGHTS,
        formatted_message=formatted,
        latency=LatencyMetrics(
            router_latency_ms=0.0,
            datosgov_latency_ms=0.0,
            heavy_path_latency_ms=None,
            total_pipeline_latency_ms=round(total_lat_ms, 2),
        ),
        is_safe=True,
        answer_source="documents",
        citations=citations,
    )


# Motor del pipeline. Lo comparten el endpoint de texto y la herramienta de
# voz: así la conversación Live nunca calcula, siempre narra estas cifras.
async def _execute_query(
    user_query: str,
    session_id: Optional[str] = None,
    use_documents: bool = False,
) -> QueryResponse:
    total_start = time.perf_counter()

    # Contexto de sesión persistido en Supabase. Sin session_id, sigue stateless.
    history_text = await conversation_service.format_history(session_id)
    has_docs = await document_service.has_documents(session_id)
    doc_hits: list = []
    conversational = is_conversational(user_query)

    # Modo documentos explícito (el usuario pidió responder desde sus archivos).
    if has_docs and use_documents and not conversational:
        doc_hits = await document_service.search(session_id, user_query)
        answer, _ = await document_service.answer(user_query, doc_hits, history_text)
        return await _document_response(
            user_query, answer, doc_hits, session_id, total_start
        )

    # --- PASO 1: Router de Intenciones (Fast Path) ---
    facility_search = (
        _is_facility_search_query(user_query)
        or _is_facility_follow_up(user_query, history_text)
    ) and not conversational
    if facility_search:
        decision, clarification = await _facility_search_decision(user_query, history_text)
        router_lat_ms = 0.0
        if clarification:
            clarification = _with_empathy(user_query, clarification)
            await conversation_service.add_turn(session_id, "user", user_query)
            await conversation_service.add_turn(session_id, "assistant", clarification)
            return QueryResponse(
                query=user_query,
                trigger=IntentTrigger.TRIGGER_CLARIFICATION,
                formatted_message=clarification,
                latency=LatencyMetrics(
                    router_latency_ms=0.0,
                    datosgov_latency_ms=0.0,
                    heavy_path_latency_ms=None,
                    total_pipeline_latency_ms=round(
                        (time.perf_counter() - total_start) * 1000, 2
                    ),
                ),
                is_safe=True,
                answer_source="soql",
            )
    else:
        decision, router_lat_ms = await intent_router.route_intent(user_query, history=history_text)

    # Verificación de Seguridad, saludos, definiciones y clarificaciones.
    if not decision.is_safe or decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION:
        # Fuera de dominio pero con documentos relevantes: responde desde ellos.
        if decision.is_safe and has_docs and not conversational:
            doc_hits = await document_service.search(session_id, user_query)
            doc_relevant = bool(doc_hits) and doc_hits[0][1] >= settings.RAG_MIN_SCORE
        else:
            doc_relevant = False
        if decision.is_safe and doc_relevant:
            answer, _ = await document_service.answer(user_query, doc_hits, history_text)
            return await _document_response(
                user_query, answer, doc_hits, session_id, total_start
            )

        mensaje = (
            decision.security_reasoning
            or (
                "Solo puedo analizar datos de IPS colombianas: departamentos, "
                "municipios, naturaleza (pública/privada), niveles de atención y "
                "capacidad instalada. Prueba con: «¿Cuántas IPS hay en Antioquia?» "
                "o «¿Cuántas camas hay en Bogotá D.C?»."
            )
        )
        mensaje = _with_empathy(user_query, mensaje)
        await conversation_service.add_turn(session_id, "user", user_query)
        await conversation_service.add_turn(session_id, "assistant", mensaje)
        total_lat_ms = (time.perf_counter() - total_start) * 1000
        return QueryResponse(
            query=user_query,
            trigger=decision.trigger,
            is_safe=decision.is_safe,
            formatted_message=mensaje,
            latency=LatencyMetrics(
                router_latency_ms=round(router_lat_ms, 2),
                datosgov_latency_ms=0.0,
                heavy_path_latency_ms=None,
                total_pipeline_latency_ms=round(total_lat_ms, 2),
            ),
            answer_source="soql",
        )

    # --- PASO 2: Ejecución Determinista (agregación SoQL en datos.gov.co) ---
    # NUNCA el LLM calcula números; la fuente pública ejecuta las agregaciones.
    spec = _build_query_spec(decision)
    if not spec.get("operation"):
        spec["operation"] = _DEFAULT_OPERATION_BY_TRIGGER.get(
            decision.trigger, QueryOperation.COUNT_REGISTROS.value
        )
    safe_query = _safe_query_label(
        user_query, spec.get("filters") or {}, spec.get("operation")
    )

    datos_start = time.perf_counter()
    kpis_result = await datosgov_service.execute(spec)
    applied_filters = kpis_result.get("filtros_aplicados")
    if isinstance(applied_filters, dict):
        kpis_result["filtros_aplicados"] = {
            key: value
            for key, value in applied_filters.items()
            if key not in IDENTIFIER_FILTER_COLUMNS
        }
    datos_lat_ms = (time.perf_counter() - datos_start) * 1000

    # --- PASO 3 & 4: Evaluación de Ruta (Fast Path vs. Heavy Path) ---
    qualitative_insight = None
    heavy_lat_ms = None

    if decision.requires_heavy_path or decision.trigger == IntentTrigger.TRIGGER_INSIGHTS:
        # Registros operacionales para contexto TOON, acotados a los mismos
        # filtros de la consulta para que el contexto sea relevante.
        raw_records = await datosgov_service.fetch_records(
            limit=10, filters=spec.get("filters")
        )
        toon_context = toon_compressor.compress_records(raw_records)

        # Knowledge propio del asistente. Opcional: si falta el archivo,
        # devuelve contexto vacío y el Heavy Path sigue sin directrices.
        knowledge = await knowledge_service.build_context(safe_query)

        doc_context = document_service.render_fragments(doc_hits) if doc_hits else ""

        qualitative_insight, heavy_lat_ms = await insights_generator.generate_insight(
            user_query=safe_query,
            kpis=kpis_result,
            toon_context=toon_context,
            knowledge=knowledge,
            history=history_text,
            document_context=doc_context,
        )

        obs_text = "\n".join(
            f"- **[{o.impact_level}] {o.area}:** {o.detail} *(Evidencia: {o.evidence_kpi})*"
            for o in qualitative_insight.observations
        )
        recs_text = "\n".join(
            f"{r.priority}. **{r.action}** → *{r.expected_outcome}*"
            for r in qualitative_insight.recommendations
        )

        formatted_message = (
            f"### 📊 Diagnóstico Estratégico NEXO IA (Heavy Path)\n\n"
            f"{qualitative_insight.executive_summary}\n\n"
            f"#### 🔍 Hallazgos Clave:\n{obs_text}\n\n"
            f"#### 💡 Acciones Recomendadas:\n{recs_text}\n\n"
            f"_{qualitative_insight.coverage_and_capacity_analysis}_"
        )
    else:
        formatted_message = _format_fast_path(kpis_result)
    formatted_message = _with_empathy(user_query, formatted_message)

    total_lat_ms = (time.perf_counter() - total_start) * 1000

    await conversation_service.add_turn(session_id, "user", safe_query)
    await conversation_service.add_turn(session_id, "assistant", formatted_message)

    return QueryResponse(
        query=safe_query,
        trigger=decision.trigger,
        verified_deterministic_kpis=kpis_result,
        qualitative_insight=qualitative_insight,
        formatted_message=formatted_message,
        latency=LatencyMetrics(
            router_latency_ms=round(router_lat_ms, 2),
            datosgov_latency_ms=round(datos_lat_ms, 2),
            heavy_path_latency_ms=round(heavy_lat_ms, 2) if heavy_lat_ms else None,
            total_pipeline_latency_ms=round(total_lat_ms, 2),
        ),
        is_safe=True,
        answer_source="soql",
    )


# 2. Endpoint de Consulta Principal (Orquestación del Flujo de Intenciones)
@app.post("/api/v1/query", response_model=QueryResponse, summary="Procesa la consulta del usuario mediante el Flujo de Intenciones")
async def process_user_query(payload: QueryRequest):
    user_query = payload.query.strip()
    if not user_query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La consulta no puede estar vacía.")
    try:
        return await _execute_query(
            user_query, session_id=payload.session_id, use_documents=payload.use_documents
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


# 2b. Voz: credencial efímera para que el navegador abra la sesión de Gemini Live.
@app.post("/api/v1/live/token", response_model=LiveTokenResponse, summary="Mintea una credencial efímera de Gemini Live (la API key no sale del backend)")
async def create_live_token():
    result = await live_token_service.create_token()
    if not result.get("ok"):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result.get("error"))
    return LiveTokenResponse(
        token=result["token"],
        model=result["model"],
        expires_at=result.get("expires_at"),
        new_session_expires_at=result.get("new_session_expires_at"),
    )


# 2c. Voz: herramienta que Gemini Live invoca para obtener cifras verificadas.
#     Reutiliza el pipeline determinista; el modelo solo narra la respuesta.
@app.post("/api/v1/live/tool", response_model=LiveToolResponse, summary="Ejecuta la consulta determinista para la herramienta de Gemini Live")
async def run_live_tool(payload: LiveToolRequest):
    result = await _execute_query(payload.pregunta.strip())
    return LiveToolResponse(
        respuesta=_to_plain_text(result.formatted_message),
        verificado=result.is_safe,
    )


# 2d. Documentos (RAG): el usuario sube PDF/Word; se indexan en memoria por
#     sesión. Las cifras del dataset siguen saliendo de SoQL, no del documento.
@app.post("/api/v1/documents", response_model=DocumentUploadResponse, summary="Sube e indexa un documento (PDF/Word/TXT/MD) para responder preguntas sobre él")
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    filename = file.filename or "documento"
    data = await file.read()
    if not data:
        return DocumentUploadResponse(ok=False, session_id=session_id, error="El archivo está vacío.")
    max_bytes = settings.RAG_MAX_FILE_MB * 1024 * 1024
    if len(data) > max_bytes:
        return DocumentUploadResponse(
            ok=False,
            session_id=session_id,
            error=f"El archivo supera el límite de {settings.RAG_MAX_FILE_MB} MB.",
        )
    try:
        info, total_chunks = await document_service.add_document(session_id, filename, data)
    except ValueError as exc:  # formato no soportado o sin texto extraíble
        logger.warning("Documento rechazado (%s): %s", filename, exc)
        return DocumentUploadResponse(ok=False, session_id=session_id, error=str(exc))
    except RuntimeError as exc:
        logger.error("Dependencia de documentos no disponible para %s: %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error("Error indexando documento %s: %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo indexar el documento; revisa el proveedor de embeddings y Supabase.",
        ) from exc
    if not info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El documento no se pudo indexar.",
        )
    return DocumentUploadResponse(
        ok=True,
        session_id=session_id,
        documento=info,
        total_chunks=total_chunks,
        documentos_sesion=len(await document_service.list_documents(session_id)),
    )


@app.get("/api/v1/documents/{session_id}", response_model=DocumentListResponse, summary="Lista los documentos indexados de una sesión")
async def list_session_documents(session_id: str):
    try:
        documents = await document_service.list_documents(session_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return DocumentListResponse(session_id=session_id, documentos=documents)


@app.delete("/api/v1/documents/{session_id}", summary="Borra los documentos y la memoria de una sesión")
async def delete_session_documents(session_id: str):
    try:
        removed = await document_service.clear(session_id)
        await conversation_service.clear(session_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return {"ok": True, "session_id": session_id, "documentos_eliminados": removed}


@app.delete("/api/v1/sessions/{session_id}/history", summary="Borra solo el historial de conversación de una sesión")
async def delete_session_history(session_id: str):
    try:
        await conversation_service.clear(session_id)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    return {"ok": True, "session_id": session_id}


# 3. Endpoint de Tableros Analíticos (Para alimentar el Dashboard Visual)
@app.get("/api/v1/dashboard", summary="Obtiene métricas agregadas y datos tabulares para el dashboard visual")
async def get_dashboard_data():
    (
        total_registros,
        total_prestadores,
        by_departamento,
        by_naturaleza,
        by_nivel,
        by_capacidad,
        capacity_by_grupo,
        camas,
        recent_records,
    ) = await asyncio.gather(
        datosgov_service.execute({"operation": "count_registros"}),
        datosgov_service.execute({"operation": "count_prestadores"}),
        datosgov_service.execute({"operation": "group_count", "group_by": "departamento", "limit": 40}),
        datosgov_service.execute({"operation": "group_count", "group_by": "naturaleza"}),
        datosgov_service.execute({"operation": "group_count", "group_by": "num_nivel_atencion"}),
        datosgov_service.execute({"operation": "group_count", "group_by": "nom_grupo_capacidad"}),
        datosgov_service.execute({"operation": "sum_capacity", "group_by": "nom_grupo_capacidad", "limit": 10}),
        datosgov_service.execute({
            "operation": "sum_capacity",
            "filters": {"nom_grupo_capacidad": "CAMAS"},
        }),
        datosgov_service.fetch_records(limit=8),
    )

    departamentos = by_departamento.get("grupos", [])
    total_capacidad = sum(
        g.get("capacidad", 0) for g in capacity_by_grupo.get("grupos", [])
    )

    return {
        "kpis": {
            "total_registros": total_registros.get("total_registros", 0),
            "total_prestadores": total_prestadores.get("total_prestadores", 0),
            "total_departamentos": len(departamentos),
            "total_capacidad": total_capacidad,
            "total_camas": camas.get("total_capacidad", 0),
        },
        "by_departamento": departamentos,
        "by_naturaleza": by_naturaleza.get("grupos", []),
        "by_nivel": by_nivel.get("grupos", []),
        "by_capacidad": by_capacidad.get("grupos", []),
        "capacity_by_grupo": capacity_by_grupo.get("grupos", []),
        "recent_records": recent_records,
        "fuente": datosgov_service.dataset_info(),
    }


# ── WhatsApp Cloud API (Meta) ──
@app.get("/api/v1/whatsapp/webhook", summary="Verificación del webhook de WhatsApp")
async def verify_whatsapp_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    if not whatsapp_service.webhook_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El webhook de WhatsApp no está configurado.",
        )

    challenge = whatsapp_service.verify_webhook(
        hub_mode, hub_verify_token, hub_challenge
    )
    if challenge is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verificación de webhook fallida.",
        )
    return Response(content=challenge, media_type="text/plain", status_code=200)


@app.post("/api/v1/whatsapp/webhook", summary="Recepción de mensajes de WhatsApp")
async def receive_whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    if not whatsapp_service.webhook_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El webhook de WhatsApp no está configurado.",
        )

    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if not whatsapp_service.verify_signature(raw_body, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Firma del webhook inválida.",
        )

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cuerpo del webhook no contiene JSON válido.",
        ) from exc

    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El webhook no corresponde a una cuenta de WhatsApp Business.",
        )

    messages = whatsapp_service.extract_messages(payload)
    if not messages:
        return {"status": "ok", "messages_queued": 0}

    async def handle_single_message(message: Dict[str, Any]) -> None:
        message_id = message["message_id"]
        sender_id = message["sender_id"]
        try:
            query_response = await _execute_query(
                user_query=message["text"],
                session_id=f"wa_{sender_id}",
            )
            reply_text = (
                query_response.formatted_message
                or "No se pudo generar respuesta para tu consulta."
            )
        except Exception:
            logger.exception(
                "Error procesando mensaje de WhatsApp (id=%s).", message_id
            )
            reply_text = (
                "Ocurrió un error procesando tu consulta en Nexo IA. "
                "Intenta de nuevo más tarde."
            )

        await whatsapp_service.send_message(sender_id, reply_text)

    for message in messages:
        background_tasks.add_task(handle_single_message, message)

    return {"status": "ok", "messages_queued": len(messages)}


@app.get("/api/v1/whatsapp/config", summary="Configuración pública del canal WhatsApp")
async def get_whatsapp_config():
    return {
        "enabled": whatsapp_service.webhook_configured
        and bool(whatsapp_service.get_public_url()),
        "phone_number": settings.WHATSAPP_PHONE_NUMBER,
        "wa_link": whatsapp_service.get_public_url(),
        "webhook_configured": whatsapp_service.webhook_configured,
    }


# 4. Healthcheck & Diagnóstico
@app.get("/api/v1/health", summary="Verificación de estado de la arquitectura")
async def healthcheck():
    persistence_health = await supabase_service.healthcheck()
    return {
        "status": (
            "online"
            if llm_client.available and persistence_health["ready"]
            else "degraded"
        ),
        "service": settings.APP_NAME,
        "models": {
            "provider": llm_client.provider,
            "fast_path_router": llm_client.router_model(),
            "heavy_path_synthesis": llm_client.insights_model(),
            "router_timeout_s": settings.ROUTER_TIMEOUT_S,
            "insights_timeout_s": settings.INSIGHTS_TIMEOUT_S,
        },
        # Diagnostico de uso real del LLM. Si `fallback_responses` crece, el
        # proveedor esta fallando aunque las respuestas sean correctas.
        "llm_diagnostics": {
            "available": llm_client.available,
            "init_error": llm_client.init_error,
            "routing": route_stats(),
            # Si `failovers` > 0, el primario quedo sin cuota y respondio el secundario.
            "failover": llm_client.failover_stats(),
        },
        "compression": "TOON (python-toon)",
        "fuente_datos": {
            **datosgov_service.dataset_info(),
            "consultas": list(OPERATIONS),
        },
        "mcp": {
            "enabled": settings.MCP_ENABLED,
        },
        "live_voz": {
            "enabled": live_token_service.available,
            "model": settings.GEMINI_LIVE_MODEL,
            "credenciales": "efimeras (auth_tokens, v1alpha; Google Developer API)",
            "nota": "La GEMINI_API_KEY permanece en el backend; el navegador recibe solo el token de corta vida.",
        },
        "whatsapp": {
            "configured": whatsapp_service.webhook_configured,
            "phone_number_configured": bool(settings.WHATSAPP_PHONE_NUMBER),
            "webhook_path": "/api/v1/whatsapp/webhook",
        },
        "documentos_rag": {
            "enabled": embeddings_service.available and persistence_health["ready"],
            "embedding_model": settings.GEMINI_EMBEDDING_MODEL,
            "storage": "Supabase Storage privado" if persistence_health["ready"] else "no disponible",
            "formatos": [".pdf", ".docx", ".txt", ".md"],
            "top_k": settings.RAG_TOP_K,
            "domain_min_score": settings.RAG_DOMAIN_MIN_SCORE,
            "almacenamiento": "Supabase Postgres + pgvector",
        },
        "memoria_conversacion": {
            "max_turnos": settings.CONVERSATION_MAX_TURNS,
            "almacenamiento": "Supabase Postgres" if persistence_health["ready"] else "no disponible",
        },
        "persistencia": {
            **persistence_health,
        },
        "knowledge": {
            "available": knowledge_service.available,
            "archivo": str(knowledge_service.path),
            "note": "Knowledge local del asistente; si falta, el Heavy Path funciona sin directrices.",
        },
    }

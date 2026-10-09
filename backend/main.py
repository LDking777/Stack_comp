import asyncio
import time
import logging
from typing import Any, Dict

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.schemas.api_schemas import QueryRequest, QueryResponse, LatencyMetrics
from backend.schemas.router_schemas import IntentTrigger, QueryOperation
from backend.services.intent_router import intent_router, route_stats
from backend.services.datosgov_service import (
    CAPACITY_COLUMN,
    OPERATIONS,
    datosgov_service,
)
from backend.services.toon_service import toon_compressor
from backend.services.insights_service import insights_generator
from backend.services.knowledge_service import knowledge_service
from backend.services.llm_client import llm_client

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando Nexo IA sobre datos.gov.co (IPS de Colombia)...")
    logger.info("⚡ Router Fast Path: %s", settings.ROUTER_MODEL)
    logger.info("🧠 Heavy Path Insights: %s", settings.INSIGHTS_MODEL)
    logger.info("🗄️ Fuente de datos: %s", settings.DATOS_GOV_RESOURCE_URL)
    logger.info("📚 Knowledge local: %s", knowledge_service.available)
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
    }
    return {
        "operation": params.operation.value,
        "group_by": params.group_by,
        "math_operation": params.math_operation.value if params.math_operation else None,
        "metric": params.target_metric or CAPACITY_COLUMN,
        "filters": {k: v for k, v in filters.items() if v},
    }


def _format_fast_path(kpis_result: Dict[str, Any]) -> str:
    """Renderiza el resultado determinista en markdown legible."""
    header = "### ⚡ Datos deterministas verificados (Fast Path)\n\n"

    if kpis_result.get("status") in {"sin_datos", "sin_coincidencias"}:
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


# 2. Endpoint de Consulta Principal (Orquestación del Flujo de Intenciones)
@app.post("/api/v1/query", response_model=QueryResponse, summary="Procesa la consulta del usuario mediante el Flujo de Intenciones")
async def process_user_query(payload: QueryRequest):
    total_start = time.perf_counter()
    user_query = payload.query.strip()

    if not user_query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La consulta no puede estar vacía.")

    # --- PASO 1: Router de Intenciones (Fast Path) ---
    decision, router_lat_ms = await intent_router.route_intent(user_query)

    # Verificación de Seguridad, saludos, definiciones y clarificaciones.
    if not decision.is_safe or decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION:
        total_lat_ms = (time.perf_counter() - total_start) * 1000
        return QueryResponse(
            query=user_query,
            trigger=decision.trigger,
            is_safe=decision.is_safe,
            formatted_message=(
                decision.security_reasoning
                or (
                    "Solo puedo analizar datos de IPS colombianas: departamentos, "
                    "municipios, naturaleza (pública/privada), niveles de atención y "
                    "capacidad instalada. Prueba con: «¿Cuántas IPS hay en Antioquia?» "
                    "o «¿Cuántas camas hay en Bogotá D.C?»."
                )
            ),
            latency=LatencyMetrics(
                router_latency_ms=round(router_lat_ms, 2),
                datosgov_latency_ms=0.0,
                heavy_path_latency_ms=None,
                total_pipeline_latency_ms=round(total_lat_ms, 2),
            ),
        )

    # --- PASO 2: Ejecución Determinista (agregación SoQL en datos.gov.co) ---
    # NUNCA el LLM calcula números; la fuente pública ejecuta las agregaciones.
    spec = _build_query_spec(decision)
    if not spec.get("operation"):
        spec["operation"] = _DEFAULT_OPERATION_BY_TRIGGER.get(
            decision.trigger, QueryOperation.COUNT_REGISTROS.value
        )

    datos_start = time.perf_counter()
    kpis_result = await datosgov_service.execute(spec)
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
        knowledge = await knowledge_service.build_context(user_query)

        qualitative_insight, heavy_lat_ms = await insights_generator.generate_insight(
            user_query=user_query,
            kpis=kpis_result,
            toon_context=toon_context,
            knowledge=knowledge,
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

    total_lat_ms = (time.perf_counter() - total_start) * 1000

    return QueryResponse(
        query=user_query,
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
    )


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


# 4. Healthcheck & Diagnóstico
@app.get("/api/v1/health", summary="Verificación de estado de la arquitectura")
async def healthcheck():
    return {
        "status": "online" if llm_client.available else "degraded",
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
        "knowledge": {
            "available": knowledge_service.available,
            "archivo": str(knowledge_service.path),
            "note": "Knowledge local del asistente; si falta, el Heavy Path funciona sin directrices.",
        },
    }

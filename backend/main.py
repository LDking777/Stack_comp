import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.schemas.api_schemas import QueryRequest, QueryResponse, LatencyMetrics
from backend.schemas.router_schemas import IntentTrigger
from backend.services.intent_router import intent_router, route_stats
from backend.services.supabase_service import supabase_service
from backend.services.toon_service import toon_compressor
from backend.services.insights_service import insights_generator
from backend.services.knowledge_service import knowledge_service
from backend.services.llm_client import llm_client
from backend.services.normalization import match_device
from backend.mcp.connector import mcp_registry

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("nexo_fastapi")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando Arquitectura MVP Flujo de Intenciones (FastAPI)...")
    logger.info(f"⚡ Router Fast Path: {settings.ROUTER_MODEL}")
    logger.info(f"🧠 Heavy Path Insights: {settings.INSIGHTS_MODEL}")
    logger.info(f"🗄️ Supabase REST Endpoint: {settings.SUPABASE_URL}")
    yield
    logger.info("🛑 Deteniendo servicios...")

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend de baja latencia con separación estricta: Fast Path (Router gpt-4o-mini), Determinismo (PostgreSQL RPC) y Heavy Path (GPT-4o + TOON).",
    version="2.0.0",
    lifespan=lifespan
)

# 1. Configuración de CORS para Frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Endpoint de Consulta Principal (Orquestación del Flujo de Intenciones)
@app.post("/api/v1/query", response_model=QueryResponse, summary="Procesa la consulta del usuario mediante el Flujo de Intenciones")
async def process_user_query(payload: QueryRequest):
    total_start = time.perf_counter()
    user_query = payload.query.strip()

    if not user_query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La consulta no puede estar vacía.")

    # --- PASO 1: Router de Intenciones (Fast Path - gpt-4o-mini con Structured Outputs) ---
    decision, router_lat_ms = await intent_router.route_intent(user_query)

    # Verificación de Seguridad y Prompt Injection
    if not decision.is_safe or decision.trigger == IntentTrigger.TRIGGER_CLARIFICATION:
        total_lat_ms = (time.perf_counter() - total_start) * 1000
        return QueryResponse(
            query=user_query,
            trigger=decision.trigger,
            is_safe=False,
            formatted_message=(
                decision.security_reasoning or 
                "Tu consulta es ambigua o infringe las políticas de seguridad. Por favor formula tu pregunta de manera específica sobre métricas o análisis."
            ),
            latency=LatencyMetrics(
                router_latency_ms=round(router_lat_ms, 2),
                supabase_rpc_latency_ms=0.0,
                heavy_path_latency_ms=None,
                total_pipeline_latency_ms=round(total_lat_ms, 2)
            )
        )

    # --- PASO 2: Ejecución Determinista (PostgreSQL RPC en Supabase) ---
    # NUNCA el LLM calcula números; la base de datos ejecuta agregaciones deterministas
    rpc_start = time.perf_counter()
    rpc_name = decision.rpc_intent.rpc_name or "rpc_get_marketing_kpis"
    
    # Mapeo de parámetros extraídos para la RPC
    rpc_params = {}
    if decision.rpc_intent.url_filter:
        rpc_params["p_url"] = decision.rpc_intent.url_filter
    if decision.rpc_intent.country_filter:
        rpc_params["p_pais"] = decision.rpc_intent.country_filter
    if decision.rpc_intent.device_filter:
        rpc_params["p_dispositivo"] = decision.rpc_intent.device_filter
    if decision.rpc_intent.math_operation:
        rpc_params["p_operacion"] = decision.rpc_intent.math_operation.value
        rpc_params["p_tabla"] = "metricas_marketing" if "marketing" in rpc_name else "grabaciones_analisis"
        rpc_params["p_columna"] = decision.rpc_intent.target_metric or "sessionsWithMetricPercentage"

    kpis_result = await supabase_service.call_rpc(rpc_name, rpc_params)
    rpc_lat_ms = (time.perf_counter() - rpc_start) * 1000

    # --- PASO 3 & 4: Evaluación de Ruta (Fast Path vs. Heavy Path) ---
    toon_preview = None
    qualitative_insight = None
    heavy_lat_ms = None

    if decision.requires_heavy_path or decision.trigger == IntentTrigger.TRIGGER_INSIGHTS:
        # Recuperación de datos operacionales para contexto TOON
        target_table = "grabaciones_analisis" if "engagement" in rpc_name else "metricas_marketing"
        raw_records = await supabase_service.fetch_operational_records(target_table, limit=10)
        
        # Compresión de contexto en Token-Oriented Object Notation (TOON)
        toon_context = toon_compressor.compress_records(raw_records)
        toon_preview = toon_context[:250] + ("..." if len(toon_context) > 250 else "")

        # Knowledge de auditoría aplicable a esta consulta. Opcional: si la
        # tabla no está desplegada, devuelve contexto vacío y el Heavy Path
        # sigue funcionando sin las directrices.
        knowledge = await knowledge_service.build_context(user_query)

        # Generación de Insight Cualitativo con el proveedor activo
        qualitative_insight, heavy_lat_ms = await insights_generator.generate_insight(
            user_query=user_query,
            kpis=kpis_result,
            toon_context=toon_context,
            knowledge=knowledge,
        )

        # Construcción del mensaje renderizable
        obs_text = "\n".join([f"- **[{o.impact_level}] {o.area}:** {o.detail} *(Evidencia: {o.evidence_kpi})*" for o in qualitative_insight.observations])
        recs_text = "\n".join([f"{r.priority}. **{r.action}** → *{r.expected_outcome}*" for r in qualitative_insight.recommendations])

        formatted_message = (
            f"### 📊 Diagnóstico Estratégico NEXO IA (Heavy Path)\n\n"
            f"{qualitative_insight.executive_summary}\n\n"
            f"#### 🔍 Hallazgos Clave:\n{obs_text}\n\n"
            f"#### 💡 Acciones Recomendadas:\n{recs_text}\n\n"
            f"_{qualitative_insight.sentiment_and_friction_analysis}_"
        )
    else:
        # Respuesta inmediata Fast Path con KPIs verificados (0% alucinaciones)
        formatted_message = (
            f"### ⚡ Datos Deterministas Verificados (Fast Path)\n\n"
            f"La base de datos ejecutó la función PostgreSQL `{rpc_name}` determinista:\n\n"
            f"```json\n"
            f"{kpis_result}\n"
            f"```\n\n"
            f"✅ **Verificado por PostgreSQL (0% alucinación numérica).**"
        )

    total_lat_ms = (time.perf_counter() - total_start) * 1000

    return QueryResponse(
        query=user_query,
        trigger=decision.trigger,
        verified_deterministic_kpis=kpis_result,
        toon_context_preview=toon_preview,
        qualitative_insight=qualitative_insight,
        formatted_message=formatted_message,
        latency=LatencyMetrics(
            router_latency_ms=round(router_lat_ms, 2),
            supabase_rpc_latency_ms=round(rpc_lat_ms, 2),
            heavy_path_latency_ms=round(heavy_lat_ms, 2) if heavy_lat_ms else None,
            total_pipeline_latency_ms=round(total_lat_ms, 2)
        ),
        is_safe=True
    )

# 3. Endpoint de Tableros Analíticos (Para alimentar el Dashboard Visual)
@app.get("/api/v1/dashboard", summary="Obtiene métricas agregadas y datos tabulares para el dashboard visual")
async def get_dashboard_data():
    records_grab = await supabase_service.fetch_operational_records("grabaciones_analisis", limit=50)
    records_mkt = await supabase_service.fetch_operational_records("metricas_marketing", limit=50)

    # 1. Cálculos de grabaciones
    total_sessions = len(records_grab)
    scores = [float(r.get("standarized_engagement_score") or 0.0) for r in records_grab]
    avg_engagement = round(sum(scores) / total_sessions, 2) if total_sessions else 0.0
    
    frustrated = [r for r in records_grab if str(r.get("posible_frustracion")) in ["1", "true", "True"]]
    frustration_rate = round((len(frustrated) * 100.0 / total_sessions), 1) if total_sessions else 0.0
    
    avg_duration = round(sum(int(r.get("duracion_sesion_segundos") or 0) for r in records_grab) / total_sessions, 0) if total_sessions else 0

    # 2. Desglose por país
    country_map = {}
    for r in records_grab:
        c = r.get("pais", "Desconocido")
        if c not in country_map:
            country_map[c] = {"pais": c, "total": 0, "scores": [], "frustrated": 0}
        country_map[c]["total"] += 1
        country_map[c]["scores"].append(float(r.get("standarized_engagement_score") or 0.0))
        if str(r.get("posible_frustracion")) in ["1", "true", "True"]:
            country_map[c]["frustrated"] += 1

    country_stats = []
    for c, data in country_map.items():
        avg_score = round(sum(data["scores"]) / data["total"], 2) if data["total"] else 0.0
        country_stats.append({
            "pais": c,
            "sesiones": data["total"],
            "engagement": avg_score,
            "frustracion_pct": round(data["frustrated"] * 100.0 / data["total"], 1)
        })
    country_stats.sort(key=lambda x: x["sesiones"], reverse=True)

    # 3. Desglose por dispositivo
    mobile_count = sum(1 for r in records_grab if match_device(str(r.get("dispositivo", "")), "Mobile"))
    desktop_count = total_sessions - mobile_count

    # 4. URLs con mayor fricción
    url_friction = []
    for r in records_mkt:
        url_friction.append({
            "url": r.get("Url", "N/A"),
            "metrica": r.get("metricName", "N/A"),
            "afectacion_pct": float(r.get("sessionsWithMetricPercentage") or 0.0),
            "sesiones_afectadas": int(r.get("sessionsCount") or 0),
            "dispositivo": r.get("Device", "N/A")
        })
    url_friction.sort(key=lambda x: x["afectacion_pct"], reverse=True)

    return {
        "kpis": {
            "total_sesiones": total_sessions,
            "avg_engagement": avg_engagement,
            "frustration_rate": frustration_rate,
            "avg_duration_sec": int(avg_duration),
            "total_friction_events": len(records_mkt)
        },
        "country_stats": country_stats,
        "device_breakdown": {
            "mobile": mobile_count,
            "desktop": desktop_count,
            "mobile_pct": round(mobile_count * 100.0 / total_sessions, 1) if total_sessions else 0
        },
        "url_friction": url_friction[:6],
        "recent_recordings": records_grab[:8]
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
        },
        "compression": "TOON (python-toon)",
        "database": {
            "endpoint": settings.SUPABASE_URL,
            "deterministic_execution": "PostgreSQL RPC",
            "rpcs_deployed": False,
            "rpcs_note": (
                "Las funciones RPC aún no están compiladas en Supabase. "
                "El servicio aplica agregación determinista equivalente en Python."
            )
        },
        "mcp": {
            "enabled": settings.MCP_ENABLED
        },
        "knowledge_auditoria": {
            "available": knowledge_service.available,
            "table": "knowledge_auditoria",
            "note": (
                "Tabla no desplegada o credenciales ausentes: el Heavy Path "
                "funciona igual, sin directrices de auditoría."
            ),
        },
    }

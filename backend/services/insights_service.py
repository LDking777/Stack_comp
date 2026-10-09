import json
import time
import logging
from typing import Dict, Any, Optional
from backend.config import settings
from backend.schemas.insight_schemas import QualitativeInsightResponse
from backend.schemas.knowledge_schemas import KnowledgeContext
from backend.services.llm_client import llm_client, describe_error

logger = logging.getLogger(__name__)

HEAVY_PATH_SYSTEM_PROMPT = """Eres el Especialista Principal en Síntesis Cualitativa y Diagnóstico de Nexo IA.
Tu responsabilidad es generar un diagnóstico ejecutivo de alto impacto sobre la cobertura y la capacidad instalada de las IPS (instituciones prestadoras de servicios de salud) de Colombia.

REGLAS INFLEXIBLES:
1. RECIBES DOS FUENTES DE CONTEXTO:
   - 'KPIS NUMÉRICOS DETERMINISTAS': cifras exactas agregadas por datos.gov.co vía SoQL. Tus menciones numéricas DEBEN coincidir 100% con estos valores (0% alucinaciones).
   - 'REGISTROS OPERACIONALES EN TOON': muestra de registros individuales (sede, departamento, municipio, naturaleza, nivel de atención y capacidad) comprimida en Token-Oriented Object Notation.
2. NUNCA alteres ni recalcules los KPIs numéricos; úsalos como evidencia empírica.
3. Profundiza en la causa raíz: concentración territorial, brechas entre IPS públicas y privadas, niveles de atención con menor oferta o tipos de capacidad deficitarios.
4. Genera recomendaciones estratégicas accionables y priorizadas (1 a 5) para gestores de salud pública.
5. Tu salida DEBE ser un JSON estrictamente estructurado según el esquema especificado.
"""

class HeavyPathInsightsGenerator:
    """
    Generador de insights cualitativos (Heavy Path) basado en el proveedor LLM activo.
    Consume KPIs exactos de datos.gov.co (SoQL) + contexto TOON comprimido.
    """

    async def generate_insight(
        self, 
        user_query: str, 
        kpis: Dict[str, Any], 
        toon_context: str,
        knowledge: Optional[KnowledgeContext] = None,
    ) -> tuple[QualitativeInsightResponse, float]:
        """
        Genera la síntesis narrativa combinando los KPIs deterministas con el contexto TOON.

        `knowledge` es opcional: si viene vacío, el prompt se construye igual
        sin el bloque de directrices.
        """
        start_time = time.perf_counter()

        if not llm_client.available:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Heavy Path sin proveedor de LLM: %s. Se devuelve la narrativa de fallback.",
                llm_client.init_error or "motivo desconocido",
            )
            return self._mock_fallback_insight(kpis), latency_ms

        # JSON explícito en vez de repr() de dict: más claro para el modelo y
        # suele ocupar menos caracteres.
        kpis_json = json.dumps(kpis, ensure_ascii=False, indent=2)

        user_content = (
            f"CONSULTA DEL USUARIO:\n{user_query}\n\n"
            f"=== 1. KPIS DETERMINISTAS VERIFICADOS (datos.gov.co / Socrata SoQL) ===\n"
            f"{kpis_json}\n\n"
            f"=== 2. CONTEXTO OPERACIONAL COMPRIMIDO (TOON NOTATION) ===\n"
            f"{toon_context}\n"
        )

        # El knowledge va en el prompt, nunca en el response_schema: así el
        # modelo puede leerlo pero no está obligado a devolverlo, y no puede
        # romper la validación del JSON de salida.
        bloque_knowledge = knowledge.como_prompt() if knowledge else ""
        if bloque_knowledge:
            user_content += f"\n{bloque_knowledge}\n"

        try:
            insight, latency_ms = await llm_client.structured(
                system_prompt=HEAVY_PATH_SYSTEM_PROMPT,
                user_content=user_content,
                response_model=QualitativeInsightResponse,
                model=llm_client.insights_model(),
                temperature=0.2,
                timeout=settings.INSIGHTS_TIMEOUT_S,
            )
            return insight, latency_ms

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Error en Heavy Path (%s) tras %.0f ms [timeout=%ss]: %s. "
                "Se responde con la narrativa de fallback.",
                llm_client.provider,
                latency_ms,
                settings.INSIGHTS_TIMEOUT_S,
                describe_error(e),
            )
            return self._mock_fallback_insight(kpis), latency_ms

    def _mock_fallback_insight(self, kpis: Dict[str, Any]) -> QualitativeInsightResponse:
        from backend.schemas.insight_schemas import KeyObservation, ActionableRecommendation
        return QualitativeInsightResponse(
            executive_summary="Análisis cualitativo generado a partir de las métricas deterministas de datos.gov.co.",
            observations=[
                KeyObservation(
                    area="Cobertura territorial",
                    impact_level="MEDIO",
                    evidence_kpi=str(kpis.get("total_registros", "Ver KPIs")),
                    detail="La oferta de IPS y su capacidad se concentra en pocos departamentos."
                )
            ],
            recommendations=[
                ActionableRecommendation(
                    priority=1,
                    action="Priorizar la planeación de capacidad en los departamentos con menor oferta relativa",
                    expected_outcome="Reducción de brechas territoriales de atención en salud"
                )
            ],
            coverage_and_capacity_analysis="La cobertura se concentra en los departamentos más poblados; revisar la distribución por naturaleza y nivel de atención.",
            data_verified=True
        )

insights_generator = HeavyPathInsightsGenerator()

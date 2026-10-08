from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from backend.schemas.router_schemas import IntentTrigger
from backend.schemas.insight_schemas import QualitativeInsightResponse

class QueryRequest(BaseModel):
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=1000, 
        description="Consulta enviada por el usuario desde el frontend React"
    )

class LatencyMetrics(BaseModel):
    router_latency_ms: float = Field(description="Tiempo tomado por el Router gpt-4o-mini en ms")
    supabase_rpc_latency_ms: float = Field(description="Tiempo de ejecución determinista en Supabase RPC en ms")
    heavy_path_latency_ms: Optional[float] = Field(default=None, description="Tiempo de síntesis en GPT-4o si aplicó en ms")
    total_pipeline_latency_ms: float = Field(description="Tiempo total extremo a extremo en ms")

class QueryResponse(BaseModel):
    query: str
    trigger: IntentTrigger
    verified_deterministic_kpis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="KPIs exactos devueltos directamente por PostgreSQL RPC (0% alucinaciones)"
    )
    toon_context_preview: Optional[str] = Field(
        default=None,
        description="Muestra del contexto operacional comprimido en formato TOON"
    )
    qualitative_insight: Optional[QualitativeInsightResponse] = Field(
        default=None,
        description="Síntesis cualitativa generada por GPT-4o (Heavy Path)"
    )
    formatted_message: str = Field(
        description="Mensaje final estructurado listo para ser renderizado en la interfaz React"
    )
    latency: LatencyMetrics
    is_safe: bool = True

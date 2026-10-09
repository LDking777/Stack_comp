from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from backend.schemas.router_schemas import IntentTrigger
from backend.schemas.insight_schemas import QualitativeInsightResponse
from backend.schemas.document_schemas import Citation

class QueryRequest(BaseModel):
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=1000, 
        description="Consulta enviada por el usuario desde el frontend React"
    )
    session_id: Optional[str] = Field(
        default=None,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]{1,64}$",
        description="Identificador de la conversación; habilita memoria multi-turno y RAG de documentos.",
    )
    use_documents: bool = Field(
        default=False,
        description="Fuerza responder desde los documentos subidos (si no, se decide por intención).",
    )

class LatencyMetrics(BaseModel):
    router_latency_ms: float = Field(description="Tiempo tomado por el Router en ms")
    datosgov_latency_ms: float = Field(description="Tiempo de la consulta determinista SoQL a datos.gov.co en ms")
    heavy_path_latency_ms: Optional[float] = Field(default=None, description="Tiempo de sintesis del modelo si aplico, en ms")
    total_pipeline_latency_ms: float = Field(description="Tiempo total extremo a extremo en ms")

class LiveTokenResponse(BaseModel):
    token: str = Field(description="Credencial efímera (auth_tokens/...) que el navegador usa como api key de Live")
    model: str = Field(description="ID del modelo Live habilitado para la sesión")
    expires_at: Optional[str] = Field(default=None, description="Vencimiento de la credencial (ISO-8601)")
    new_session_expires_at: Optional[str] = Field(default=None, description="Plazo para iniciar la sesión (ISO-8601)")


class LiveToolRequest(BaseModel):
    pregunta: str = Field(
        ..., min_length=1, max_length=1000,
        description="Pregunta dictada por el usuario, extraída por Gemini Live",
    )


class LiveToolResponse(BaseModel):
    respuesta: str = Field(description="Respuesta determinista en texto plano para que Live la narre")
    verificado: bool = Field(default=True, description="True: la cifra salió de SoQL, no del LLM")


class QueryResponse(BaseModel):
    query: str
    trigger: IntentTrigger
    verified_deterministic_kpis: Optional[Dict[str, Any]] = Field(
        default=None,
        description="KPIs exactos devueltos por la agregacion SoQL de datos.gov.co (0% alucinaciones)"
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
    answer_source: Optional[str] = Field(
        default=None,
        description="Origen de la respuesta: 'soql' (datos.gov.co), 'documents' (RAG) o 'mixed'.",
    )
    citations: Optional[List[Citation]] = Field(
        default=None,
        description="Fragmentos de documentos usados como evidencia (solo RAG).",
    )

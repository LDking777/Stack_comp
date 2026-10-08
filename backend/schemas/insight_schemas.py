from typing import List, Optional
from pydantic import BaseModel, Field

class KeyObservation(BaseModel):
    area: str = Field(description="Área afectada (ej. 'Checkout Mobile', 'Engagement México')")
    impact_level: str = Field(description="'ALTO', 'MEDIO', o 'BAJO'")
    evidence_kpi: str = Field(description="KPI numérico exacto proveniente de la base de datos que sustenta la observación")
    detail: str = Field(description="Explicación cualitativa del síntoma")

class ActionableRecommendation(BaseModel):
    priority: int = Field(ge=1, le=5, description="Prioridad de ejecución (1 = Más urgente)")
    action: str = Field(description="Acción concreta recomendada")
    expected_outcome: str = Field(description="Resultado esperado tras la acción")

class QualitativeInsightResponse(BaseModel):
    executive_summary: str = Field(
        description="Resumen ejecutivo de alto nivel sintetizando la situación analítica"
    )
    observations: List[KeyObservation] = Field(
        description="Puntos clave observados combinando métricas deterministas y contexto TOON"
    )
    recommendations: List[ActionableRecommendation] = Field(
        description="Recomendaciones estratégicas basadas en la evidencia"
    )
    sentiment_and_friction_analysis: str = Field(
        description="Análisis del nivel de frustración, abandono y engagement del usuario"
    )
    data_verified: bool = Field(
        default=True,
        description="Garantía de que las afirmaciones numéricas concuerdan con la RPC de Supabase"
    )

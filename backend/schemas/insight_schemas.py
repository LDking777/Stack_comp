from typing import List, Optional
from pydantic import BaseModel, Field

class KeyObservation(BaseModel):
    area: str = Field(description="Area o dimension analizada (ej. 'Cobertura en Antioquia', 'Capacidad pública Bogotá')")
    impact_level: str = Field(description="'ALTO', 'MEDIO', o 'BAJO'")
    evidence_kpi: str = Field(description="KPI numerico exacto proveniente de la consulta SoQL que sustenta la observacion")
    detail: str = Field(description="Explicacion cualitativa del hallazgo")

class ActionableRecommendation(BaseModel):
    priority: int = Field(ge=1, le=5, description="Prioridad de ejecucion (1 = Mas urgente)")
    action: str = Field(description="Accion concreta recomendada")
    expected_outcome: str = Field(description="Resultado esperado tras la accion")

class QualitativeInsightResponse(BaseModel):
    executive_summary: str = Field(
        description="Resumen ejecutivo de alto nivel sintetizando la situacion analitica"
    )
    observations: List[KeyObservation] = Field(
        description="Puntos clave observados combinando metricas deterministas y contexto TOON"
    )
    recommendations: List[ActionableRecommendation] = Field(
        description="Recomendaciones estrategicas basadas en la evidencia"
    )
    coverage_and_capacity_analysis: str = Field(
        description="Analisis de la cobertura geografica, la naturaleza publica/privada y los brechas de capacidad instalada"
    )
    data_verified: bool = Field(
        default=True,
        description="Garantia de que las afirmaciones numericas concuerdan con la consulta SoQL de datos.gov.co"
    )

"""
Contratos del knowledge de auditoria del asistente de IPS.

La fuente de verdad es el archivo local `backend/data/knowledge_ips.json`
(conjunto de directrices propio del asistente). Este modulo solo define el
contrato de lo que se lee del archivo.

No existe el concepto de "respuesta fija": una entrada aporta una `directriz`
de analisis, nunca el texto que el usuario recibira. El LLM sigue siendo quien
narra; el knowledge solo acota el analisis.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class KnowledgeCategory(str, Enum):
    """
    Categorias de auditoria. El backend puede pedir solo las categorias que
    interesan a una consulta en vez de inyectar el catalogo completo.
    """

    GENERAL = "general"
    COBERTURA = "cobertura"
    CAPACIDAD = "capacidad"
    GESTION = "gestion"
    CALIDAD_DATOS = "calidad_datos"


class KnowledgeEntry(BaseModel):
    """Una entrada del knowledge de auditoria, ya normalizada."""

    id: int = Field(description="Identificador de la entrada en el archivo de knowledge")
    trigger_key: str = Field(
        description="Ancla de coincidencia, en minúsculas y sin acentos"
    )
    categoria: KnowledgeCategory = Field(
        default=KnowledgeCategory.GENERAL,
        description="Categoría de auditoría de la entrada",
    )
    ambito: str = Field(
        default="GLOBAL",
        description="Ambito geografico de la entrada (departamento). 'GLOBAL' aplica a cualquier consulta.",
    )
    directriz: str = Field(
        description="Qué debe hacer el modelo al aplicar esta entrada. Nunca es la respuesta final."
    )
    criterios_evidencia: Optional[str] = Field(
        default=None,
        description="Criterios de evidencia que el insight debe citar para sostener la conclusión.",
    )
    prioridad: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Peso de prioridad. 1 es máxima; ordena las coincidencias.",
    )


class KnowledgeContext(BaseModel):
    """
    Contexto de knowledge inyectado al prompt del Heavy Path.

    Viaja dentro del `prompt` y no dentro del `response_schema`: el LLM lo lee
    para orientar el análisis, pero no tiene un campo donde devolverlo, así que
    no puede contaminar el JSON validado.
    """

    entradas: List[KnowledgeEntry] = Field(
        default_factory=list, description="Entradas que aplican a la consulta actual"
    )
    consulta: str = Field(default="", description="Consulta original del usuario")

    def como_prompt(self) -> str:
        """
        Renderiza el knowledge como bloque de texto para el prompt.

        Devuelve cadena vacía si no hubo coincidencias, para no gastar tokens en
        un encabezado sin contenido (ver AGENTS.md seccion 4.6).
        """
        if not self.entradas:
            return ""

        lineas = [
            "=== 3. KNOWLEDGE DE AUDITORÍA APLICABLE ===",
            "Directrices metodológicas para esta consulta. Úsalas para interpretar los datos,",
            "no como fuente de cifras: los KPIs siguen siendo la única verdad numérica.",
            "",
        ]
        for entrada in sorted(self.entradas, key=lambda e: e.prioridad):
            etiqueta = f"[{entrada.categoria.value}]" if entrada.categoria else ""
            linea = f"- {etiqueta} {entrada.directriz}".rstrip()
            if entrada.criterios_evidencia:
                linea += f"\n    Evidencia requerida: {entrada.criterios_evidencia}"
            lineas.append(linea)

        return "\n".join(lineas)
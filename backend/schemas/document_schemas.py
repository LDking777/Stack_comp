from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    id: str = Field(description="Identificador interno del documento indexado")
    filename: str = Field(description="Nombre del archivo tal como lo subió el usuario")
    chars: int = Field(description="Caracteres de texto extraídos")
    chunks: int = Field(description="Fragmentos indexados")


class DocumentUploadResponse(BaseModel):
    ok: bool
    session_id: str
    documento: Optional[DocumentInfo] = None
    total_chunks: int = 0
    documentos_sesion: int = 0
    error: Optional[str] = None


class DocumentListResponse(BaseModel):
    session_id: str
    documentos: List[DocumentInfo] = Field(default_factory=list)


class Citation(BaseModel):
    source: str = Field(description="Archivo de origen del fragmento citado")
    fragmento: str = Field(description="Extracto textual usado como evidencia")


class DocumentAnswer(BaseModel):
    respuesta: str = Field(
        description="Respuesta en español basada exclusivamente en los fragmentos de los documentos"
    )
    citas: List[str] = Field(
        default_factory=list,
        description="Archivos citados (nombres de archivo) que sustentan la respuesta",
    )

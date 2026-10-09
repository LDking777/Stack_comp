from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Nexo IA - Analítica de IPS de Colombia (datos.gov.co)"
    APP_ENV: str = "development"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS para Frontend React
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:5000",
        "*"
    ]

    # LLM Provider: "groq" (free tier, 1,000 req/dia), "gemini" o "openai"
    LLM_PROVIDER: str = "groq"

    # Groq API Keys & Models (free tier, sin tarjeta)
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    GROQ_ROUTER_MODEL: str = "openai/gpt-oss-120b"
    GROQ_INSIGHTS_MODEL: str = "openai/gpt-oss-120b"

    # OpenAI API Keys & Models
    OPENAI_API_KEY: str = ""
    ROUTER_MODEL: str = "gpt-4o-mini"
    INSIGHTS_MODEL: str = "gpt-4o"

    # Gemini API Keys & Models
    GEMINI_API_KEY: str = ""
    GEMINI_ROUTER_MODEL: str = "gemini-2.5-flash"
    GEMINI_INSIGHTS_MODEL: str = "gemini-2.5-flash"

    # Supabase: la service-role key solo se usa en el backend y nunca en Vite.
    SUPABASE_URL: str = ""
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "nexo-documents"

    # ── Gemini Live API (voz bidireccional) ──
    # Credenciales efímeras: requieren el SDK `google-genai` (NO el
    # `google-generativeai` deprecado que usa llm_client) y la Gemini
    # Developer API (api key), en `v1alpha`. El nombre del modelo debe ser el
    # vigente y estar habilitado para la cuenta; se deja configurable para no
    # tocar código si Google cambia el ID.
    # IDs documentados actualmente: `gemini-3.8-live` (GA) y
    # `gemini-2.5-flash-native-audio-preview-12-2025` (guías del SDK).
    GEMINI_LIVE_MODEL: str = "gemini-3.8-live"
    GEMINI_LIVE_TOKEN_TTL_MIN: int = 30        # vida del token (default docs)
    GEMINI_LIVE_NEW_SESSION_TTL_MIN: int = 1   # para iniciar la sesión (default docs)

    # ── RAG de documentos (embeddings de Gemini) ──
    # El backend extrae texto/embeddings y persiste documentos en Supabase.
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_EMBEDDING_DIMENSIONS: int = 768
    RAG_TOP_K: int = 4
    RAG_CHUNK_CHARS: int = 900
    RAG_CHUNK_OVERLAP: int = 150
    RAG_MAX_FILE_MB: int = 10
    RAG_MIN_SCORE: float = 0.35
    RAG_DOMAIN_MIN_SCORE: float = 0.30

    # ── Memoria de conversación (persistida en Supabase por sesión) ──
    CONVERSATION_MAX_TURNS: int = 8

    # ── Timeouts del proveedor (segundos) ──
    # El router corre en cada consulta, pero no puede caerse al fallback por
    # latencia: `gemini-2.5-flash` con thinking habilitado oscila entre 1.5s y
    # >20s segun la carga. Un timeout corto aqui solo producia respuestas
    # heuristicas silenciosas.
    ROUTER_TIMEOUT_S: float = 45.0
    INSIGHTS_TIMEOUT_S: float = 90.0
    
    # Fuente de datos publica: datos.gov.co (Socrata SODA / SoQL)
    # Nunca usar api/v3/views/<id>/query.json: ignora $limit y devuelve ~36 MB.
    DATOS_GOV_RESOURCE_URL: str = "https://www.datos.gov.co/resource/s2ru-bqt6.json"

    # ── WhatsApp Cloud API (Meta) ──
    WHATSAPP_ENABLED: bool = True
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_PHONE_NUMBER: str = ""
    WHATSAPP_API_VERSION: str = "v21.0"

    # Model Context Protocol (MCP) Config
    MCP_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

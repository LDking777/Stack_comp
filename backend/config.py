from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Nexo IA - Arquitectura MVP Flujo de Intenciones"
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

    # ── Timeouts del proveedor (segundos) ──
    # El router corre en cada consulta, pero no puede caerse al fallback por
    # latencia: `gemini-2.5-flash` con thinking habilitado oscila entre 1.5s y
    # >20s segun la carga. Un timeout corto aqui solo producia respuestas
    # heuristicas silenciosas.
    ROUTER_TIMEOUT_S: float = 45.0
    INSIGHTS_TIMEOUT_S: float = 90.0
    
    # Supabase Credentials
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""

    # Model Context Protocol (MCP) Config
    MCP_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

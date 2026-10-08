import json
import time
import logging
from typing import Any, Type

from pydantic import BaseModel

from backend.config import settings

logger = logging.getLogger(__name__)

_RETRY_POLICY = {"max_retries": 0}


_GEMINI_ALLOWED = {
    "type",
    "format",
    "description",
    "enum",
    "items",
    "properties",
    "required",
    "anyOf",
    "propertyOrdering",
    "nullable",
}

_NULL_TYPE = "null"


def describe_error(exc: BaseException) -> str:
    """
    Renderiza una excepción de proveedor de forma diagnosable.

    `asyncio.TimeoutError` tiene `str()` vacío, así que un log con solo `{e}`
    imprimía "Error en el Intent Router (gemini):" sin explicar nada. Se
    incluye el tipo y, si existe, el detalle.
    """
    detail = str(exc).strip()
    if not detail:
        return type(exc).__name__
    return f"{type(exc).__name__}: {detail}"


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Traduce un JSON Schema de Pydantic al subconjunto que acepta Gemini.

    Gemini implementa solo una parte del OpenAPI Schema y rechaza el resto con
    `Unknown field for Schema`. Pydantic emite palabras clave que no admite
    (`$defs`, `title`, `additionalProperties`, `minimum`, `maximum`, `default`),
    así que en lugar de ir descartando errores de uno en uno se reconstruye el
    esquema conservando únicamente las claves permitidas.
    """
    defs = schema.get("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/$defs/"):
                return resolve(defs.get(ref.split("/")[-1], {}))
            return {k: resolve(v) for k, v in node.items() if k != "$ref"}
        if isinstance(node, list):
            return [resolve(item) for item in node]
        return node

    def build(node: Any) -> Any:
        if not isinstance(node, dict):
            return node

        # Colapsar anyOf con un único tipo no nulo: Gemini lo acepta, pero
        # simplifica el esquema y reduce rechazos en la validación.
        alternatives = node.get("anyOf")
        if isinstance(alternatives, list):
            non_null = [a for a in alternatives if resolve(a).get("type") != _NULL_TYPE]
            if len(non_null) == 1:
                node = {**resolve(non_null[0]), **{k: v for k, v in node.items() if k == "description"}}

        out: dict[str, Any] = {}
        for key, value in node.items():
            if key not in _GEMINI_ALLOWED:
                continue
            if key == "properties" and isinstance(value, dict):
                out[key] = {name: build(sub) for name, sub in value.items()}
            elif key == "items":
                out[key] = build(value)
            elif key in ("required", "enum", "propertyOrdering"):
                out[key] = value
            elif key == "anyOf":
                out[key] = [build(a) for a in value]
            else:
                out[key] = value
        return out

    return build(resolve(schema))


class LLMClient:
    """
    Cliente LLM intercambiable entre Gemini y OpenAI.

    Ambos proveedores devuelven un dict ya parseado y validado contra el
    modelo Pydantic solicitado, de modo que los servicios callers no saben
    cuál proveedor está activo.
    """

    def __init__(self):
        self.provider = (settings.LLM_PROVIDER or "gemini").strip().lower()
        self._gemini = None
        self._openai = None
        self._init_error: str | None = None
        self._init()

    def _init(self) -> None:
        try:
            if self.provider == "gemini":
                if not settings.GEMINI_API_KEY:
                    raise RuntimeError("GEMINI_API_KEY no configurada en .env")
                import google.generativeai as genai

                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._gemini = genai.GenerativeModel(
                    settings.GEMINI_ROUTER_MODEL,
                    generation_config={
                        "temperature": 0.0,
                        "response_mime_type": "application/json",
                    },
                )
            else:
                if not settings.OPENAI_API_KEY:
                    raise RuntimeError("OPENAI_API_KEY no configurada en .env")
                from openai import AsyncOpenAI

                self._openai = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY, **_RETRY_POLICY
                )
        except Exception as exc:
            self._init_error = str(exc)
            logger.error(
                f"No se pudo inicializar el proveedor '{self.provider}': {exc}. "
                "Los servicios usarán su fallback determinista."
            )

    @property
    def available(self) -> bool:
        return self._init_error is None

    @property
    def init_error(self) -> str | None:
        """Motivo de la ultima falla de inicializacion, si la hubo."""
        return self._init_error

    def router_model(self) -> str:
        if self.provider == "gemini":
            return settings.GEMINI_ROUTER_MODEL
        return settings.ROUTER_MODEL

    def insights_model(self) -> str:
        if self.provider == "gemini":
            return settings.GEMINI_INSIGHTS_MODEL
        return settings.INSIGHTS_MODEL

    async def structured(
        self,
        system_prompt: str,
        user_content: str,
        response_model: Type[BaseModel],
        model: str,
        temperature: float = 0.0,
        timeout: float = 30.0,
    ) -> tuple[BaseModel, float]:
        """
        Genera una respuesta estructurada validada contra `response_model`.
        Lanza excepción si el proveedor falla o devuelve JSON inválido.
        """
        if not self.available:
            raise RuntimeError(self._init_error or "LLM no disponible")

        if self.provider == "gemini":
            return await self._structured_gemini(
                system_prompt, user_content, response_model, model, temperature, timeout
            )
        return await self._structured_openai(
            system_prompt, user_content, response_model, model, temperature, timeout
        )

    async def _structured_gemini(
        self,
        system_prompt: str,
        user_content: str,
        response_model: Type[BaseModel],
        model: str,
        temperature: float,
        timeout: float,
    ) -> tuple[BaseModel, float]:
        import asyncio
        import google.generativeai as genai

        schema = inline_refs(response_model.model_json_schema())
        prompt = f"{system_prompt}\n\n---\n{user_content}"
        start = time.perf_counter()

        def call():
            engine = genai.GenerativeModel(
                model,
                generation_config={
                    "temperature": temperature,
                    "response_mime_type": "application/json",
                    "response_schema": schema,
                },
            )
            return engine.generate_content(prompt)

        raw = await asyncio.wait_for(asyncio.to_thread(call), timeout=timeout)
        latency_ms = (time.perf_counter() - start) * 1000

        text = getattr(raw, "text", None)
        if not text:
            raise ValueError("Gemini devolvió una respuesta vacía")
        return response_model.model_validate(json.loads(text)), latency_ms

    async def _structured_openai(
        self,
        system_prompt: str,
        user_content: str,
        response_model: Type[BaseModel],
        model: str,
        temperature: float,
        timeout: float,
    ) -> tuple[BaseModel, float]:
        start = time.perf_counter()
        completion = await self._openai.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format=response_model,
            temperature=temperature,
            timeout=timeout,
            **_RETRY_POLICY,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("OpenAI devolvió una respuesta sin parsear")
        return parsed, latency_ms


llm_client = LLMClient()
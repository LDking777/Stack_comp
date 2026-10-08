import json
import time
import asyncio
import logging
from typing import Any, Type

from pydantic import BaseModel

from backend.config import settings

logger = logging.getLogger(__name__)

_RETRY_POLICY = {"max_retries": 0}

# Fallos reintentables: cuota agotada (429) y cortes de red transitorios.
# El router caia al fallback heuristico la mitad de las veces sin esto
# (AGENTS.md, trampa 1).
_RETRYABLE_MARKERS = (
    "ResourceExhausted",
    "RESOURCE_EXHAUSTED",
    "429",
    "rate limit",
    "RateLimit",
    "rate_limit",
    "quota",
    "APIConnectionError",
    "Connection error",
)


def _is_retryable(exc: BaseException) -> bool:
    """Detecta si un fallo del proveedor es transitorio y reintentable."""
    rendered = f"{type(exc).__name__}: {exc}"
    return any(marker in rendered for marker in _RETRYABLE_MARKERS)


_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (5.0, 15.0)


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


def strict_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Traduce un JSON Schema de Pydantic al modo estricto de OpenAI/Groq.

    El modo estricto de OpenAI y Groq exige: `additionalProperties: false` en
    todo objeto y `required` con TODAS las claves. Pydantic omite lo primero y
    solo marca requerido lo no-nulo, así que ambos proveedores rechazan el
    esquema crudo: Groq con `required is required to be supplied...including
    every key in properties` y OpenAI con `additionalProperties` ausente.
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
        if isinstance(node, list):
            return [build(item) for item in node]
        if not isinstance(node, dict):
            return node
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key in ("title", "default"):
                continue
            out[key] = build(value)
        if out.get("type") == "object" and "properties" in out:
            out["additionalProperties"] = False
            out["required"] = list(out["properties"].keys())
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
        self.provider = (settings.LLM_PROVIDER or "groq").strip().lower()
        self._gemini = None
        self._openai = None
        self._groq = None
        self._init_error: str | None = None
        self._failover_stats = {"failovers": 0, "last_reason": None}
        self._init()

    def _init(self) -> None:
        """
        Inicializa los tres proveedores cuyas claves existan.

        El primario sale de LLM_PROVIDER, pero los demas quedan listos para el
        failover: si la cuota del primario se agota (Gemini free tier son 20
        consultas/dia, Groq 1.000) se intenta el siguiente antes de caer a la
        heuristica determinista.
        """
        errors = []

        try:
            if settings.GROQ_API_KEY:
                from openai import AsyncOpenAI

                self._groq = AsyncOpenAI(
                    api_key=settings.GROQ_API_KEY,
                    base_url=settings.GROQ_BASE_URL,
                    **_RETRY_POLICY,
                )
            else:
                errors.append("GROQ_API_KEY no configurada en .env")
        except Exception as exc:
            errors.append(f"Groq: {exc}")

        try:
            if settings.GEMINI_API_KEY:
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
                errors.append("GEMINI_API_KEY no configurada en .env")
        except Exception as exc:
            errors.append(f"Gemini: {exc}")

        try:
            if settings.OPENAI_API_KEY:
                from openai import AsyncOpenAI

                self._openai = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY, **_RETRY_POLICY
                )
            else:
                errors.append("OPENAI_API_KEY no configurada en .env")
        except Exception as exc:
            errors.append(f"OpenAI: {exc}")

        if self._gemini is None and self._openai is None and self._groq is None:
            self._init_error = "; ".join(errors) or "Ningun proveedor configurado"
            logger.error(
                f"No se pudo inicializar ningun proveedor LLM: {self._init_error}. "
                "Los servicios usaran su fallback determinista."
            )
        elif errors:
            # Un proveedor caido no degrada el servicio: queda el otro.
            logger.warning(
                "Proveedor LLM secundario no disponible (sigue el primario): %s",
                "; ".join(errors),
            )

    @property
    def available(self) -> bool:
        return self._init_error is None

    @property
    def init_error(self) -> str | None:
        """Motivo de la ultima falla de inicializacion, si la hubo."""
        return self._init_error

    def failover_stats(self) -> dict:
        """Veces que se uso el proveedor secundario por cuota agotada."""
        return dict(self._failover_stats)

    def router_model(self) -> str:
        if self.provider == "groq":
            return settings.GROQ_ROUTER_MODEL
        if self.provider == "gemini":
            return settings.GEMINI_ROUTER_MODEL
        return settings.ROUTER_MODEL

    def insights_model(self) -> str:
        if self.provider == "groq":
            return settings.GROQ_INSIGHTS_MODEL
        if self.provider == "gemini":
            return settings.GEMINI_INSIGHTS_MODEL
        return settings.INSIGHTS_MODEL

    def _client_for(self, provider: str):
        if provider == "groq":
            return self._groq
        return self._gemini if provider == "gemini" else self._openai

    def _model_for(self, provider: str, is_router: bool) -> str:
        if provider == "groq":
            return settings.GROQ_ROUTER_MODEL if is_router else settings.GROQ_INSIGHTS_MODEL
        if provider == "gemini":
            return settings.GEMINI_ROUTER_MODEL if is_router else settings.GEMINI_INSIGHTS_MODEL
        return settings.ROUTER_MODEL if is_router else settings.INSIGHTS_MODEL

    def _provider_chain(self) -> list[str]:
        """Primario primero, el resto despues; solo los inicializados."""
        all_providers = ["groq", "gemini", "openai"]
        primary = self.provider if self.provider in all_providers else "groq"
        order = [primary] + [p for p in all_providers if p != primary]
        return [p for p in order if self._client_for(p) is not None]

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

        Recorre la cadena de proveedores: si el primario falla por cuota
        agotada o red, se intenta el siguiente con el tiempo restante. `model`
        es el modelo del proveedor primario; para los demas se resuelve el
        equivalente.
        """
        if not self.available:
            raise RuntimeError(self._init_error or "LLM no disponible")

        chain = self._provider_chain()
        if not chain:
            raise RuntimeError(self._init_error or "Ningun proveedor LLM inicializado")

        is_router = model in (
            settings.GROQ_ROUTER_MODEL,
            settings.GEMINI_ROUTER_MODEL,
            settings.ROUTER_MODEL,
        )
        total_start = time.perf_counter()
        deadline = total_start + timeout
        last_exc: Exception | None = None

        for index, provider in enumerate(chain):
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break
            resolved_model = model if provider == self.provider else self._model_for(provider, is_router)
            try:
                if provider == "gemini":
                    result, _ = await self._structured_gemini(
                        system_prompt, user_content, response_model, resolved_model, temperature, remaining
                    )
                else:
                    # Groq expone una API compatible con OpenAI: reutiliza el
                    # mismo camino con su propio cliente.
                    result, _ = await self._structured_openai(
                        system_prompt, user_content, response_model, resolved_model,
                        temperature, remaining, client=self._client_for(provider),
                    )
                if index > 0:
                    self._failover_stats["failovers"] += 1
                    logger.info(
                        "Failover activo: el proveedor primario (%s) no respondio "
                        "y la respuesta la dio %s.", chain[0], provider,
                    )
                return result, (time.perf_counter() - total_start) * 1000
            except Exception as exc:
                last_exc = exc
                if index < len(chain) - 1 and _is_retryable(exc):
                    self._failover_stats["last_reason"] = describe_error(exc)
                    logger.warning(
                        "Proveedor (%s) fallo con error transitorio; se intenta %s. %s",
                        provider,
                        chain[index + 1],
                        describe_error(exc),
                    )
                    continue
                raise

        raise last_exc if last_exc else asyncio.TimeoutError()

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
        deadline = start + timeout

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

        # Reintenta solo ante rate limit (429), dentro del mismo presupuesto de
        # timeout. Un timeout real no se reintenta: lo reporta el caller.
        attempt = 0
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            try:
                raw = await asyncio.wait_for(asyncio.to_thread(call), timeout=remaining)
                break
            except Exception as exc:
                attempt += 1
                if attempt >= _MAX_ATTEMPTS or not _is_retryable(exc):
                    raise
                backoff = _BACKOFF_SECONDS[min(attempt - 1, len(_BACKOFF_SECONDS) - 1)]
                if time.perf_counter() + backoff >= deadline:
                    raise
                logger.warning(
                    "Gemini rechazo la peticion por cuota agotada; reintento %s/%s en %.1fs: %s",
                    attempt,
                    _MAX_ATTEMPTS - 1,
                    backoff,
                    describe_error(exc),
                )
                await asyncio.sleep(backoff)

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
        client=None,
    ) -> tuple[BaseModel, float]:
        """
        Camino compatible con OpenAI (OpenAI y Groq).

        Ambos exigen el modo estricto para `response_format` (Groq devuelve un
        400 si el esquema de Pydantic llega crudo), así que se transforma con
        `strict_refs()` y la respuesta se valida aquí en lugar de depender del
        parseo del SDK.

        Reintenta solo ante fallos transitorios (429, red) dentro del mismo
        presupuesto de timeout; un timeout real no se reintenta.
        """
        active = client or self._openai
        strict_schema = strict_refs(response_model.model_json_schema())
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__,
                "schema": strict_schema,
                "strict": True,
            },
        }
        start = time.perf_counter()
        deadline = start + timeout
        attempt = 0

        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                raise asyncio.TimeoutError()
            try:
                completion = await asyncio.wait_for(
                    active.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content},
                        ],
                        response_format=response_format,
                        temperature=temperature,
                        timeout=remaining,
                    ),
                    timeout=remaining,
                )
                break
            except Exception as exc:
                attempt += 1
                if attempt >= _MAX_ATTEMPTS or not _is_retryable(exc):
                    raise
                backoff = _BACKOFF_SECONDS[min(attempt - 1, len(_BACKOFF_SECONDS) - 1)]
                if time.perf_counter() + backoff >= deadline:
                    raise
                logger.warning(
                    "%s rechazo la peticion por cuota agotada o red; "
                    "reintento %s/%s en %.1fs: %s",
                    model,
                    attempt,
                    _MAX_ATTEMPTS - 1,
                    backoff,
                    describe_error(exc),
                )
                await asyncio.sleep(backoff)

        latency_ms = (time.perf_counter() - start) * 1000
        content = completion.choices[0].message.content
        if not content:
            raise ValueError("El proveedor devolvió una respuesta vacía")
        return response_model.model_validate_json(content), latency_ms


llm_client = LLMClient()
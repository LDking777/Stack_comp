# AGENTS.md — Guía de trabajo para Nexo IA

Lee este archivo antes de tocar código. Está escrito para que un agente nuevo pueda orientarse sin antes leer todo el repositorio.

---

## 1. Qué es este proyecto

Nexo IA es un asistente de Business Intelligence para usuarios de ventas. El usuario hace preguntas en lenguaje natural ("¿por qué se frustran los usuarios de México?") y recibe una respuesta con cifras verificadas y una interpretación narrativa.

No es un chat de propósito general. El dominio es analítica de sesiones de usuario: métricas de marketing, engagement, contenido de páginas y eventos de fricción.

### El invariante central

**El LLM nunca calcula números.** PostgreSQL agrega; el LLM solo narra.

Si alguna vez modificas este diseño, cualquier ruta que haga que el modelo estime, infiera o "aproxime" un KPI es un bug, no una mejora. Los numeros exactos vienen de la base de datos o del fallback determinista, nunca del prompt.

### Segundo invariante

Los cálculos deterministas y la síntesis cualitativa son capas separadas. El router decide cuál se ejecuta; no se mezclan los resultados.

---

## 2. Mapa del repositorio

```
api-service-v2/
├── backend/                    # API FastAPI (todo el análisis)
│   ├── main.py                 # Endpoints y orquestación del pipeline
│   ├── config.py               # Settings desde .env (Pydantic)
│   ├── mcp/connector.py        # Registro de conectores MCP
│   ├── schemas/                # Contratos Pydantic (router, insights, API)
│   │   ├── router_schemas.py   # IntentRouterDecision, RPCIntentParams, IntentTrigger
│   │   ├── insight_schemas.py  # QualitativeInsightResponse
│   │   └── api_schemas.py      # QueryRequest, QueryResponse, HealthResponse
│   └── services/               # Lógica de negocio (aqui vive el 90% del trabajo)
│       ├── intent_router.py    # Fast Path: query -> trigger + filtros + RPC
│       ├── supabase_service.py # RPC + fallback determinista en Python
│       ├── toon_service.py     # Compresion TOON del contexto
│       ├── insights_service.py # Heavy Path: KPIs -> narrativa
│       ├── llm_client.py       # Abstraccion Gemini/OpenAI + adaptacion de esquemas
│       └── normalization.py    # Paises y dispositivos (acentos, alias)
├── frontend/                   # React + Vite
│   └── src/
│       ├── App.jsx             # Composicion tablero + burbuja + panel
│       ├── api.js              # Cliente HTTP
│       └── components/
│           ├── BIDashboard.jsx     # KPIs, paises, dispositivos, friccion
│           ├── ChatPanel.jsx       # Burbuja flotante + panel lateral
│           └── AnswerCard.jsx      # Render de respuestas estructuradas
├── supabase/migrations/        # SQL. Solo existe la migracion inicial de tablas
├── docs/                       # Documentacion tecnica
├── legacy/                     # v1 Flask (app.py, telegram_bot.py, ai_clients.py)
├── ARQUITECTURA_FLUJO_INTENCIONES.md   # Arquitectura, estado real, bitacora
├── opencode.json               # Config de opencode (MCP de Supabase)
└── .env                        # Secretos locales. Gitignored. Nunca commitear
```

---

## 3. Dónde seguir una consulta

Este es el recorrido de `POST /api/v1/query`. Si buscas un comportamiento, este es el orden.

1. `backend/main.py` — orquestacion. Decide modo fast vs heavy.
2. `backend/services/intent_router.py` — clasifica y extrae filtros.
3. `backend/services/supabase_service.py` — ejecuta RPC o fallback.
4. `backend/services/insights_service.py` — genera narrativa (solo heavy).
5. `backend/schemas/` — el contrato de lo que sale por cada lado.

Para el tablero, entra directo en `backend/main.py` (`GET /api/v1/dashboard`) y salta a `supabase_service.fetch_operational_records()`.

---

## 4. Donde buscar para optimizar tokens

Si la tarea es reducir consumo de tokens, empieza aqui y en este orden de impacto.

### 4.1. El limite de registros — mayor palanca

`backend/main.py` llama a `supabase_service.fetch_operational_records(tabla, limit=10)`. Ese `10` multiplica directamente el costo del Heavy Path: los tres bloques de contexto que se comprimen a TOON. Bajarlo a 5 reduce a la mitad el contexto, con perdida de detalle. Subirlo sube el costo de forma lineal.

### 4.2. La compresion TOON

`backend/services/toon_service.py`. Ya entrega -53% a -60% frente a JSON. Si buscas mas, el lugar correcto es aqui, no en los prompts.

### 4.3. Los prompts del sistema

`ROUTER_SYSTEM_PROMPT` en `intent_router.py` (~570 tokens) se envia **completo en todas las consultas**. `HEAVY_PATH_SYSTEM_PROMPT` en `insights_service.py` (~254 tokens) solo en heavy path.

El router es determinista y de bajo riesgo, asi que es el candidato natural a prompt mas corto: buena parte de sus reglas pueden pasar al esquema Pydantic, donde no se repiten por llamada.

### 4.4. Serializacion de KPIs

`insights_service.py` construye el contexto con `f"{kpis}"`, que produce la `repr()` de un dict de Python. No es JSON y es mas verboso. Usar `json.dumps` mejora la claridad para el modelo y suele reducir caracteres.

### 4.5. Campos muertos en la respuesta

`QueryResponse` sigue enviando `toon_context_preview` (~250 chars), `trigger`, `confidence_score` y `latency`. El frontend ya no lee ninguno: la UX los ocultó a proposito. `toon_context_preview` es el unico con costo apreciable y se calcula sin consumidor. No ahorra tokens de LLM, pero reduce ancho de banda.

### 4.6. Lo que NO debes optimizar

Los KPIs deterministas. Son la fuente de verdad. Recortarlos para ahorrar tokens degrada el insight sin beneficio. Y `contenido_paginas` devuelve 0 filas: cualquier contexto que se le anada hoy es costo sin informacion.

---

## 5. Comandos para trabajar

```powershell
# Backend
.\venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing

# Frontend
cd frontend; npm run dev

# Verificar que un cambio no rompio las importaciones
.\venv\Scripts\python.exe -c "import backend.main"
```

Endpoint de consulta rapida:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/query" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"Analiza los usuarios de Mexico en celular"}'
```

`GET /api/v1/health` expone `provider`, los modelos efectivos y `rpcs_deployed`. Si `rpcs_deployed` es `false`, los numeros vienen del fallback de Python, no de PostgreSQL.

---

## 6. Trampas conocidas

Estas cosas fallan **en silencio**. Un cambio puede romper el sistema sin que ninguna prueba falle, porque el fallback determinista siempre responde.

1. **El fallback tapa los fallos del LLM.** Si Gemini devuelve algo invalido, el sistema responde igual con reglas heuristicas. Solo se nota en los logs (`Error en el Intent Router`). Al probar, revisa el log: una respuesta correcta no prueba que el LLM se haya usado.
2. **Confianza alta no significa LLM.** `_heuristic_fallback` asigna confianzas fijas (0.85, 0.88, 0.90). El LLM produce valores como 0.88-0.95. Si ves 0.85 o 0.90 exactos, sospecha fallback.
3. **Gemini rechaza esquemas Pydantic.** Acepta solo un subconjunto de OpenAPI Schema. `title`, `$defs`, `minimum`, `maximum` y `additionalProperties` producen `Unknown field for Schema`. Cualquier campo nuevo agregado a un esquema Pydantic puede romper la llamada. `inline_refs()` en `llm_client.py` lo maneja; verificalo si tocas los schemas.
4. **Normalizacion de pais.** `Mexico` y `México` son valores distintos en la base de datos. Sin pasar por `normalization.py`, el filtro cae a `GLOBAL` y el usuario ve datos de todos los paises creyendo que filtro.
5. **`AIza...` vs `AQ.Ab8...`.** Las claves de Gemini tienen dos formatos. El activo es `AQ.Ab8...` y esta en `.env`. No imprimir claves en salidas, commits ni mensajes.
6. **El paquete `google.generativeai` esta deprecado** a favor de `google.genai`. Funciona, pero emite `FutureWarning` en cada arranque.

---

## 7. Estado actual y pendientes

Al dia de hoy:

- Router, Heavy Path, tablero y chat funcionando con Gemini (`LLM_PROVIDER=gemini`).
- `insights_service.py` sin llamada asincrona sin await, resuelto.
- Fallo de filtro de pais, resuelto.
- Compresion TOON verificada.

Pendientes, en orden de impacto:

1. **RPCs sin desplegar.** Es el pendiente critico. Hasta que existan en Supabase, la agregacion no ocurre en PostgreSQL: la sustituye el fallback de Python. Ver seccion 10.2 del documento de arquitectura.
2. **Prompt y esquema desalineados.** El esquema permite combinaciones inconsistentes de trigger y RPC. Se necesita validacion cruzada.
3. **Saludo inicial no se renderiza** en `ChatPanel.jsx` (el mensaje lleva `text` pero se pinta via `payload`).
4. **v1 sin reubicar** en `legacy/`. `README.md` todavia describe la app Flask de CaldasTour.
5. **MCP de Supabase** requiere reiniciar opencode y autorizar por OAuth.

Ya resuelto en esta sesion: `requirements.txt` completo y en UTF-8, `.env` alineado con `config.py`, esquema Pydantic adaptado a Gemini, filtro de pais normalizado y TOON verificado.

El detalle completo de errores corregidos y pendientes vive en las secciones 10 y 11 de `ARQUITECTURA_FLUJO_INTENCIONES.md`. Actualiza esa bitacora al cerrar cada tarea.
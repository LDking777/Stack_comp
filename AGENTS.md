# AGENTS.md — Guía de trabajo para Nexo IA

Lee este archivo antes de tocar código. Está escrito para que un agente nuevo pueda orientarse sin antes leer todo el repositorio.

> **Regla de oro:** todo cambio de código se refleja en la documentación en el mismo commit. Si modificas `backend/`, `frontend/src/`, `supabase/`, `render.yaml` o `requirements.txt`, actualiza este archivo y la bitácora (secciones 10 y 11 de `ARQUITECTURA_FLUJO_INTENCIONES.md`). El hook `.githooks/pre-commit` lo recuerda; ver sección 9.

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
│   │   ├── knowledge_schemas.py# KnowledgeContext, KnowledgeEntry
│   │   └── api_schemas.py      # QueryRequest, QueryResponse, HealthResponse
│   └── services/               # Lógica de negocio (aqui vive el 90% del trabajo)
│       ├── intent_router.py    # Fast Path: query -> trigger + filtros + RPC
│       ├── supabase_service.py # RPC + fallback determinista en Python
│       ├── toon_service.py     # Compresion TOON del contexto
│       ├── insights_service.py # Heavy Path: KPIs -> narrativa
│       ├── knowledge_service.py# Directrices de auditoria (tabla knowledge_auditoria)
│       ├── llm_client.py       # Abstraccion Gemini/OpenAI/Groq + adaptacion de esquemas
│       └── normalization.py    # Paises y dispositivos (acentos, alias)
├── frontend/                   # React + Vite (desplegado en Vercel)
│   └── src/
│       ├── App.jsx             # Composicion tablero + burbuja + panel
│       ├── api.js              # Cliente HTTP; API_BASE recorta el "/" final
│       └── components/
│           ├── BIDashboard.jsx     # KPIs, paises, dispositivos, friccion
│           ├── ChatPanel.jsx       # Burbuja flotante + panel lateral
│           └── AnswerCard.jsx      # Render de respuestas estructuradas
├── tests/                      # pytest (pytest.ini: testpaths=tests, 43 pruebas)
├── supabase/migrations/        # SQL: esquema inicial + knowledge_auditoria
├── render.yaml                 # Blueprint de Render: rootDir, build, start, envVars
├── requirements.txt            # Dependencias del backend (fuente unica)
├── pytest.ini                  # Configuracion de pruebas
├── README.md                   # Arranque local y despliegue
├── opencode.json               # Config de opencode (MCP de Supabase)
├── ARQUITECTURA_FLUJO_INTENCIONES.md   # Arquitectura, estado real, bitacora
├── .githooks/pre-commit        # Recuerda actualizar la documentacion
└── .env                        # Secretos locales. Gitignored. Nunca commitear
```

No existe `legacy/` ni `docs/`: el v1 Flask (`app.py`, `ai_clients.py`, `telegram_bot.py`, `knowledge_base.py`, `test_keys.py`, `test_models.py`, `check_supabase.py`, `static/`, `templates/`) fue **eliminado** del repositorio. Su código sigue en el historial (`git show <commit>:app.py`).


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

# Pruebas (43, sin llamar al proveedor real de LLM)
.\venv\Scripts\python.exe -m pytest -q

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
7. **Root Directory de Render.** Si el servicio apunta a `./backend`, `uvicorn backend.main:app` falla con `ModuleNotFoundError: No module named 'backend'` porque todo el código importa `from backend...`. Debe quedar en la raíz del repo. Ver sección 8.
8. **`VITE_API_URL` con barra final.** `api.js` concatenaba `...onrender.com/` + `/api/v1/...` = `//api/v1/...`, que Starlette no matchea: 404 `{"detail":"Not Found"}`. `API_BASE` ya recorta barras, pero el valor limpio sigue siendo el correcto. Además Vite inyecta `VITE_*` **en el build**: cambiar la variable sin redeployar no hace nada.
9. **Deploy sin push.** Vercel y Render despliegan lo que hay en `Stack_comp`, no tu disco. Un commit local no despliega nada; la verificación es ver el bundle/nombre del asset cambiado, no asumir.


---

## 7. Estado actual y pendientes

Al dia de hoy:

- Router, Heavy Path, tablero y chat funcionando con Gemini (`LLM_PROVIDER=gemini`).
- **API desplegada en Render** (`stack-comp.onrender.com`) y **frontend en Vercel** (`stack-comp.vercel.app`), verificados con `curl`.
- `insights_service.py` sin llamada asincrona sin await, resuelto.
- Fallo de filtro de pais, resuelto.
- Compresion TOON verificada.
- v1 Flask eliminado del repo; `README.md` reescrito para v2.

Pendientes, en orden de impacto:

1. **RPCs sin desplegar.** Es el pendiente critico. Hasta que existan en Supabase, la agregacion no ocurre en PostgreSQL: la sustituye el fallback de Python. Ver seccion 10.2 del documento de arquitectura.
2. **Prompt y esquema desalineados.** El esquema permite combinaciones inconsistentes de trigger y RPC. Se necesita validacion cruzada.
3. **Sin CI.** El push dispara el deploy sin correr `pytest`, `npm run lint` ni `npm run build`. Un error solo se ve en produccion.
4. **Blueprint de Render no vinculado.** `render.yaml` existe pero el servicio se configuro a mano en el dashboard: la fuente real de la config es el dashboard, no el repo. Vincularlo para eliminar el drift.
5. **Saludo inicial no se renderiza** en `ChatPanel.jsx` (el mensaje lleva `text` pero se pinta via `payload`).
6. **MCP de Supabase** requiere reiniciar opencode y autorizar por OAuth.
7. **`google.generativeai` deprecado**, migrar a `google.genai`.

Ya resuelto en estas sesiones: `requirements.txt` completo y en UTF-8, `.env` alineado con `config.py`, esquema Pydantic adaptado a Gemini, filtro de pais normalizado, TOON verificado, despliegues Render + Vercel funcionando y limpieza del v1.

El detalle completo de errores corregidos y pendientes vive en las secciones 10 y 11 de `ARQUITECTURA_FLUJO_INTENCIONES.md`. Actualiza esa bitacora al cerrar cada tarea.

---

## 8. Despliegue (Render + Vercel)

| Pieza | Servicio | URL | Origen |
| --- | --- | --- | --- |
| API FastAPI | Render | `stack-comp.onrender.com` | Repo `Stack_comp`, rama `pdn_qa` |
| Frontend React | Vercel | `stack-comp.vercel.app` | Repo `Stack_comp`, rama `pdn_qa` |

Configuracion real del servicio en Render (hoy en el dashboard, no sincronizada con `render.yaml`):

- **Root Directory:** vacio (raiz del repo). Con `./backend` el arranque muere con `ModuleNotFoundError` — ver trampa 7.
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/api/v1/health`

En Vercel: `VITE_API_URL=https://stack-comp.onrender.com` sin `/` final, y todo cambio de variable exige redeploy (ver trampa 8).

Un solo remoto: `stack` (`LDking777/Stack_comp`), fuente unica del proyecto. El deploy sale de `stack/pdn_qa`, que va en fast-forward con `developer`. El remoto `origin` (`LDking777/api-service-v2`) se elimino de este clon el 2026-10-08 para independizar el proyecto; ese repositorio quedo como estaba (v1 Flask, `main` en `3d11d6e`).

Verificacion posterior al deploy:

1. `git ls-remote stack refs/heads/pdn_qa` debe devolver el commit que acabas de empujar.
2. `curl https://stack-comp.onrender.com/api/v1/health` → 200 con `provider`.
3. El asset del front cambia de nombre: `https://stack-comp.vercel.app/` → `/assets/index-<hash>.js`. Si el hash no cambio, no se desplego nada.

---

## 9. Regla de documentacion: codigo y .md viajan juntos

Un cambio que no se documenta es deuda: el siguiente agente (o tu yo del mes que viene) toma decisiones con informacion vieja.

Siempre que modifiques `backend/`, `frontend/src/`, `supabase/`, `render.yaml`, `requirements.txt`, `pytest.ini` o `.githooks/`, actualiza en el mismo commit:

1. **`AGENTS.md`** — mapa, comandos, trampas conocidas y estado/pendientes (este archivo).
2. **`ARQUITECTURA_FLUJO_INTENCIONES.md`** — anade el caso en la seccion 10.1 (corregido) o 10.2 (pendiente) y cierra en la 11.

Para que no dependa de la memoria, el hook `.githooks/pre-commit` bloquea el commit si tocaste archivos de codigo sin llevar documentacion staged. Se activa una vez por clon:

```powershell
git config core.hooksPath .githooks
```

Salida deliberada cuando el cambio realmente no afecta la documentacion:

```powershell
$env:SKIP_DOCS=1; git commit -m "..."
```


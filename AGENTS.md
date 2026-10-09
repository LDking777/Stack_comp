# AGENTS.md — Guía de trabajo para Nexo IA

Lee este archivo antes de tocar código. Está escrito para que un agente nuevo pueda orientarse sin antes leer todo el repositorio.

> **Regla de oro:** todo cambio de código se refleja en la documentación en el mismo commit. Si modificas `backend/`, `frontend/src/`, `render.yaml` o `requirements.txt`, actualiza este archivo y la bitácora (`ARQUITECTURA_FLUJO_INTENCIONES.md`, secciones 10 y 11). El hook `.githooks/pre-commit` lo recuerda; ver sección 9.

---

## 1. Qué es este proyecto

Nexo IA es un asistente de Business Intelligence sobre el dataset público de **IPS (instituciones prestadoras de servicios de salud) de Colombia**: **"Relación de IPS públicas y privadas según el nivel de atención y capacidad instalada"** (MinSalud/REPS, id `s2ru-bqt6` en datos.gov.co).

El usuario hace preguntas en lenguaje natural ("¿por qué Antioquia concentra tanta capacidad?", "¿cuántas camas hay en Bogotá?") y recibe una respuesta con cifras verificadas y una interpretación narrativa.

No es un chat de propósito general. El dominio es el sistema de salud colombiano: cobertura territorial, naturaleza jurídica, niveles de atención y capacidad instalada agregada por grupo y descripción (p. ej. camas pediátricas, urgencias, salas de cirugía, cuidado neonatal). También permite buscar sedes registradas por ubicación, nombre, NIT/código como filtros internos y tipo de capacidad, devolviendo nombre, sede, dirección, teléfono institucional publicado y datos analíticos públicos. Nunca devuelve NIT/códigos ni datos de contacto personales. Todas las respuestas, incluso en voz y documentos, deben ser en español.

### El invariante central

**El LLM nunca calcula números.** Socrata (datos.gov.co) agrega vía **SoQL**; el LLM solo narra.

Si alguna vez modificas este diseño, cualquier ruta que haga que el modelo estime, infiera o "aproxime" un KPI es un bug, no una mejora. Los números exactos vienen de la API pública o del fallback, nunca del prompt.

### Segundo invariante

Los cálculos deterministas y la síntesis cualitativa son capas separadas. El router decide cuál se ejecuta; no se mezclan los resultados.

### Tercer invariante: la fuente analítica es externa y de solo lectura

La agregación del dataset de IPS ocurre en `https://www.datos.gov.co/resource/s2ru-bqt6.json`. Supabase no almacena ni calcula esos KPIs: se usa únicamente para persistir sesiones, turnos de chat, documentos cargados, archivos originales privados y embeddings de RAG. La fuente analítica está congelada desde `2022-11-21` (REPS), por eso el cache en memoria de datos.gov.co es seguro.

---

## 2. Mapa del repositorio

```
api-service-v2/
├── backend/                    # API FastAPI (todo el análisis)
│   ├── main.py                 # Endpoints y orquestación del pipeline
│   ├── config.py               # Settings desde .env (Pydantic)
│   ├── data/
│   │   └── knowledge_ips.json  # Knowledge local del asistente (directrices)
│   ├── mcp/connector.py        # Registro de conectores MCP
│   ├── schemas/                # Contratos Pydantic (router, insights, API)
│   │   ├── router_schemas.py   # IntentRouterDecision, QueryIntentParams, IntentTrigger
│   │   ├── insight_schemas.py  # QualitativeInsightResponse
│   │   ├── knowledge_schemas.py# KnowledgeContext, KnowledgeEntry
│   │   └── api_schemas.py      # QueryRequest, QueryResponse, HealthResponse,
│   │                           #   LiveTokenResponse, LiveToolRequest, LiveToolResponse
│   └── services/               # Lógica de negocio (aquí vive el 90% del trabajo)
│       ├── intent_router.py    # Fast Path: query -> trigger + filtros + operación
│       ├── datosgov_service.py # SoQL a datos.gov.co (agregación y muestra no identificable)
│       ├── toon_service.py     # Compresión TOON del contexto
│       ├── insights_service.py # Heavy Path: KPIs -> narrativa
│       ├── knowledge_service.py# Directrices desde backend/data/knowledge_ips.json
│       ├── llm_client.py       # Abstracción Gemini/OpenAI/Groq + adaptación de esquemas
│       ├── normalization.py    # Departamentos, naturaleza, nivel, grupo de capacidad
│       ├── conversation_service.py # Historial persistente de chat por sesión
│       ├── document_service.py # Extracción, filtro de dominio y RAG de documentos
│       ├── embeddings_service.py # Vectores Gemini para búsqueda semántica
│       ├── supabase_service.py # PostgREST + Storage con service_role solo backend
│       ├── whatsapp_service.py # Firma Meta y mensajería Cloud API
│       └── live_token_service.py # Credenciales efímeras para Gemini Live (voz)
├── frontend/                   # React + Vite (desplegado en Vercel)
│   ├── public/avatar.jpg       # Avatar de la portada del agente
│   └── src/
│       ├── App.jsx             # Rutas / (portada) y /dashboard + estado global
│       ├── api.js              # Cliente HTTP; API_BASE recorta el "/" final
│       ├── pages/HomePage.jsx  # Portada con avatar cuadrado y chat persistente
│       ├── hooks/
│       │   └── useGeminiLive.js# Voz bidireccional con Gemini Live
│       ├── utils/pcmAudio.js   # PCM 16 kHz (in) / 24 kHz (out) vía Web Audio
│       └── components/
│           ├── BIDashboard.jsx # KPIs, desgloses por departamento/naturaleza/capacidad
│           ├── ChatPanel.jsx   # Chat embebido en portada y flotante en dashboard
│           ├── Markdown.jsx    # Render mínimo de markdown para respuestas del bot
│           ├── AnswerCard.jsx  # Render de respuestas estructuradas
│           └── WhatsAppModal.jsx # Conexión y preguntas agregadas para WhatsApp
├── tests/                      # pytest (pytest.ini: testpaths=tests)
├── render.yaml                 # Blueprint de Render: rootDir, build, start, envVars
├── requirements.txt            # Dependencias del backend (fuente única)
├── supabase_mvp.sql            # Esquema pegable en Supabase SQL Editor
├── pytest.ini                  # Configuración de pruebas
├── README.md                   # Arranque local y despliegue
├── opencode.json               # Config de opencode
├── ARQUITECTURA_FLUJO_INTENCIONES.md   # Arquitectura, estado real, bitácora
├── .githooks/pre-commit        # Recuerda actualizar la documentación
└── .env                        # Secretos locales. Gitignored. Nunca commitear
```

No existe una carpeta `supabase/` ni se usa Supabase como fuente de KPIs. El script `supabase_mvp.sql` en la raíz crea las tablas de memoria/RAG y el bucket privado. El v1 Flask y sus migraciones anteriores fueron eliminados (su código sigue en el historial de git).

---

## 3. Dónde seguir una consulta

Este es el recorrido de `POST /api/v1/query`. Si buscas un comportamiento, este es el orden.

1. `backend/main.py` — orquestación. Decide Fast vs Heavy Path.
2. `backend/services/intent_router.py` — clasifica y extrae filtros. Saludos, definiciones y listados se resuelven aquí sin LLM.
3. `backend/services/datosgov_service.py` — ejecuta la operación SoQL (o devuelve `sin_datos`).
4. `backend/services/insights_service.py` — genera narrativa (solo Heavy Path).
5. `backend/schemas/` — el contrato de lo que sale por cada lado.

Para el tablero, entra directo en `backend/main.py` (`GET /api/v1/dashboard`) y salta a `datosgov_service.execute()` (varias operaciones en `asyncio.gather`).

### El recorrido de la voz (Gemini Live)

La voz reutiliza el mismo pipeline determinista; el modelo Live solo narra.

1. `frontend/src/hooks/useGeminiLive.js` — pide permiso de micrófono y luego `getLiveToken()`.
2. `backend/main.py` (`POST /api/v1/live/token`) → `live_token_service.py` mintea una credencial efímera (`auth_tokens`, `v1alpha`). La `GEMINI_API_KEY` **nunca sale del backend**.
3. El navegador abre el WebSocket contra Gemini Live con `token.token`, envía PCM 16 kHz y reproduce PCM 24 kHz (`utils/pcmAudio.js`).
4. Cualquier pregunta con cifras dispara la herramienta `consultar_ips` → `POST /api/v1/live/tool` → `_execute_query()` (mismo pipeline de `POST /api/v1/query`); la respuesta vuelve al modelo vía `sendToolResponse`.
5. Las consultas agregadas y muestras analíticas se limitan a departamento, municipio, naturaleza, nivel, grupo y descripción de capacidad y cantidad. NIT/código/nombre pueden filtrar internamente un agregado o una búsqueda de sedes; no se devuelven identificadores. El directorio devuelve nombre de prestador/sede, dirección, capacidades y teléfono institucional solo si está publicado; no devuelve email ni datos personales.
6. Al completar cada turno, las transcripciones del usuario y de la respuesta hablada se agregan al historial visible del chat; no hay diarización acústica. Si Gemini no entrega transcripción de salida, se muestra como respaldo la respuesta verificada de la herramienta.

---

## 4. Dónde buscar para optimizar tokens

Si la tarea es reducir consumo de tokens, empieza aquí y en este orden de impacto.

### 4.1. El límite de registros — mayor palanca

`backend/main.py` llama a `datosgov_service.fetch_records(limit=10, ...)`. Ese `10` multiplica directamente el costo del Heavy Path: el bloque de contexto que se comprime a TOON. Bajarlo a 5 reduce a la mitad el contexto, con pérdida de detalle. Subirlo sube el costo de forma lineal.

### 4.2. La compresión TOON

`backend/services/toon_service.py`. Ya entrega -53% a -60% frente a JSON. Si buscas más, el lugar correcto es aquí, no en los prompts.

### 4.3. Los prompts del sistema

`ROUTER_SYSTEM_PROMPT` en `intent_router.py` se envía **completo en todas las consultas que llegan al LLM** (saludos, definiciones y listados no llegan). `HEAVY_PATH_SYSTEM_PROMPT` en `insights_service.py` solo en Heavy Path.

El router es determinista y de bajo riesgo, así que es el candidato natural a prompt más corto: buena parte de sus reglas pueden pasar al esquema Pydantic, donde no se repiten por llamada.

### 4.4. Serialización de KPIs

`insights_service.py` construye el contexto con `json.dumps(kpis, ensure_ascii=False, indent=2)`. Antes usaba `f"{kpis}"` (la `repr()` de un dict de Python, más verbosa).

### 4.5. Campos muertos en la respuesta

`QueryResponse` aún puede enviar `toon_context_preview` (ya no se calcula), `trigger`, `confidence_score` y `latency`. El frontend ya no lee ninguno. Reducir esto no ahorra tokens de LLM, pero reduce ancho de banda.

### 4.6. Lo que NO debes optimizar

Los KPIs deterministas. Son la fuente de verdad. Recortarlos para ahorrar tokens degrada el insight sin beneficio.

---

## 5. Comandos para trabajar

```powershell
# Backend
.\venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing

# Frontend
cd frontend; npm run dev

# Pruebas (sin llamar al proveedor real de LLM)
$env:PYTHONIOENCODING="utf-8"; .\venv\Scripts\python.exe -m pytest -q

# Verificar que un cambio no rompió las importaciones
.\venv\Scripts\python.exe -c "import backend.main"
```

Endpoint de consulta rápida:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/query" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"¿Cuántas camas hay en Antioquia?"}'
```

`GET /api/v1/health` expone `provider`, los modelos efectivos y el bloque `fuente_datos` (dataset, recurso y operaciones SoQL disponibles).

---

## 6. Trampas conocidas

Estas cosas fallan **en silencio**. Un cambio puede romper el sistema sin que ninguna prueba falle, porque el fallback determinista siempre responde.

1. **El fallback tapa los fallos del LLM.** Si el proveedor devuelve algo inválido, el sistema responde igual con reglas heurísticas. Solo se nota en los logs (`Error en el Intent Router`). Al probar, revisa el log: una respuesta correcta no prueba que el LLM se haya usado.
2. **Confianza alta no significa LLM.** `_heuristic_fallback` asigna confianzas fijas (0.85, 0.88, 0.90). Si ves 0.85 o 0.90 exactos, sospecha fallback.
3. **Gemini rechaza esquemas Pydantic.** Acepta solo un subconjunto de OpenAPI Schema. `title`, `$defs`, `minimum`, `maximum` y `additionalProperties` producen `Unknown field for Schema`. `inline_refs()` en `llm_client.py` lo maneja; verifícalo si tocas los schemas.
4. **SoQL compara texto EXACTO y su `lower()` NO quita acentos.** `naturaleza='Pública'` funciona; `lower(naturaleza)='publica'` devuelve 0 filas. Toda canonicalización debe ocurrir en `normalization.py` antes de armar el `$where`. Los municipios llegan en MAYÚSCULAS y con acentos propios ("APARTADÓ"), y se resuelven contra un índice dinámico cacheado. Si una palabra coincide con un municipio pero está usada en otro sentido (p. ej., "apartado de urgencias"), se priorizan los lugares introducidos por "en", "cerca de" y expresiones equivalentes.
5. **NUNCA usar `api/v3/views/s2ru-bqt6/query.json`.** Ignora `$limit` y devuelve el dataset completo (~36 MB). El endpoint `/resource/` sí respeta filtros y agregaciones y responde en KB.
6. **El paquete `google.generativeai` está deprecado** a favor de `google.genai`. Funciona, pero emite `FutureWarning` en cada arranque.
7. **Root Directory de Render.** Si el servicio apunta a `./backend`, `uvicorn backend.main:app` falla con `ModuleNotFoundError: No module named 'backend'` porque todo el código importa `from backend...`. Debe quedar en la raíz del repo. Ver sección 8.
8. **`VITE_API_URL` con barra final.** `api.js` concatena `...onrender.com/` + `/api/v1/...` = `//api/v1/...`, que Starlette no matchea: 404 `{"detail":"Not Found"}`. `API_BASE` ya recorta barras, pero el valor limpio sigue siendo el correcto. Además Vite inyecta `VITE_*` **en el build**: cambiar la variable sin redeployar no hace nada.
9. **Deploy sin push.** Vercel y Render despliegan lo que hay en `Stack_comp`, no tu disco. Un commit local no despliega nada; la verificación es ver el bundle/nombre del asset cambiado, no asumir.
10. **`sum_capacity` sin `group_by` es un total.** En `datosgov_service.execute()`, `sum_capacity` con `group_by` devuelve desglose + `total_capacidad`; sin `group_by` devuelve solo `total_capacidad` (escalar). No es un error.
11. **Memoria/RAG requieren Supabase configurado.** Ejecuta `supabase_mvp.sql` y configura `SUPABASE_URL` + `SUPABASE_SECRET_KEY` (o `SUPABASE_SERVICE_ROLE_KEY` legado) solo en el backend. La clave secreta nunca va en Vite. Sin configuración, `/api/v1/health` queda `degraded` y las operaciones con sesión responden 503; no hay fallback silencioso a RAM. El SQL no altera `storage.objects` ni sus políticas: es una tabla gestionada por Supabase; el bucket propio se crea privado y el backend accede con la clave de servidor.

---

## 7. Estado actual y pendientes

Los KPIs siguen viniendo exclusivamente de **datos.gov.co** (Socrata/SoQL). Supabase se usa solo para sesión/memoria y documentos, no para la analítica de IPS.

- **Router, Heavy Path, tablero y chat funcionando** con **Groq** (`LLM_PROVIDER=groq`, modelo `openai/gpt-oss-120b` en ambas etapas). Groq es el proveedor activo por decisión: Gemini se descartó por no ofrecer capa gratuita y OpenAI está sin créditos (`429 insufficient_quota`).
- **Fuente de datos**: dataset `s2ru-bqt6` (41.427 registros, corte `2022-11-21`, ~1.027 municipios). Agregaciones en vivo vía SoQL.
- **Pivote completado**: la capa de datos (`datosgov_service.py`), la normalización (departamentos/naturaleza/nivel/grupo), los esquemas, el router, el knowledge local (`backend/data/knowledge_ips.json`) y el frontend (tablero IPS, sin el bloque pitch/turismo) fueron migrados al dominio de salud.
- **Knowledge local** del asistente con 8 directrices (capacidad, cobertura, gestión, calidad de datos). Si falta el archivo, el Heavy Path sigue sin directrices.
- **Preguntas de definición/fuera de dominio con guía.** `intent_router.py` resuelve "¿qué es una IPS?" con un glosario determinista (`_definition_reply`, sin LLM), saludos y capacidades (`_small_talk_reply`) y listados (`_list_intent`).
- **UI**: tema claro/oscuro persistido (`ThemeContext`) y acento emerald. El chat se llama **NEXO IA**.
- **Rutas principales**: `/` es la portada con el avatar cuadrado grande a la izquierda y el chat persistente a la derecha; en escritorio el avatar escala por ancho y altura disponibles, y en móvil compacto mantiene más espacio visual sin desbordar el encabezado. Tablet/móvil mantiene scroll natural si el contenido excede el alto. `/dashboard` conserva el tablero analítico anterior y el chat flotante. El header permite navegar entre ambas. El usuario inicia el micrófono explícitamente desde el control de voz.
- **Memoria y documentos por sesión**: `supabase_mvp.sql` crea tablas con RLS, búsqueda pgvector y bucket privado. El backend persiste historial, fragmentos, embeddings y archivo original; el frontend conserva el `session_id` y el historial visible local. Embeddings con Gemini y el prompt RAG limitan documentos/preguntas al dominio IPS/salud de Colombia. Requiere ejecutar el SQL y configurar `SUPABASE_URL`, `SUPABASE_SECRET_KEY` (o `SUPABASE_SERVICE_ROLE_KEY`) y `GEMINI_API_KEY` en el backend. La conexión real de DB, búsqueda y limpieza se probó el 2026-10-09 con contenido sintético temporal.
- **Análisis y directorio de IPS.** Los agregados aceptan filtros y desglose por ubicación, naturaleza, nivel y tipo de capacidad. Para orientar búsquedas de sedes, `list_ips` filtra por municipio/departamento y capacidad; también permite filtrar internamente por nombre, NIT o código. La respuesta agrupa las filas repetidas por sede y muestra nombre, sede, dirección, teléfono institucional si está publicado, nivel, naturaleza y capacidades; omite los NIT/códigos, email y datos personales. Interpreta preguntas como «¿quiénes tienen urgencias?» como búsqueda de directorio y puede heredar ubicación del turno anterior. Compara solo la cantidad declarada del tipo de capacidad. La fuente REPS tiene corte `2022-11-21` y no incluye coordenadas: «cerca» significa el municipio indicado, no distancia ni disponibilidad actual.
- **Idioma y tono.** Router, análisis, documentos y voz deben responder únicamente en español, aunque el usuario escriba o pida otro idioma. El backend añade una frase empática solo ante señales explícitas de preocupación/frustración; no etiqueta ni almacena emociones y no reemplaza la respuesta verificada ni da diagnósticos.
- **Voz con Gemini Live.** El backend mintea credenciales efímeras (`POST /api/v1/live/token`, la `GEMINI_API_KEY` no sale del server) y el navegador conversa por WebSocket (`gemini-3.8-live`). Las preguntas con cifras disparan la herramienta `consultar_ips` → `POST /api/v1/live/tool` → mismo pipeline SoQL. El chat de texto sigue intacto; al completar cada turno, las transcripciones del usuario y de la respuesta hablada se agregan al historial visible y persistente del chat. Si Gemini no entrega transcripción de salida, se muestra como respaldo la respuesta verificada de la herramienta. No hay diarización acústica. El avatar de portada permanece estático durante la conversación. **Conexión real verificada** (2026-10-09): token efímero + sesión WebSocket contra `gemini-3.8-live` responden OK.
- **Canal WhatsApp (Meta Cloud API).** `GET/POST /api/v1/whatsapp/webhook` valida el handshake y la firma HMAC-SHA256 de los eventos entrantes. Los mensajes se procesan con `_execute_query()` y memoria aislada por remitente; `GET /api/v1/whatsapp/config` publica solo el enlace y número del canal. Requiere `WHATSAPP_ENABLED`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` y `WHATSAPP_PHONE_NUMBER`; configurar secretos únicamente en el backend.

Pendientes, en orden de impacto:

1. **Sin CI.** El push dispara el deploy sin correr `pytest`, `npm run lint` ni `npm run build`. Un error solo se ve en producción.
2. **Blueprint de Render no vinculado.** `render.yaml` existe pero el servicio se configuró a mano en el dashboard: la fuente real de la config es el dashboard, no el repo. Vinculenlo para eliminar el drift.
3. **Prompt del router y esquema.** El esquema permite combinaciones de trigger/operación poco consistentes. Falta validación cruzada.
4. **`google.generativeai` deprecado**, migrar a `google.genai`.
5. **Saludo inicial de `ChatPanel.jsx`**: verifica que se renderice (lleva `text` y no `payload`).
6. **Gemini Live verificado a nivel de protocolo; falta el audio del navegador.** La cuenta **sí tiene acceso**: `POST /api/v1/live/token` mintea la credencial y una sesión real contra `gemini-3.8-live` se abre y responde (probado 2026-10-09). Falta la prueba de extremo a extremo en el navegador (permiso de micrófono, captura/reproducción PCM y la herramienta `consultar_ips`). Las credenciales efímeras siguen en Preview y solo en Gemini Developer API (`v1alpha`).
7. **WhatsApp requiere configuración en producción.** Antes de habilitarlo, configurar sus secretos/valores en Render; después registrar en Meta la URL del backend (`VITE_API_URL` + `/api/v1/whatsapp/webhook`) y el mismo `WHATSAPP_VERIFY_TOKEN`. Aún no se ha desplegado ni probado con una cuenta real de Meta.

El detalle completo de errores corregidos y pendientes vive en las secciones 10 y 11 de `ARQUITECTURA_FLUJO_INTENCIONES.md`. Actualiza esa bitácora al cerrar cada tarea.

---

## 8. Despliegue (Render + Vercel)

| Pieza | Servicio | URL | Origen |
| --- | --- | --- | --- |
| API FastAPI | Render | `stack-comp.onrender.com` | Repo `Stack_comp`, rama `pdn_qa` |
| Frontend React | Vercel | `stack-comp.vercel.app` | Repo `Stack_comp`, rama `pdn_qa` |

Configuración real del servicio en Render (hoy en el dashboard, no sincronizada con `render.yaml`):

- **Root Directory:** vacío (raíz del repo). Con `./backend` el arranque muere con `ModuleNotFoundError` — ver trampa 7.
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path:** `/api/v1/health`
- **Variables:** `LLM_PROVIDER=groq`, modelos Groq y `GROQ_API_KEY` (secretos a mano en el dashboard). Para memoria/RAG: `SUPABASE_URL`, `SUPABASE_SECRET_KEY` (o la legacy `SUPABASE_SERVICE_ROLE_KEY`) y `GEMINI_API_KEY` (solo backend; nunca `VITE_*`). Para la voz: opcional `GEMINI_LIVE_MODEL` (por defecto `gemini-3.8-live`). Para WhatsApp: `WHATSAPP_ENABLED`, `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET` y el número público `WHATSAPP_PHONE_NUMBER`.

En Vercel: `VITE_API_URL=https://stack-comp.onrender.com` sin `/` final, y todo cambio de variable exige redeploy (ver trampa 8).

Un solo remoto: `stack` (`LDking777/Stack_comp`), fuente única del proyecto. El deploy sale de `stack/pdn_qa`. El remoto `origin` (`LDking777/api-service-v2`) se eliminó de este clon el 2026-10-08.

Verificación posterior al deploy:

1. `git ls-remote stack refs/heads/pdn_qa` debe devolver el commit que acabas de empujar.
2. `curl https://stack-comp.onrender.com/api/v1/health` → 200 con `provider`.
3. El asset del front cambia de nombre: `https://stack-comp.vercel.app/` → `/assets/index-<hash>.js`. Si el hash no cambió, no se desplegó nada.

---

## 9. Regla de documentación: código y .md viajan juntos

Un cambio que no se documenta es deuda: el siguiente agente (o tu yo del mes que viene) toma decisiones con información vieja.

Siempre que modifiques `backend/`, `frontend/src/`, `render.yaml`, `requirements.txt`, `pytest.ini` o `.githooks/`, actualiza en el mismo commit:

1. **`AGENTS.md`** — mapa, comandos, trampas conocidas y estado/pendientes (este archivo).
2. **`ARQUITECTURA_FLUJO_INTENCIONES.md`** — añade el caso en la sección 10.1 (corregido) o 10.2 (pendiente) y cierra en la 11.

Para que no dependa de la memoria, el hook `.githooks/pre-commit` bloquea el commit si tocaste archivos de código sin llevar documentación staged. Se activa una vez por clon:

```powershell
git config core.hooksPath .githooks
```

Salida deliberada cuando el cambio realmente no afecta la documentación:

```powershell
$env:SKIP_DOCS=1; git commit -m "..."
```

# Nexo IA — Analítica de IPS de Colombia (datos.gov.co)

Asistente de BI sobre el dataset público **"Relación de IPS públicas y privadas según el nivel de atención y capacidad instalada"** (MinSalud/REPS, `s2ru-bqt6` en datos.gov.co). El usuario pregunta en lenguaje natural ("¿cuántas camas hay en Antioquia?") y recibe cifras exactas más una interpretación narrativa.

**El LLM nunca calcula números.** Socrata ejecuta toda agregación del dataset vía **SoQL** (`$select`, `$where`, `$group`). Supabase se usa solamente para persistir memoria del chat y documentos de RAG; no almacena los KPIs.

- Backend: **FastAPI** + router LLM (Groq/Gemini/OpenAI), compresión TOON, Fast Path (KPIs) / Heavy Path (diagnóstico).
- Frontend: **React + Vite**, tablero de cobertura y capacidad, y asistente **Nexo IA**. En portada el chat permanece junto al avatar; en el dashboard conserva el acceso flotante. UI con **Tailwind vía CDN** (`index.html`).
- Rutas del frontend: `/` muestra la portada con avatar y conversación persistente, ajustada al alto disponible en escritorio y compacta junto al chat en móviles; en tablets y pantallas cortas puede desplazarse si el contenido excede el viewport. `/dashboard` mantiene accesible el tablero BI con chat flotante.
- Datos: **[datos.gov.co](https://www.datos.gov.co)**, dataset `s2ru-bqt6` — 41.427 registros, corte `2022-11-21`. Datos en vivo vía SoQL.
- Memoria/RAG: **Supabase Postgres + pgvector + Storage privado**. El esquema está en [`supabase_mvp.sql`](supabase_mvp.sql).

Documentación completa: [`AGENTS.md`](AGENTS.md) (guía de trabajo) y [`ARQUITECTURA_FLUJO_INTENCIONES.md`](ARQUITECTURA_FLUJO_INTENCIONES.md) (arquitectura y bitácora).

## Requisitos

- Python 3.11+
- Node 18+
- Una clave de LLM (Groq, Gemini u OpenAI). Groq es el proveedor activo (capa gratuita).

## Arranque local

### 1. Backend

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configura `.env` en la raíz (gitignored) con:

```
LLM_PROVIDER=groq
GROQ_API_KEY=...
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SECRET_KEY=...
GEMINI_API_KEY=...
```

Antes, pega [`supabase_mvp.sql`](supabase_mvp.sql) en **Supabase → SQL Editor** y ejecútalo. Configura la clave `SUPABASE_SECRET_KEY` (o el nombre legado `SUPABASE_SERVICE_ROLE_KEY`) solo en el backend (por ejemplo, Render); nunca la pongas en variables `VITE_*` ni en el frontend. `GEMINI_API_KEY` se usa para crear embeddings de documentos.

Al indexar un archivo, el original queda en el bucket privado de Supabase; el texto se envía a Gemini para crear embeddings y los fragmentos pertinentes pueden enviarse al proveedor LLM configurado para responder. No subas documentos que no estés autorizado a procesar.

Levanta la API:

```powershell
.\venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000
```

Comprobación: `GET http://127.0.0.1:8000/api/v1/health` debe indicar `status: online`, `persistencia.configured: true` y `documentos_rag.enabled: true`. Si Supabase no está configurado, la API indica `degraded` y las funciones con sesión no se degradan silenciosamente a memoria volátil.

> `uvicorn` debe lanzarse desde la raíz del repo: todo el código importa `from backend...`.

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173
```

`VITE_API_URL` apunta al backend (por defecto `http://localhost:8000`). La barra final es opcional: `api.js` la recorta.

> La UI se compila con **Tailwind CDN** inyectado en `frontend/index.html`; no requiere `npm install` extra ni paso de build además del de Vite.

### 3. Pruebas

```powershell
.\venv\Scripts\python.exe -m pytest        # sin llamar al proveedor real de LLM
```

Las que llaman al proveedor real llevan el marker `live_llm` y no corren por defecto (actívalas con `NEXO_TEST_LIVE_LLM=1`).

## Endpoints

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/api/v1/query` | Flujo de intenciones (router → SoQL → respuesta/narrativa). |
| GET | `/api/v1/dashboard` | KPIs y desgloses agregados para el tablero. |
| GET | `/api/v1/health` | Estado, diagnóstico del LLM y metadatos de la fuente. |
| POST | `/api/v1/documents` | Indexa documento relacionado con salud/IPS y guarda original privado en Supabase Storage. |
| GET/DELETE | `/api/v1/documents/{session_id}` | Lista o elimina documentos, vectores, originales y memoria de una sesión. |
| DELETE | `/api/v1/sessions/{session_id}/history` | Reinicia solo la memoria conversacional sin borrar documentos. |

Consulta rápida:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/query" -Method Post `
  -ContentType "application/json" `
  -Body '{"query":"¿Cuántas camas hay en Antioquia?"}'
```

## Despliegue

| Pieza | Servicio | Config |
| --- | --- | --- |
| API | Render (`stack-comp.onrender.com`) | `render.yaml` (Blueprint) + Groq, Gemini y Supabase secrets en el dashboard |
| Frontend | Vercel (`stack-comp.vercel.app`) | variable `VITE_API_URL` |

Reglas que ya costaron un despliegue roto:

1. **Render**: el Root Directory debe quedar **vacío** (raíz del repo). Con `./backend`, `uvicorn backend.main:app` falla con `ModuleNotFoundError: No module named 'backend'`. El `buildCommand` es `pip install -r requirements.txt` y el `startCommand` `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
2. **Vercel**: `VITE_API_URL=https://stack-comp.onrender.com` **sin barra final** (Vite la inyecta en el build; si cambias la variable hay que redeployar). Con `/` final la petición llegaba como `//api/v1/...` y devolvía 404 `{"detail":"Not Found"}`.
3. Nada llega a producción sin `git commit` + `git push`: Vercel y Render despliegan lo que está en `Stack_comp`, no tu disco local.

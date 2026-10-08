# Nexo IA — API de Business Intelligence (v2)

Asistente de BI para usuarios de ventas: preguntas en lenguaje natural, respuestas con cifras verificadas (PostgreSQL/Supabase) y una interpretación narrativa. El LLM nunca calcula números.

- Backend: **FastAPI** + Gemini/Groq/OpenAI, compresión TOON, router de intenciones (Fast/Heavy Path).
- Frontend: **React + Vite** (tablero KPIs + burbuja de chat).
- Datos: **Supabase** (PostgreSQL), RPCs de agregación.

Documentación completa: [`AGENTS.md`](AGENTS.md) (guía de trabajo) y [`ARQUITECTURA_FLUJO_INTENCIONES.md`](ARQUITECTURA_FLUJO_INTENCIONES.md) (arquitectura y bitácora).

## Requisitos

- Python 3.11+
- Node 18+
- Cuenta en Supabase y una clave de LLM (Groq, Gemini u OpenAI)

## Arranque local

### 1. Backend

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configura `.env` en la raíz (gitignored) con, al menos:

```
LLM_PROVIDER=groq
GROQ_API_KEY=...
SUPABASE_URL=https://<proyecto>.supabase.co
SUPABASE_KEY=...
SUPABASE_SECRET_KEY=...
```

Levanta la API:

```powershell
.\venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000
```

Comprobación: `GET http://127.0.0.1:8000/api/v1/health` devuelve `provider`, modelos efectivos y `rpcs_deployed`.

> `uvicorn` debe lanzarse desde la raíz del repo: todo el código importa `from backend...`.

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev        # http://localhost:3000
```

`VITE_API_URL` apunta al backend (por defecto `http://localhost:8000`). La barra final es opcional: `api.js` la recorta.

### 3. Pruebas

```powershell
.\venv\Scripts\python.exe -m pytest        # 43 pruebas, sin llamar al LLM real
```

Las que llaman al proveedor real llevan el marker `live_llm` y no corren por defecto.

## Despliegue

| Pieza | Servicio | Config |
| --- | --- | --- |
| API | Render (`stack-comp.onrender.com`) | `render.yaml` (Blueprint) |
| Frontend | Vercel (`stack-comp.vercel.app`) | variable `VITE_API_URL` |

Reglas que ya costaron un despliegue roto:

1. **Render**: el Root Directory debe quedar **vacío** (raíz del repo). Con `./backend`, `uvicorn backend.main:app` falla con `ModuleNotFoundError: No module named 'backend'`. El `buildCommand` es `pip install -r requirements.txt` y el `startCommand` `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
2. **Vercel**: `VITE_API_URL=https://stack-comp.onrender.com` **sin barra final** (Vite la inyecta en el build; si cambias la variable hay que redeployar). Con `/` final la petición llegaba como `//api/v1/...` y devolvía 404 `{"detail":"Not Found"}`.
3. Nada llega a producción sin `git commit` + `git push`: Vercel y Render despliegan lo que está en `Stack_comp`, no tu disco local.

# AGENTS.md — Guía de trabajo para Nexo IA

Lee este archivo antes de tocar código. Está escrito para que un agente nuevo pueda orientarse sin antes leer todo el repositorio.

> **Regla de oro:** todo cambio de código se refleja en la documentación en el mismo commit. Si modificas `backend/`, `frontend/src/`, `supabase/`, `render.yaml` o `requirements.txt`, actualiza este archivo y la bitácora (secciones 10 y 11 de `ARQUITECTURA_FLUJO_INTENCIONES.md`). El hook `.githooks/pre-commit` lo recuerda; ver sección 9.

---

## 1. Qué es este proyecto

Nexo IA es un asistente de Business Intelligence y Agente Vocal Cognitivo desarrollado para interactuar con datos en tiempo real. En su evolución para el **Reto 01 de Kognia Labs**, se transformó en un **Agente Vocal Cognitivo** que habla con cualquier documento en tiempo real, ingestando la API oficial de `datos.gov.co` (Relación de IPS y capacidad instalada) o documentos sorpresa del jurado, ofreciendo briefing automático, streaming diarizado y telemetría de emoción en vivo.

### El invariante central

**El LLM nunca calcula números.** PostgreSQL o el dataset validado agregan; el LLM solo narra.

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
│       ├── App.jsx             # Switcher Bi-vista (Pitch & Arquitectura vs Consola Vocal)
│       ├── api.js              # Cliente HTTP; API_BASE recorta el "/" final
│       ├── services/
│       │   └── documentKnowledge.js # Ingesta SODA3 datos.gov.co (s2ru-bqt6) + parser local RAG
│       ├── utils/
│       │   ├── speechVoiceEngine.js # STT/TTS bidireccional de baja latencia + telemetría de emoción
│       │   └── soundEffects.js      # Sistema de micro-sonidos Web Audio API puro
│       └── components/
│           ├── PitchSection.jsx     # Apartado expositivo: Kognia Labs Reto 01 & guion 10 min
│           ├── CognitiveDashboard.jsx # Consola Vocal, transcripción diarizada, radar de emociones y tabla IPS
│           ├── BIDashboard.jsx      # Dashboard analítico tradicional de sesiones
│           ├── ChatPanel.jsx        # Asistente flotante NEXO IA
│           └── ToastContainer.jsx   # Notificaciones contextuales Tailwind
├── tests/                      # pytest (pytest.ini: testpaths=tests, 47 pruebas)
├── supabase/migrations/        # SQL: esquema inicial + knowledge_auditoria
├── render.yaml                 # Blueprint de Render: rootDir, build, start, envVars
├── requirements.txt            # Dependencias del backend (fuente unica)
├── pytest.ini                  # Configuracion de pruebas
├── README.md                   # Arranque local y despliegue
├── ARQUITECTURA_FLUJO_INTENCIONES.md   # Arquitectura, estado real, bitacora
└── .env                        # Secretos locales. Gitignored. Nunca commitear
```

---

## 3. Dónde seguir una consulta

1. `backend/main.py` — orquestacion. Decide modo fast vs heavy.
2. `backend/services/intent_router.py` — clasifica y extrae filtros.
3. `backend/services/supabase_service.py` — ejecuta RPC o fallback.
4. `backend/services/insights_service.py` — genera narrativa (solo heavy).
5. En Frontend: `CognitiveDashboard.jsx` y `documentKnowledge.js` procesan consultas de voz en tiempo real con Web Speech API y RAG documental.

---

## 4. Comandos para trabajar

```powershell
# Backend
.\venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000
Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing

# Frontend
cd frontend; npm run dev

# Pruebas (47, sin llamar al proveedor real de LLM)
.\venv\Scripts\python.exe -m pytest -q

# Compilación de producción Frontend
npm --prefix frontend run build
```

---

## 5. Estado actual y pendientes

Al día de hoy:
- **Adaptación completa a Kognia Labs (Reto 01 — Agente Vocal Cognitivo)**:
  - Frontend transformado al 100% manteniendo el apartado expositivo (`PitchSection.jsx`) y la consola operativa en vivo (`CognitiveDashboard.jsx`).
  - Motor RAG e Ingesta SODA3: conexión con `https://www.datos.gov.co/resource/s2ru-bqt6.json` (Relación de IPS según nivel y capacidad instalada) con fallback resiliente.
  - Soporte de subida Drag & Drop para documentos sorpresa del jurado (P2) con briefing instantáneo y 4 preguntas sugeridas ejecutables con 1 clic (P3).
  - Conversación vocal de baja latencia (<420ms) con Web Speech API (`SpeechRecognition` + `SpeechSynthesis Utterance`).
  - Transcripción diarizada estricta en tiempo real (Hablante 1: Jurado vs Hablante 2: Agente) con timestamps y badges emocionales (P5).
  - Panel de telemetría cognitiva con score de sentimiento (-1.0 a +1.0) y radar de emociones (Confianza, Curiosidad, Frustración, Asombro, Duda).
  - Fidelidad estricta al documento y rechazo de preguntas fuera de dominio (honesty RAG).
  - Compilación de Vite limpia y exitosa (`built in 6.09s`), 42 pruebas de backend pytest aprobadas sin regresiones.

# Plan: Pivot completo a dataset de IPS (datos.gov.co), Supabase eliminado

## Contexto y decisiones ya tomadas

- **Fuente única**: dataset `s2ru-bqt6` de datos.gov.co — *"Relación de IPS públicas y privadas según el nivel de atención y capacidad instalada"* (MinSalud/REPS). 41.427 filas, ~9.320 prestadores, datos congelados desde **2022-11-21**.
- **Acceso: SoQL en vivo** contra `https://www.datos.gov.co/resource/s2ru-bqt6.json` (SODA). La agregación la ejecuta Socrata → se mantiene el invariante *"el LLM nunca calcula números"*.
  - **NUNCA usar** `api/v3/views/s2ru-bqt6/query.json`: ignora `$limit` y devuelve 36 MB.
- **Supabase se elimina por completo** (servicio, credenciales, migraciones, MCP, docs).
- **Pivot completo de dominio**: router, prompts, schemas, dashboard y frontend pasan de "sesiones/engagement/frustración" a "IPS/salud colombiana".
- **Se elimina el bloque de pitch turístico** (`PitchSection.jsx`, `FrictionReplayModal.jsx`, `frictionDiagnostics.js`).
- **Knowledge se borra y se rehace**: nuevo `knowledge_service` con directrices propias del asistente de IPS, en archivo local (sin Supabase).

### Verificaciones hechas contra la API (todas responden OK)

| Consulta | Resultado |
|---|---|
| `count(*)` | 41427 |
| `count(distinct c_digo_prestador)` | 9320 |
| `sum(num_cantidad_capacidad_instalada) where nom_grupo_capacidad='CAMAS'` | 97036 |
| `group by naturaleza` | Privada 25067 / Pública 16174 / Mixta 186 |
| `group by num_nivel_atencion` | 1: 12588, 2: 2424, 3: 1149, null: 25266 |
| `group by nom_grupo_capacidad` | CONSULTORIOS 16053, SALAS 7597, CAMAS 6738, AMBULANCIAS 5340, CAMILLAS 4409, UNIDAD MOVIL 694, SILLAS 596 |
| `where departamento='Bogotá D.C'` | 4647 (match acento exacto funciona) |
| `where lower(naturaleza)='publica'` | **0** — `lower()` NO quita acentos ⇒ los filtros se canonifican **en nuestro lado** al valor exacto del dataset |

### Columnas canónicas del dataset

`departamento`, `municipio`, `nombre_prestador`, `c_digo_prestador`, `nit_ips`, `naturaleza` (Privada/Pública/Mixta), `num_nivel_atencion` (1/2/3/null), `nom_grupo_capacidad` (CAMAS/CONSULTORIOS/SALAS/AMBULANCIAS/CAMILLAS/UNIDAD MOVIL/SILLAS), `num_cantidad_capacidad_instalada` (number), `nom_sede_ips`, `direcci_n`, `email`, `tel_fono`, `gerente`, `fecha_corte`, `fuente`, `c_digo_sede`, `n_mero_sede`.

---

## Fase 1 — Capa de datos (backend)

1. **Crear `backend/services/datosgov_service.py`** (reemplaza a `supabase_service.py`, que se borra):
   - `DATASET_URL = "https://www.datos.gov.co/resource/s2ru-bqt6.json"`.
   - `execute(spec) -> Dict`: construye SoQL (`$select`, `$where`, `$group`, `$order`, `$limit`) y hace GET con `httpx.AsyncClient(timeout=10)`.
   - Operaciones deterministas (las nuevas "RPC"):
     - `count` — `count(*)` con filtros `$where`.
     - `group_count` — `count(*) $group=<col> $order=count(*) DESC`.
     - `sum_capacity` — `sum(num_cantidad_capacidad_instalada)` con filtros y `$group` opcional.
     - `math` — `avg/min/max/sum` sobre `num_cantidad_capacidad_instalada` con filtros.
     - `list_distinct` — `$select=<col>,count(*) $group=<col>` (para "lista los departamentos/municipios").
     - `sample_records` — filas crudas con `$limit` (alimenta TOON y el dashboard).
   - Cache en memoria (TTL ~10 min, `dict` + timestamp): los datos llevan sin cambiar desde 2022, así que el cache es casi siempre hit.
   - Todos los retornos incluyen `"modo": "agregacion_determinista_socrata"` (o `"fuente": "datos.gov.co/s2ru-bqt6"`).
   - Si la red falla → `{"error": ..., "status": "sin_datos"}` **sin** LLM de por medio (el invariante prohíbe que el modelo rellene).
   - Manejo de valores: SoQL devuelve números como strings a veces → parsear a `int/float` antes de devolver.
2. **`backend/config.py`**: eliminar `SUPABASE_URL/KEY/SECRET_KEY`; añadir `DATOS_GOV_RESOURCE_URL` (default al dataset).
3. **`backend/services/normalization.py`** (reescribir):
   - `DEPARTAMENTO_ALIASES`: 33 departamentos + Bogotá, mapeando variantes sin acento/alias ("bogota" → `Bogotá D.C`, "n santander"/"norte de santander" → `Norte de Santander`, "valle" → `Valle del Cauca`, etc.). Matcher insensible a acentos y mayúsculas.
   - `NATURALEZA_ALIASES`: publico/pública/estatal → `Pública`; privado → `Privada`; mixto → `Mixta`.
   - `NIVEL_ATENCION_ALIASES`: "primario/1/nivel 1" → `"1"`, etc.
   - `GRUPO_CAPACIDAD_ALIASES`: cama/camas → `CAMAS`, consultorio → `CONSULTORIOS`, etc.
   - Eliminar `DEVICE_ALIASES` y el default peligroso "desconocido → Desktop".
   - Municipios: matcher genérico insensible a acentos (la comparación final se hace contra valor canonizado; si hay empate, filtrar por departamento).

## Fase 2 — Contratos (schemas)

4. **`backend/schemas/router_schemas.py`**:
   - `RPCIntentParams` → `QueryIntentParams` con campos nuevos: `operation` (`count|group_count|sum_capacity|math|list_distinct`), `group_by`, `departamento_filter`, `municipio_filter`, `naturaleza_filter`, `nivel_atencion_filter`, `grupo_capacidad_filter`, `math_operation`, `target_metric` (default `num_cantidad_capacidad_instalada`).
   - Eliminar `url_filter`, `country_filter`, `device_filter` y las descripciones de RPCs viejas.
   - `IntentRouterDecision.rpc_intent` → `query_intent`.
   - Ojo (trampa 3 de AGENTS.md): revisar `inline_refs()` en `llm_client.py` si Gemini vuelve a quejarse con los campos nuevos.
5. **`backend/schemas/insight_schemas.py`**: descripciones al nuevo dominio (`area` = "Cobertura Antioquia", `sentiment_and_friction_analysis` → renombrar a `analysis_summary` o actualizar descripción a "brechas de cobertura y capacidad").
6. **`backend/schemas/knowledge_schemas.py`**: `KnowledgeCategory` nuevo → `general`, `cobertura`, `capacidad`, `gestion`, `calidad_datos`. Borrar referencias a Supabase.
7. **`backend/schemas/api_schemas.py`**: `LatencyMetrics.supabase_rpc_latency_ms` → `datosgov_latency_ms`.

## Fase 3 — Router, Heavy Path y orquestación

8. **`backend/services/intent_router.py`** (reescribir textos, conservar mecánica):
   - `ROUTER_SYSTEM_PROMPT`: triggers redefinidos — `TRIGGER_KPIS` (conteos/agregados de IPS, camas, capacidad), `TRIGGER_INSIGHTS` (diagnóstico de cobertura/capacidad por región), `TRIGGER_MATH` (sumas/promedios de `num_cantidad_capacidad_instalada`), `TRIGGER_CLARIFICATION`. Reglas de extracción de filtros: `departamento`, `municipio`, `naturaleza`, `nivel de atención`, `grupo de capacidad`. Ejemplos tipo: «¿Cuántas camas hay en Antioquia?», «IPS públicas vs privadas en Bogotá», «Capacidad total de consultorios por departamento».
   - `_GLOSSARY` nuevo (12-13 términos): `ips`, `capacidad instalada`, `nivel de atención`, `naturaleza`, `reps`, `camas`, `consultorios`, `prestador`, `sede`, `departamento`, `municipio`, `ambulancias`, `cobertura`.
   - `_CAPABILITY_LIST` / `_small_talk_reply`: textos del nuevo dominio.
   - `_list_intent`: entidades → `departamentos`, `municipios`, `prestadores`, `grupos` (→ `operation=list_distinct`).
   - `_heuristic_fallback`: keywords de dominio (ips, cama, capacidad, hospital, prestador, departamento, nivel, publica/privada), extracción de departamento en vez de país, sin dispositivo; mensaje de "fuera de dominio" nuevo: *"Solo puedo analizar datos de IPS colombianas: departamentos, municipios, naturaleza, niveles de atención y capacidad instalada…"*; elegir operación por tema. **Conservar las confianzas fijas 0.85/0.88/0.90** (las usan los tests).
9. **`backend/services/insights_service.py`**:
   - `HEAVY_PATH_SYSTEM_PROMPT`: diagnóstico sobre cobertura y capacidad de salud; regla "NUNCA recalcules los KPIs" intacta.
   - `generate_insight`: bloque `=== 1. KPIS DETERMINISTAS VERIFICADOS (datos.gov.co / Socrata SoQL) ===` y serializar KPIs con `json.dumps(..., ensure_ascii=False, indent=2)` en vez de `f"{kpis}"` (mejora limpia de legibilidad).
   - `_mock_fallback_insight`: textos nuevos de dominio (sin checkout/rage clicks).
10. **`backend/main.py`**:
    - `_DEFAULT_RPC_BY_TRIGGER` → `_DEFAULT_OPERATION_BY_TRIGGER`.
    - Mapeo de parámetros → `operation`, `group_by` y filtros canonizados vía `normalization`.
    - `formatted_message` Fast Path: "La fuente pública datos.gov.co ejecutó la consulta SoQL determinista…".
    - **`GET /api/v1/dashboard`**: reconstruir con `asyncio.gather` sobre SoQL:
      - `total_registros` = count(*), `total_prestadores` = count(distinct), `total_camas` = sum where CAMAS, `total_consultorios` = sum where CONSULTORIOS.
      - `naturaleza_breakdown` = group_count por `naturaleza`.
      - `departamento_stats` = group_count top 12 por departamento (+ suma de capacidad por departamento con `$group`).
      - `grupo_capacidad_breakdown` = group_count por `nom_grupo_capacidad`.
      - `nivel_atencion_breakdown` = group_count por `num_nivel_atencion`.
      - `recent_records` = sample 8 filas.
      - **Mantener las claves raíz que el test de contrato ya espera** (`kpis`, `country_stats`→renombrar y actualizar test; ver Fase 5): se decide renombrar a `departamento_stats`, `naturaleza_breakdown`, etc., y actualizo el test en consecuencia.
    - `GET /api/v1/health`: bloque `database` → `fuente_datos` con `dataset: s2ru-bqt6`, `provider: datos.gov.co (Socrata SoQL)`, `data_updated_at: 2022-11-21`, `rows: 41427`. Quitar `rpcs_deployed`. Quitar `knowledge_auditoria.table` (apuntar al archivo local).
    - Mensaje de clarificación (L74-81) con ejemplos del nuevo dominio.
    - Log de arranque: `🗄️ Socrata SoQL Endpoint: ...` en vez de Supabase.
11. **Knowledge nuevo**: reescribir `backend/services/knowledge_service.py` para leer `backend/data/knowledge_ips.json` (mismo motor de matching regex + prioridad + recorte, sin red). Sembrar 6-7 directrices propias del asistente (triggers: `camas`, `nivel de atención`, `departamento`, `capacidad instalada`, `naturaleza`, `prestador`, `municipio`). `available` = archivo existe y parsea.
12. **Borrar** `backend/services/supabase_service.py`.

## Fase 4 — Frontend

13. **Eliminar**: `components/PitchSection.jsx`, `components/FrictionReplayModal.jsx`, `data/frictionDiagnostics.js`.
14. **`App.jsx`**: quitar imports y uso de pitch/modal/diagnósticos; textos: "Manizales, Caldas, Colombia" → header de dominio IPS; toast "Alerta de fricción/RageClicks" → quitar o reemplazar por aviso de datos (ej. "Fuente: datos.gov.co · datos desde nov 2022"); "Sesión Activa/Hackathon Team" → reemplazar; quitar badge "Eje Cafetero AI".
15. **`components/BIDashboard.jsx`**: reescribir el contenido (mantener layout/estética):
    - Título "RESUMEN ANALÍTICO DE SESIONES" → "CAPACIDAD INSTALADA DE IPS · COLOMBIA".
    - KPIs: `TOTAL IPS/REGISTROS`, `PRESTADORES`, `CAPACIDAD DE CAMAS`, `CONSULTORIOS` (gauge), tarjeta de `naturaleza` (Pública/Privada donut), `NIVEL DE ATENCIÓN`.
    - Tablas: "TOP DEPARTAMENTOS POR REGISTROS", "GRUPOS DE CAPACIDAD", "IPS DE EJEMPLO".
    - Quitar chips engagement/frustración/fricción, datos hardcodeados de turismo/sesiones y la pregunta de "volumen de sesiones"; reemplazar por preguntas del nuevo dominio (ej. «¿Cuántas camas hay en Antioquia?»).
    - Pies `grabaciones_analisis` → `datos.gov.co / s2ru-bqt6`.
16. **`components/ChatPanel.jsx`**: `GREETING` nuevo (sin portales turísticos de Caldas); `THINKING_STEPS` "Consultando datos de Supabase RPC…" → "Consultando datos.gov.co (SoQL)…"; header "CaldasUX Copilot" → "NEXO IA"; placeholder → "Pregunta por departamentos, camas, IPS públicas…".
17. **`components/AnswerCard.jsx`**: `FIELD_LABELS` nuevo para las claves del dominio IPS (`total_registros`, `total_prestadores`, `total_camas`, `departamento`, `municipio`, `naturaleza`, `num_nivel_atencion`, `nom_grupo_capacidad`, `num_cantidad_capacidad_instalada`, `valores_distintos`…); quitar regla `engagement → %` y labels de turismo; `VerifiedTag` "PostgreSQL Verificado" → "datos.gov.co verificado"; actualizar bloque `sentiment_and_friction_analysis`.
18. **`index.html`**: `<title>` nuevo; mantener la paleta Tailwind (es estética, no de dominio) pero revisar el token `caldas` del config. **`ThemeContext.jsx`**: renombrar clave `caldas_theme` → `nexo_theme` (bajo riesgo, con fallback a la clave vieja).
19. Regenerar `frontend/dist/` con `npm run build`.

## Fase 5 — Pruebas

20. **Nuevo `tests/test_datosgov_service.py`**: builder SoQL puro (sin red) — filtros se escapan bien (`'` → `''`), operaciones generan `$select/$group` correctos, parseo de números, cache TTL, manejo de error de red.
21. **`tests/test_api_endpoints.py`**: doblar `datosgov_service.execute/sample_records` en vez de `call_rpc`; queries de dominio ("¿Cuántas camas hay en Antioquia?"); contrato de dashboard con claves nuevas.
22. **`tests/test_router_contract.py`**: canonicalización de departamento (`bogota` → `Bogotá D.C`, `NORTE DE SANTANDER`…) y naturaleza (`publica` → `Pública`); confirmar confianzas fijas 0.85/0.88/0.90.
23. **`tests/test_router_definitions.py`**: glosario nuevo («¿qué es una IPS?», «¿qué es capacidad instalada?», «¿qué es el nivel de atención?» → respuesta; desconocida → lista de términos; fuera de dominio → clarificación con ejemplos nuevos).
24. **`tests/test_knowledge_service.py`**: fixtures con triggers del nuevo dominio apuntando al JSON local (el motor de matching se conserva).
25. **`tests/test_llm_live.py`**: consultas de dominio nuevo (marcado `live_llm`, no corre por defecto).
26. **`tests/conftest.py`**: conservar `FALLBACK_CONFIDENCES` y `FakeLLM`.

## Fase 6 — Limpieza y docs (obligatoria: hook pre-commit)

27. **Borrar** `supabase/migrations/` (directorio completo).
28. **`render.yaml`**: eliminar envVars `SUPABASE_URL/KEY/SECRET_KEY`; añadir `DATOS_GOV_RESOURCE_URL` si aplica (tiene default, opcional).
29. **`.env` local**: eliminar `SUPABASE_*` (no commitear, es gitignored, pero limpiar).
30. **`README.md`**: fuente de datos, bloque `.env` sin Supabase, cómo probar.
31. **`AGENTS.md`**: actualizar §1 (dominio), §2 (mapa: `datosgov_service.py`, sin `supabase/`), §3 (recorrido de consulta), §4 (optimización de tokens: URL con filtros → payloads KB, cache SoQL), §5 (comandos), §6 (trampas: acentos en filtros, `lower()` no quita acentos, `query.json` de 36 MB, datos congelados 2022), §7 (estado/pendientes), §8 (deploy).
32. **`ARQUITECTURA_FLUJO_INTENCIONES.md`**: §1 diagrama, §4.2 (Supabase → datos.gov/SoQL), §5 endpoints, §8 estado, **§10.1** (corregido: pivot + eliminación Supabase) y **§10.2** (pendientes: ver lista abajo), **§11** cierre de sesión.
33. **`opencode.json`**: quitar el MCP de Supabase (requiere la skill `customize-opencode` — hacerlo con ella o dejarlo como pendiente explícito).

### Pendientes que quedarán documentados (§10.2)
- Verificar en Render/Vercel tras push (trampa 9: deploy sin push).
- Sin CI (pendiente viejo, sigue vigente).
- `google.generativi` deprecado (sigue vigente).

## Orden de ejecución y verificación

1. Fase 1 → `python -c "import backend.services.datosgov_service"` + prueba manual de una consulta SoQL.
2. Fases 2-3 → `.\venv\Scripts\python.exe -c "import backend.main"`.
3. Fase 5 → `.\venv\Scripts\python.exe -m pytest -q` (todas verdes).
4. Arrancar uvicorn y probar en vivo:
   - `POST /api/v1/query` con «¿Cuántas camas hay en Antioquia?» → debe devolver 4245-regs/camas reales vía SoQL.
   - `GET /api/v1/dashboard` → KPIs nuevos, `total_prestadores ≈ 9320`, `total_camas ≈ 97036`.
   - `GET /api/v1/health` → `fuente_datos`, sin `SUPABASE` en ningún lado.
5. Fase 4 → `cd frontend; npm run lint; npm run build`.
6. Fase 6 → docs actualizados + `git status` sin archivos de Supabase pendientes.

## Riesgos

- **Acentos en filtros**: `lower()` de SoQL no normaliza; si un alias no está en el mapa, el filtro devuelve 0 filas en silencio (misma familia que la trampa 4 actual). Mitigación: mapa de alias completo + tests de canonicalización.
- **Gemini y schemas nuevos**: trampa 3 conocida; verificar `inline_refs()` si se usa Gemini (hoy el proveedor es Groq, riesgo bajo).
- **Latencia de red por consulta**: mitigada con cache TTL; si datos.gov.co cae, la respuesta es `sin_datos` explícita (nunca números del LLM).
- **Renombrar campos de contrato** (`rpc_intent` → `query_intent`, `supabase_rpc_latency_ms` → `datosgov_latency_ms`): el frontend no lee esos campos (AGENTS §4.5), impacto nulo en UX.

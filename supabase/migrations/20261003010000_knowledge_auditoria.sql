-- ==============================================================================
-- KNOWLEDGE DE AUDITORÍA PARAMETRIZABLE (Nexo IA)
-- Archivo: supabase/migrations/20261003010000_knowledge_auditoria.sql
--
-- Sustituye al dict hardcodeado de `knowledge_base.py` (v1). Alli el conocimiento
-- cortaba ANTES del LLM: `get_fixed_response()` devolvia una respuesta fija y la
-- consulta nunca llegaba al modelo. Aquí el conocimiento NO decide la ruta; solo
-- aporta contexto al prompt, de modo que el LLM sigue siendo quien clasifica.
-- ==============================================================================

CREATE TABLE IF NOT EXISTS public.knowledge_auditoria (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Clave de coincidencia. Se compara en minúsculas y sin acentos contra la
    -- consulta del usuario, igual que hace `normalization.strip_accents`.
    -- Debe ser una frase corta y estable: es el ancla del match.
    trigger_key TEXT NOT NULL UNIQUE,

    -- Categoría de auditoría. Permite filtrar el knowledge por contexto
    -- (p. ej. cargar solo 'friccion' para una consulta de fricción) en vez de
    -- inyectar el catálogo completo en cada llamada.
    categoria TEXT NOT NULL DEFAULT 'general',

    -- Ámbito geográfico o de mercado al que aplica la entrada, si aplica.
    -- 'GLOBAL' cuando la guía vale para cualquier mercado.
    mercado TEXT NOT NULL DEFAULT 'GLOBAL',

    -- Qué debe hacer el modelo cuando la entrada aplica. No contiene la
    -- respuesta: contiene la instrucción de análisis.
    -- Ej.: 'Cruzar tasa de DeadClicks con engagement por dispositivo antes de concluir.'
    directriz TEXT NOT NULL,

    -- Criterios de evidencia que el insight debe citar para sostener la
    -- conclusión. Alimenta el campo `evidence_kpi` del Heavy Path.
    criterios_evidencia TEXT,

    -- Peso de prioridad (1 = máxima). Ordena las coincidencias cuando varias
    -- entradas aplican a la misma consulta.
    prioridad SMALLINT NOT NULL DEFAULT 3,

    -- Permite desactivar una entrada sin borrarla.
    activo BOOLEAN NOT NULL DEFAULT TRUE
);

-- El fetch usa `activo = true ORDER BY prioridad, id`, así que un índice parcial
-- cubre el caso de lectura sin penalizar las entradas desactivadas.
CREATE INDEX IF NOT EXISTS idx_knowledge_auditoria_activa
    ON public.knowledge_auditoria (prioridad, id)
    WHERE activo = TRUE;

-- Búsqueda por categoría/mercado, que es el filtro que aplica el backend.
CREATE INDEX IF NOT EXISTS idx_knowledge_auditoria_ambito
    ON public.knowledge_auditoria (categoria, mercado)
    WHERE activo = TRUE;

-- ------------------------------------------------------------------------------
-- RLS: misma política de solo lectura que el resto del esquema, para que el
-- backend pueda consultarla sin quedar bloqueada por políticas.
-- ------------------------------------------------------------------------------
ALTER TABLE public.knowledge_auditoria ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir lectura anonima knowledge_auditoria" ON public.knowledge_auditoria;
CREATE POLICY "Permitir lectura anonima knowledge_auditoria"
    ON public.knowledge_auditoria
    FOR SELECT
    USING (true);

-- ------------------------------------------------------------------------------
-- SEMILLA — knowledge base mínimo de auditoría de fricción y engagement.
-- Corresponde a las métricas que realmente existen en el esquema:
-- metricas_marketing (DeadClicks/RageClicks) y grabaciones_analisis (engagement,
-- país, dispositivo, posible_frustracion).
-- ------------------------------------------------------------------------------
INSERT INTO public.knowledge_auditoria
    (trigger_key, categoria, mercado, directriz, criterios_evidencia, prioridad)
VALUES
    ('dead click',
     'friccion', 'GLOBAL',
     'Un Dead Click es un clic sobre un elemento sin respuesta. Suele indicar UI defectuosa o enlaces rotos, no confusión del usuario. No lo atribuir a falta de interés sin verificar el elemento.',
     'sessionsCount del elemento afectado y su share de sesiones con la métrica.', 1),

    ('rage click',
     'friccion', 'GLOBAL',
     'Los Rage Clicks se repiten sobre el mismo elemento. Es la señal más fuerte de fricción real. Contrastar siempre con engagement: RageClicks altos con engagement bajo confirman el problema; con engagement alto puede ser exploración legítima.',
     'porcentaje de sesiones con RageClicks y engagement medio de esas sesiones.', 1),

    ('checkout',
     'friccion', 'GLOBAL',
     'Revisar el flujo de pago antes de atribuir el abandono a falta de interés. Un pico de DeadClicks en checkout suele ser un campo, un botón o un medio de pago que falla.',
     'URL exacta con mayor afectación y el dispositivo donde se concentra.', 1),

    ('engagement bajo',
     'engagement', 'GLOBAL',
     'Cruzar engagement bajo con posible_frustracion antes de concluir. El engagement solo no distingue entre usuario confundido y usuario con objetivo rápido.',
     'standarized_engagement_score medio y porcentaje de sesiones con posible_frustracion = 1.', 2),

    ('movil',
     'dispositivo', 'GLOBAL',
     'Diferencias por dispositivo suelen ser diferencias de UX, no de usuario. Antes de culpar al mercado, descartar la hipótesis de diseño responsive.',
     'comparación de deadClicks por Device y engagement medio por dispositivo.', 2),

    ('pais',
     'mercado', 'GLOBAL',
     'Un mercado con baja fricción y engagement bajo señala un problema de oferta o de expectativa, no de interfaz. Un mercado con alta fricción y engagement bajo sí señala fricción.',
     'tasa de frustración por país cruzada con el engagement medio del mismo país.', 3),

    ('salto rapido',
     'comportamiento', 'GLOBAL',
     'Sesiones muy cortas con pocas páginas suelen indicar una landing incorrecta o decepción inmediata en el primer mensaje.',
     'duracion_sesion_segundos y recuento_paginas de esas sesiones.', 3)
ON CONFLICT (trigger_key) DO NOTHING;
-- ==============================================================================
-- MIGRACIÓN INICIAL PARA AMBIENTE DE PRUEBAS (NEXO IA / CLOUDLABS)
-- Archivo: supabase/migrations/20261003000000_init_schema_and_mock_data.sql
-- ==============================================================================

-- 1. TABLA: metricas_marketing
-- Usada en app.py y telegram_bot.py para medir Dead Clicks, Rage Clicks, etc.
CREATE TABLE IF NOT EXISTS public.metricas_marketing (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    "Url" TEXT NOT NULL,
    "metricName" TEXT NOT NULL,
    "sessionsWithMetricPercentage" NUMERIC(5,2) DEFAULT 0.0,
    "sessionsCount" INTEGER DEFAULT 0,
    "Device" TEXT DEFAULT 'Desktop',
    "OS" TEXT DEFAULT 'Windows'
);

-- 2. TABLA: grabaciones_analisis
-- Usada para comportamiento por sesión (país, páginas, engagement, frustración)
CREATE TABLE IF NOT EXISTS public.grabaciones_analisis (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    fecha DATE DEFAULT CURRENT_DATE,
    hora TIME DEFAULT CURRENT_TIME,
    pais TEXT NOT NULL,
    dispositivo TEXT DEFAULT 'Desktop',
    direccion_url_entrada TEXT DEFAULT '/',
    standarized_engagement_score NUMERIC(4,2) DEFAULT 0.50,
    recuento_paginas INTEGER DEFAULT 1,
    duracion_sesion_segundos INTEGER DEFAULT 60,
    posible_frustracion INTEGER DEFAULT 0 -- 1 = Alta frustración, 0 = Baja frustración
);

-- 3. POLÍTICAS DE SEGURIDAD (RLS)
-- Permitir lectura pública con la anon key para que el backend pueda consultar sin trabas
ALTER TABLE public.metricas_marketing ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.grabaciones_analisis ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir lectura anonima metricas" ON public.metricas_marketing;
CREATE POLICY "Permitir lectura anonima metricas" 
    ON public.metricas_marketing 
    FOR SELECT 
    USING (true);

DROP POLICY IF EXISTS "Permitir insercion anonima metricas" ON public.metricas_marketing;
CREATE POLICY "Permitir insercion anonima metricas" 
    ON public.metricas_marketing 
    FOR INSERT 
    WITH CHECK (true);

DROP POLICY IF EXISTS "Permitir lectura anonima grabaciones" ON public.grabaciones_analisis;
CREATE POLICY "Permitir lectura anonima grabaciones" 
    ON public.grabaciones_analisis 
    FOR SELECT 
    USING (true);

DROP POLICY IF EXISTS "Permitir insercion anonima grabaciones" ON public.grabaciones_analisis;
CREATE POLICY "Permitir insercion anonima grabaciones" 
    ON public.grabaciones_analisis 
    FOR INSERT 
    WITH CHECK (true);

-- 4. LIMPIEZA PREVIA DE DATOS DE PRUEBA
TRUNCATE TABLE public.metricas_marketing RESTART IDENTITY CASCADE;
TRUNCATE TABLE public.grabaciones_analisis RESTART IDENTITY CASCADE;

-- 5. DATOS FALSOS / MOCK REALISTAS PARA NEXO IA
-- Casos para métricas de marketing (Dead Clicks y Rage Clicks en URLs críticas)
INSERT INTO public.metricas_marketing ("Url", "metricName", "sessionsWithMetricPercentage", "sessionsCount", "Device", "OS")
VALUES
    ('/checkout/pago-tarjeta', 'RageClicks', 38.5, 450, 'Mobile', 'Android'),
    ('/checkout/pago-tarjeta', 'DeadClicks', 44.2, 510, 'Mobile', 'iOS'),
    ('/precios-planes-cloud', 'DeadClicks', 21.0, 310, 'Desktop', 'Windows'),
    ('/login-admin', 'RageClicks', 15.3, 120, 'Desktop', 'macOS'),
    ('/registro/paso-2', 'DeadClicks', 32.8, 640, 'Mobile', 'Android'),
    ('/laboratorios-virtuales', 'QuickBack', 12.1, 890, 'Desktop', 'Windows'),
    ('/carrito-compras', 'RageClicks', 27.4, 380, 'Mobile', 'Android'),
    ('/landing-campana-2026', 'DeadClicks', 8.5, 1250, 'Desktop', 'macOS'),
    ('/soporte-tecnico', 'RageClicks', 19.0, 210, 'Desktop', 'Windows'),
    ('/checkout/resumen', 'DeadClicks', 18.2, 290, 'Mobile', 'iOS');

-- Casos de grabaciones y análisis de comportamiento por sesión:
-- Incluye países con bajo engagement y alta frustración (ej. México y Argentina en móvil)
-- y países con alto engagement (ej. Colombia y España)
INSERT INTO public.grabaciones_analisis (fecha, hora, pais, dispositivo, direccion_url_entrada, standarized_engagement_score, recuento_paginas, duracion_sesion_segundos, posible_frustracion)
VALUES
    (CURRENT_DATE - INTERVAL '1 day', '09:14:22', 'México', 'Mobile', '/checkout/pago-tarjeta', 0.18, 2, 45, 1),
    (CURRENT_DATE - INTERVAL '1 day', '10:30:15', 'Colombia', 'Desktop', '/laboratorios-virtuales', 0.89, 9, 480, 0),
    (CURRENT_DATE - INTERVAL '1 day', '11:45:00', 'Argentina', 'Mobile', '/precios-planes-cloud', 0.22, 3, 58, 1),
    (CURRENT_DATE - INTERVAL '1 day', '12:15:33', 'España', 'Desktop', '/landing-campana-2026', 0.94, 12, 620, 0),
    (CURRENT_DATE - INTERVAL '1 day', '14:02:11', 'Chile', 'Desktop', '/registro/paso-2', 0.55, 5, 210, 0),
    (CURRENT_DATE, '08:20:10', 'México', 'Mobile', '/carrito-compras', 0.15, 2, 35, 1),
    (CURRENT_DATE, '08:45:50', 'Perú', 'Desktop', '/laboratorios-virtuales', 0.76, 7, 340, 0),
    (CURRENT_DATE, '09:12:05', 'Argentina', 'Mobile', '/checkout/pago-tarjeta', 0.20, 3, 52, 1),
    (CURRENT_DATE, '10:05:40', 'Colombia', 'Mobile', '/precios-planes-cloud', 0.81, 8, 410, 0),
    (CURRENT_DATE, '10:40:18', 'México', 'Desktop', '/soporte-tecnico', 0.31, 4, 110, 1),
    (CURRENT_DATE, '11:15:22', 'España', 'Mobile', '/landing-campana-2026', 0.88, 10, 530, 0),
    (CURRENT_DATE, '11:55:00', 'Chile', 'Mobile', '/checkout/pago-tarjeta', 0.28, 3, 75, 1);

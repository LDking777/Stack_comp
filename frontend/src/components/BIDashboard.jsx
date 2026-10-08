import { useState } from "react";
import {
  Calendar,
  ChevronDown,
  TrendingUp,
  ArrowUpRight,
  RefreshCw,
  AlertCircle,
} from "lucide-react";

/* ============================================================
   GAUGE CIRCULAR — Ocupación Hotelera (con onda decorativa)
   ============================================================ */
function CircularGauge({ percentage = 74 }) {
  const radius          = 42;
  const circumference   = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="gauge-container">
      <div className="gauge-graphic-wrap">
        {/* Onda decorativa */}
        <svg
          className="gauge-ambient-wave"
          viewBox="0 0 200 60"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="wave-fill" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#2c2c2e" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#2c2c2e" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="gauge-grad" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#1c1c1e" />
              <stop offset="100%" stopColor="#6b6b70" />
            </linearGradient>
          </defs>
          <path
            d="M0,38 C35,50 65,20 100,30 C135,40 165,18 200,32 L200,60 L0,60 Z"
            fill="url(#wave-fill)"
          />
          <path
            d="M0,38 C35,50 65,20 100,30 C135,40 165,18 200,32"
            fill="none"
            stroke="#2c2c2e"
            strokeWidth="2"
            strokeLinecap="round"
            opacity="0.8"
          />
        </svg>

        {/* Círculo */}
        <div className="gauge-circle-box">
          <svg className="gauge-svg" viewBox="0 0 100 100" aria-label={`Ocupación hotelera ${percentage}%`}>
            <defs>
              <linearGradient id="gauge-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#1c1c1e" />
                <stop offset="100%" stopColor="#6b6b70" />
              </linearGradient>
            </defs>
            <circle cx="50" cy="50" r={radius} className="gauge-track" strokeWidth="9" fill="none" />
            <circle
              cx="50" cy="50" r={radius}
              className="gauge-progress"
              strokeWidth="9"
              fill="none"
              stroke="url(#gauge-grad)"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              transform="rotate(-90 50 50)"
            />
          </svg>
          <div className="gauge-center-text">
            <span className="gauge-num">{percentage}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   DONUT CHART — Categorías Principales
   ============================================================ */
const DEFAULT_CATEGORIES = [
  { name: "Ruta del Café",       percentage: 38, color: "#1c1c1e" },
  { name: "Ecoturismo Nevados",  percentage: 28, color: "#3a3a3c" },
  { name: "Termalismo & Relax",  percentage: 20, color: "#6b6b70" },
  { name: "Eventos & Ferias",    percentage: 14, color: "#9a9aa0" },
];

function DonutCategoriesChart({ categories }) {
  const cats = categories || DEFAULT_CATEGORIES;
  let acc = 0;
  const gradientStops = cats.map((c) => {
    const start = acc;
    acc += c.percentage;
    return `${c.color} ${start}% ${acc}%`;
  }).join(", ");

  return (
    <div className="donut-section-wrap">
      <div className="donut-center-graphic">
        <div
          className="donut-circle"
          style={{ background: `conic-gradient(${gradientStops})` }}
          role="img"
          aria-label="Distribución de categorías turísticas"
        >
          <div className="donut-inner-hole" />
        </div>
      </div>
      <div className="donut-legend-grid">
        {cats.map((c) => (
          <div key={c.name} className="donut-legend-item">
            <span className="legend-chip" style={{ backgroundColor: c.color }} />
            <span className="legend-name">{c.name}</span>
            <span className="legend-pct">{c.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============================================================
   BIDASHBOARD — Componente principal del tablero
   ============================================================ */
export default function BIDashboard({ data, loading, error, onRetry, onInspect }) {
  const [period,          setPeriod]         = useState("Observatorio / Sept-Oct 2026");
  const [showPeriodMenu,  setShowPeriodMenu]  = useState(false);

  const PERIODS = [
    "Observatorio / Sept-Oct 2026",
    "Q3 Consolidado (Jul-Sep 2026)",
    "Año 2026 Acumulado",
  ];

  if (loading && !data) {
    return (
      <div className="dashboard-state-box">
        <RefreshCw size={26} className="spin text-blue" aria-hidden="true" />
        <p>Sincronizando métricas en tiempo real de Caldas 5.0…</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="dashboard-state-box">
        <AlertCircle size={28} className="text-amber" aria-hidden="true" />
        <h3>No se pudo conectar con el servidor analítico</h3>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", textAlign: "center", maxWidth: 340 }}>{error}</p>
        <button className="btn-caldas-secondary" onClick={onRetry}>
          <RefreshCw size={14} /> Reintentar conexión
        </button>
      </div>
    );
  }

  const kpis        = data?.kpis        || {};
  const categories  = data?.categories;
  const countryStats = data?.country_stats || [];
  const urlFriction  = data?.url_friction  || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>

      {/* ── Cabecera de sección ── */}
      <div className="dash-section-header">
        <h2 className="dash-section-title">
          RESUMEN ANALÍTICO OPERATIVO (MANIZALES/CALDAS)
        </h2>

        <div className="period-dropdown-wrap">
          <button
            id="period-selector"
            className="period-dropdown-btn"
            onClick={() => setShowPeriodMenu((v) => !v)}
            aria-haspopup="listbox"
            aria-expanded={showPeriodMenu}
          >
            <Calendar size={13} />
            {period}
            <ChevronDown size={13} />
          </button>

          {showPeriodMenu && (
            <div className="period-menu-popup" role="listbox" aria-label="Seleccionar periodo">
              {PERIODS.map((p) => (
                <button
                  key={p}
                  role="option"
                  aria-selected={period === p}
                  className={period === p ? "active" : ""}
                  onClick={() => { setPeriod(p); setShowPeriodMenu(false); }}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ── GRID PRINCIPAL ── */}
      <div className="caldas-grid">

        {/* Card 1 — Visitantes Totales */}
        <article
          className="caldas-card card-kpi cursor-pointer"
          onClick={() => onInspect?.("¿Cómo se distribuyen los 142.5K visitantes totales en el Q3 de Caldas?")}
          role="button"
          tabIndex={0}
          aria-label="Visitantes Totales - ver análisis"
        >
          <div className="card-top-label">Visitantes Totales (Q3)</div>
          <div className="card-main-stat">
            <span className="stat-large">{kpis.formatted_total_sesiones || "142.5K"}</span>
          </div>
          <div className="card-bottom-sub">
            <span>Visitantes Totales</span>
            <span className="stat-growth-tag">
              <TrendingUp size={12} /> +12.4%
            </span>
          </div>
        </article>

        {/* Card 2 — Gauge Ocupación Hotelera */}
        <article
          className="caldas-card card-gauge cursor-pointer"
          onClick={() => onInspect?.("¿Cuál fue la tasa de ocupación promedio en Manizales en septiembre?")}
          role="button"
          tabIndex={0}
          aria-label="Ocupación Hotelera - ver análisis"
        >
          <div className="card-top-label">Ocupación Hotelera</div>
          <CircularGauge percentage={kpis.ocupacion_hotelera_pct || 74} />
        </article>

        {/* Card 3 — Ocupación Q3 */}
        <article
          className="caldas-card card-kpi cursor-pointer"
          onClick={() => onInspect?.("Explica el volumen de ocupación hotelera en Q3 y la demanda turística en Caldas")}
          role="button"
          tabIndex={0}
          aria-label="Ocupación hotelera Q3 - ver análisis"
        >
          <div className="card-top-label">Ocupación hotelera (Q3)</div>
          <div className="card-main-stat">
            <span className="stat-large">{kpis.ocupacion_q3 || "876.8K"}</span>
          </div>
          <div className="card-bottom-sub">
            <span>Estancias Registradas</span>
            <span className="stat-highlight-dot">● Alta Demanda</span>
          </div>
        </article>

        {/* Card 4 — Ingresos */}
        <article
          className="caldas-card card-kpi cursor-pointer"
          onClick={() => onInspect?.("Analiza los ingresos estimados de $31,383.900 COP y su impacto en la economía local")}
          role="button"
          tabIndex={0}
          aria-label="Ingresos estimados - ver análisis"
        >
          <div className="card-top-label">Ingresos Estimados</div>
          <div className="card-main-stat text-income">
            <span className="stat-large">{kpis.ingresos_estimados || "$31,383.900"}</span>
          </div>
          <div className="card-bottom-sub">
            <span>Ingresos</span>
            <span className="badge-estimated-pill">Visitantes Estimados</span>
          </div>
        </article>

        {/* Card 5 — Donut Categorías */}
        <article
          className="caldas-card card-donut cursor-pointer"
          onClick={() => onInspect?.("¿Cuáles son las categorías turísticas con mayor afluencia en Caldas?")}
          role="button"
          tabIndex={0}
          aria-label="Categorías principales - ver análisis"
        >
          <div className="card-top-label">Categorías Principales</div>
          <DonutCategoriesChart categories={categories} />
        </article>

        {/* Card 6 — Mercados por origen */}
        <article className="caldas-card card-table">
          <div className="card-top-label">
            <span>Mercados por Origen</span>
            <span className="card-micro-hint">PostgreSQL RPC</span>
          </div>

          <div className="mini-stats-table" role="table" aria-label="Estadísticas por país de origen">
            {countryStats.slice(0, 4).map((c) => (
              <div
                key={c.pais}
                className="mini-table-row"
                role="row"
                onClick={() => onInspect?.(`Analiza el comportamiento turístico del mercado de ${c.pais} en Caldas`)}
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && onInspect?.(`Analiza el comportamiento turístico del mercado de ${c.pais} en Caldas`)}
              >
                <span className="col-country" role="cell">{c.pais}</span>
                <span className="col-val" role="cell">{c.sesiones.toLocaleString()} vis.</span>
                <span className="col-bar-wrap" role="cell" aria-hidden="true">
                  <span
                    className="col-bar-fill"
                    style={{ width: `${Math.min(100, Math.round((c.sesiones / 90000) * 100))}%` }}
                  />
                </span>
                <span className="col-inspect" aria-hidden="true">
                  <ArrowUpRight size={13} />
                </span>
              </div>
            ))}
          </div>
        </article>

        {/* Card 7 — Fricción digital */}
        <article className="caldas-card card-table card-wide">
          <div className="card-top-label">
            <span>Puntos Críticos de Fricción Digital</span>
            <span className="badge-tag-amber">Fricción Operativa</span>
          </div>

          <div className="friction-mini-list">
            {urlFriction.length === 0 ? (
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", padding: "8px" }}>
                No hay eventos críticos de fricción en este periodo.
              </p>
            ) : (
              urlFriction.slice(0, 4).map((f, i) => (
                <div
                  key={i}
                  className="friction-item-row"
                  onClick={() => onInspect?.(`¿Por qué ocurre ${f.metrica} en ${f.url} y cómo lo solucionamos?`)}
                  role="button"
                  tabIndex={0}
                  aria-label={`Ver análisis de fricción en ${f.url}`}
                >
                  <div className="friction-item-info">
                    <span className="friction-url-text">{f.url}</span>
                    <span className="friction-badge-sub">{f.metrica} · {f.dispositivo}</span>
                  </div>
                  <div className="friction-stat-box">
                    <span className="friction-pct">{f.afectacion_pct}%</span>
                    <span className="friction-count">{f.sesiones_afectadas} ses.</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </article>

      </div>
    </div>
  );
}
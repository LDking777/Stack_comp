import { ArrowUpRight, AlertCircle, RefreshCw, Clock } from "lucide-react";

/* ============================================================
   GAUGE CIRCULAR — Engagement promedio (con onda decorativa)
   ============================================================ */
function CircularGauge({ percentage = 0 }) {
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
          <svg className="gauge-svg" viewBox="0 0 100 100" aria-label={`Engagement promedio ${percentage}%`}>
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
   DONUT CHART — Desglose por dispositivo
   ============================================================ */
function DonutChart({ segments }) {
  const total = segments.reduce((a, s) => a + (s.percentage || 0), 0);
  let acc = 0;
  const gradientStops = segments.map((s) => {
    const start = acc;
    acc += s.percentage;
    return `${s.color} ${start}% ${acc}%`;
  }).join(", ");

  const isEmpty = !segments.length || total <= 0;

  return (
    <div className="donut-section-wrap">
      <div className="donut-center-graphic">
        <div
          className="donut-circle"
          style={{ background: isEmpty ? "#ececef" : `conic-gradient(${gradientStops})` }}
          role="img"
          aria-label="Distribución de sesiones por dispositivo"
        >
          <div className="donut-inner-hole" />
        </div>
      </div>
      <div className="donut-legend-grid">
        {segments.map((s) => (
          <div key={s.name} className="donut-legend-item">
            <span className="legend-chip" style={{ backgroundColor: s.color }} />
            <span className="legend-name">{s.name}</span>
            <span className="legend-pct">{s.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============================================================
   Helpers de formato
   ============================================================ */
function fmtNum(n) {
  return (Number(n) || 0).toLocaleString("es-CO");
}

function fmtDuration(sec) {
  const s = Math.round(Number(sec) || 0);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return m > 0 ? `${m} min ${r} s` : `${s} s`;
}

const DEVICE_COLORS = ["#1c1c1e", "#6b6b70", "#9a9aa0"];

/* ============================================================
   BIDASHBOARD — Componente principal del tablero (datos reales)
   ============================================================ */
export default function BIDashboard({ data, loading, error, onRetry, onInspect }) {
  const kpis        = data?.kpis        || {};
  const countryStats = data?.country_stats || [];
  const deviceBreak = data?.device_breakdown || {};
  const urlFriction  = data?.url_friction  || [];

  const engagementPct = Math.round((Number(kpis.avg_engagement) || 0) * 100);

  const deviceSegments = (() => {
    const mobile = Number(deviceBreak.mobile) || 0;
    const desktop = Number(deviceBreak.desktop) || 0;
    if (!mobile && !desktop) return [];
    const total = mobile + desktop;
    return [
      { name: "Mobile",     percentage: Math.round((mobile * 100) / total), color: DEVICE_COLORS[0] },
      { name: "Desktop",    percentage: Math.round((desktop * 100) / total), color: DEVICE_COLORS[1] },
    ];
  })();

  if (loading && !data) {
    return (
      <div className="dashboard-state-box">
        <RefreshCw size={26} className="spin text-blue" aria-hidden="true" />
        <p>Sincronizando métricas de sesiones de usuario…</p>
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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>

      {/* ── Cabecera de sección ── */}
      <div className="dash-section-header">
        <h2 className="dash-section-title">
          RESUMEN ANALÍTICO DE SESIONES
        </h2>
        <span className="card-micro-hint">engagement · frustración · dispositivos · fricción</span>
      </div>

      {/* ── GRID PRINCIPAL ── */}
      <div className="caldas-grid">

        {/* Card 1 — Sesiones Totales */}
        <article
          className="caldas-card card-kpi cursor-pointer"
          onClick={() => onInspect?.("Analiza el total de sesiones y su comportamiento general")}
          role="button"
          tabIndex={0}
          aria-label="Sesiones totales - ver análisis"
        >
          <div className="card-top-label">Sesiones Totales</div>
          <div className="card-main-stat">
            <span className="stat-large">{fmtNum(kpis.total_sesiones)}</span>
          </div>
          <div className="card-bottom-sub">
            <span>grabaciones_analisis</span>
          </div>
        </article>

        {/* Card 2 — Gauge Engagement Promedio */}
        <article
          className="caldas-card card-gauge cursor-pointer"
          onClick={() => onInspect?.("¿Qué nivel de engagement tienen las sesiones y qué lo está afectando?")}
          role="button"
          tabIndex={0}
          aria-label="Engagement promedio - ver análisis"
        >
          <div className="card-top-label">Engagement Promedio</div>
          <CircularGauge percentage={engagementPct} />
        </article>

        {/* Card 3 — Tasa de Frustración */}
        <article
          className="caldas-card card-kpi cursor-pointer"
          onClick={() => onInspect?.("¿Por qué ocurre frustración en las sesiones y en qué páginas?")}
          role="button"
          tabIndex={0}
          aria-label="Tasa de frustración - ver análisis"
        >
          <div className="card-top-label">Tasa de Frustración</div>
          <div className="card-main-stat">
            <span className="stat-large">{fmtNum(kpis.frustration_rate)}%</span>
          </div>
          <div className="card-bottom-sub">
            <span>Sesiones con fricción</span>
          </div>
        </article>

        {/* Card 4 — Duración Promedio */}
        <article
          className="caldas-card card-kpi cursor-pointer"
          onClick={() => onInspect?.("Analiza la duración promedio de las sesiones por país y dispositivo")}
          role="button"
          tabIndex={0}
          aria-label="Duración promedio de sesión - ver análisis"
        >
          <div className="card-top-label">Duración Promedio</div>
          <div className="card-main-stat">
            <span className="stat-large" style={{ fontSize: "1.35rem" }}>
              <Clock size={14} aria-hidden="true" style={{ marginRight: 6, verticalAlign: "-1px" }} />
              {fmtDuration(kpis.avg_duration_sec)}
            </span>
          </div>
          <div className="card-bottom-sub">
            <span>Por sesión</span>
          </div>
        </article>

        {/* Card 5 — Donut Dispositivos */}
        <article
          className="caldas-card card-donut cursor-pointer"
          onClick={() => onInspect?.("Compara engagement en celular vs escritorio")}
          role="button"
          tabIndex={0}
          aria-label="Distribución por dispositivo - ver análisis"
        >
          <div className="card-top-label">Dispositivos</div>
          <DonutChart segments={deviceSegments} />
        </article>

        {/* Card 6 — Mercados por origen */}
        <article className="caldas-card card-table">
          <div className="card-top-label">
            <span>Sesiones por País</span>
            <span className="card-micro-hint">Agregación determinista</span>
          </div>

          <div className="mini-stats-table" role="table" aria-label="Estadísticas por país de origen">
            {countryStats.slice(0, 4).map((c) => (
              <div
                key={c.pais}
                className="mini-table-row"
                role="row"
                onClick={() => onInspect?.(`Analiza el engagement y la frustración del mercado de ${c.pais}`)}
                tabIndex={0}
                onKeyDown={(e) => e.key === "Enter" && onInspect?.(`Analiza el engagement y la frustración del mercado de ${c.pais}`)}
              >
                <span className="col-country" role="cell">{c.pais}</span>
                <span className="col-val" role="cell">{fmtNum(c.sesiones)} vis.</span>
                <span className="col-bar-wrap" role="cell" aria-hidden="true">
                  <span
                    className="col-bar-fill"
                    style={{ width: `${Math.min(100, Math.round((c.sesiones / Math.max(countryStats[0]?.sesiones, 1)) * 100))}%` }}
                  />
                </span>
                <span className="col-inspect" aria-hidden="true">
                  <ArrowUpRight size={13} />
                </span>
              </div>
            ))}
            {countryStats.length === 0 && (
              <p style={{ fontSize: "0.78rem", color: "var(--text-muted)", padding: "8px" }}>
                Sin datos de países en este periodo.
              </p>
            )}
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
                    <span className="friction-count">{fmtNum(f.sesiones_afectadas)} ses.</span>
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
import {
  ShieldCheck,
  Target,
  Lightbulb,
  MessageSquareText,
  AlertTriangle,
} from "lucide-react";

const FIELD_LABELS = {
  pais_filtrado:                    "País analizado",
  dispositivo_filtrado:             "Dispositivo",
  total_sesiones:                   "Sesiones analizadas",
  total_sesiones_alta_frustracion:  "Sesiones con frustración alta",
  promedio_engagement_score:        "Interés promedio",
  tasa_frustracion_porcentaje:      "Tasa de frustración",
  promedio_duracion_sesion:         "Permanencia promedio",
  promedio_paginas_vistas:          "Páginas vistas promedio",
  total_eventos:                    "Eventos registrados",
  tasa_ocupacion_promedio:          "Tasa de ocupación promedio",
  ocupacion_2025:                   "Ocupación 2025",
  ocupacion_2026:                   "Ocupación 2026",
  variacion_interanual:             "Variación interanual",
  periodo:                          "Periodo",
  region:                           "Región",
  alucinaciones_numericas:          "Verificación LLM",
  total_perdidas_cancelaciones:     "Pérdidas por cancelaciones",
  tasa_cancelacion:                 "Tasa de cancelación",
  canal_critico:                    "Canal crítico",
  visitantes_totales:               "Visitantes totales",
  ingresos_estimados:               "Ingresos estimados",
  ocupacion_promedio:               "Ocupación promedio",
  resultado:                        "Resultado",
  valor:                            "Valor",
  total:                            "Total",
};

const SKIP_FIELDS = new Set(["modo", "explicacion_determinista"]);

function humanizeKey(key) {
  return (
    FIELD_LABELS[key] ??
    key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())
  );
}

function humanizeValue(value, key) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (Array.isArray(value)) return `${value.length} registros`;
  if (typeof value === "object") return null;

  const num = Number(value);
  if (!Number.isNaN(num) && key) {
    if (key.includes("porcentaje") || key.includes("pct")) return `${value}%`;
    if (key.includes("engagement"))  return `${Math.round(num * 100)}%`;
    if (key.includes("duracion") && num > 90) {
      return `${Math.floor(num / 60)} min ${Math.round(num % 60)} s`;
    }
  }
  return String(value);
}

function VerifiedTag() {
  return (
    <span className="verified-tag">
      <ShieldCheck size={12} />
      PostgreSQL Verificado
    </span>
  );
}

function DeterministicAnswer({ kpis }) {
  const entries = Object.entries(kpis || {}).filter(
    ([key, value]) =>
      !SKIP_FIELDS.has(key) && (typeof value !== "object" || value === null),
  );

  if (entries.length === 0) {
    return (
      <p className="answer-text">
        No se encontraron registros para los filtros especificados.
      </p>
    );
  }

  return (
    <>
      <p className="answer-text">Datos verificados directamente desde la base de datos:</p>
      <div className="answer-metrics">
        {entries.map(([key, value]) => {
          const display = humanizeValue(value, key);
          if (display === null) return null;
          return (
            <div key={key} className="answer-metric">
              <span className="answer-metric-label">{humanizeKey(key)}</span>
              <span className="answer-metric-value">{display}</span>
            </div>
          );
        })}
      </div>
    </>
  );
}

function InsightAnswer({ insight }) {
  const impactClass = {
    ALTO:  "impact-high",
    MEDIO: "impact-mid",
    BAJO:  "impact-low",
  };

  return (
    <>
      <p className="answer-text">{insight.executive_summary}</p>

      {insight.sentiment_and_friction_analysis && (
        <div className="answer-callout">
          <MessageSquareText size={14} />
          <span>{insight.sentiment_and_friction_analysis}</span>
        </div>
      )}

      {insight.observations?.length > 0 && (
        <div className="answer-block">
          <span className="answer-block-title">
            <Target size={13} /> Hallazgos Clave
          </span>
          <ul className="finding-list">
            {insight.observations.map((o, i) => (
              <li key={i}>
                <div className="finding-top">
                  <strong>{o.area}</strong>
                  <span className={`label-badge ${impactClass[o.impact_level] || "impact-low"}`}>
                    {o.impact_level === "ALTO" ? "Alto impacto" :
                     o.impact_level === "MEDIO" ? "Medio impacto" : "Bajo impacto"}
                  </span>
                </div>
                <p style={{ fontSize: "0.76rem", color: "var(--text-secondary)", marginTop: "3px" }}>
                  {o.detail}
                </p>
                {o.evidence_kpi && (
                  <code className="finding-evidence">Respaldo: {o.evidence_kpi}</code>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {insight.recommendations?.length > 0 && (
        <div className="answer-block">
          <span className="answer-block-title">
            <Lightbulb size={13} /> Plan de Acción
          </span>
          <ol className="action-list">
            {insight.recommendations.map((r, i) => (
              <li key={i}>
                <span className="action-rank">{r.priority}</span>
                <div className="action-content">
                  <strong>{r.action}</strong>
                  <span className="action-outcome">Meta: {r.expected_outcome}</span>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </>
  );
}

export default function AnswerCard({ payload }) {
  if (!payload) return null;

  if (!payload.is_safe) {
    return (
      <div className="answer-safety">
        <AlertTriangle size={16} />
        <div>
          <strong>Consulta no procesable</strong>
          <p>{payload.formatted_message}</p>
        </div>
      </div>
    );
  }

  const hasInsight = Boolean(payload.qualitative_insight);
  const hasKpis    = Boolean(payload.verified_deterministic_kpis);

  return (
    <div className="answer-card">
      {hasInsight ? (
        <InsightAnswer insight={payload.qualitative_insight} />
      ) : hasKpis ? (
        <DeterministicAnswer kpis={payload.verified_deterministic_kpis} />
      ) : (
        <p className="answer-text">{payload.formatted_message}</p>
      )}

      {(hasInsight || hasKpis) && (
        <div className="answer-footer">
          <VerifiedTag />
        </div>
      )}
    </div>
  );
}
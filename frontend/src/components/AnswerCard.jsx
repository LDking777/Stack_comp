import { ShieldCheck, Target, Lightbulb, MessageSquareText, AlertTriangle } from "lucide-react";
import Markdown from "./Markdown";

const FIELD_LABELS = {
  pais_filtrado: "País analizado",
  dispositivo_filtrado: "Dispositivo",
  total_sesiones: "Sesiones analizadas",
  total_sesiones_alta_frustracion: "Sesiones con frustración alta",
  promedio_engagement_score: "Interés promedio",
  tasa_frustracion_porcentaje: "Tasa de frustración",
  promedio_duracion_sesion: "Permanencia promedio",
  promedio_paginas_vistas: "Páginas vistas promedio",
  total_eventos: "Eventos registrados",
  tasa_ocupacion_promedio: "Tasa de ocupación promedio",
  ocupacion_2025: "Ocupación 2025",
  ocupacion_2026: "Ocupación 2026",
  variacion_interanual: "Variación interanual",
  periodo: "Periodo",
  region: "Región",
  alucinaciones_numericas: "Verificación LLM",
  total_perdidas_cancelaciones: "Pérdidas por cancelaciones",
  tasa_cancelacion: "Tasa de cancelación",
  canal_critico: "Canal crítico",
  visitantes_totales: "Visitantes totales",
  ingresos_estimados: "Ingresos estimados",
  ocupacion_promedio: "Ocupación promedio",
  resultado: "Resultado",
  valor: "Valor",
  total: "Total",
  categoria: "Categoría",
  total_valores: "Valores distintos",
  valores_distintos: "Listado (con sesiones)",
};

const SKIP_FIELDS = new Set(["modo", "explicacion_determinista"]);

function humanizeKey(key) {
  return FIELD_LABELS[key] ?? key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function humanizeValue(value, key) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (Array.isArray(value)) return `${value.length} registros`;
  if (typeof value === "object") return null;

  const num = Number(value);
  if (!Number.isNaN(num) && key) {
    if (key.includes("porcentaje") || key.includes("pct")) return `${value}%`;
    if (key.includes("engagement")) return `${Math.round(num * 100)}%`;
    if (key.includes("duracion") && num > 90) {
      return `${Math.floor(num / 60)} min ${Math.round(num % 60)} s`;
    }
  }
  return String(value);
}

function VerifiedTag() {
  return (
    <span className="inline-flex items-center gap-1 mt-3 text-[10px] font-mono text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
      <ShieldCheck className="w-3 h-3" />
      PostgreSQL Verificado
    </span>
  );
}

function DeterministicAnswer({ kpis }) {
  const entries = Object.entries(kpis || {}).filter(
    ([key, value]) => !SKIP_FIELDS.has(key) && (typeof value !== "object" || value === null),
  );

  if (entries.length === 0) {
    return <p className="text-xs text-slate-500">No se encontraron registros para los filtros especificados.</p>;
  }

  return (
    <>
      <p className="text-xs text-slate-600 dark:text-slate-300 mb-2">Datos verificados directamente desde la base de datos:</p>
      <div className="grid grid-cols-2 gap-2">
        {entries.map(([key, value]) => {
          const display = humanizeValue(value, key);
          if (display === null) return null;
          return (
            <div key={key} className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 flex flex-col gap-1">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">{humanizeKey(key)}</span>
              <span className="text-xs font-mono font-bold text-slate-900 dark:text-white">{display}</span>
            </div>
          );
        })}
      </div>
    </>
  );
}

function InsightAnswer({ insight }) {
  const impactClass = {
    ALTO: "bg-rose-500/10 text-rose-600 border-rose-500/20",
    MEDIO: "bg-amber-500/10 text-amber-600 border-amber-500/20",
    BAJO: "bg-slate-500/10 text-slate-600 border-slate-500/20",
  };

  return (
    <div className="space-y-4">
      <div className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
        <Markdown text={insight.executive_summary} />
      </div>

      {insight.sentiment_and_friction_analysis && (
        <div className="p-3 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800/50 flex gap-2.5 text-indigo-900 dark:text-indigo-200">
          <MessageSquareText className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="text-xs leading-relaxed">
            <Markdown text={insight.sentiment_and_friction_analysis} />
          </div>
        </div>
      )}

      {insight.observations?.length > 0 && (
        <div>
          <span className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-white mb-2 uppercase tracking-wider">
            <Target className="w-3.5 h-3.5 text-rose-500" /> Hallazgos Clave
          </span>
          <ul className="space-y-2">
            {insight.observations.map((o, i) => (
              <li key={i} className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <div className="flex items-center justify-between mb-1">
                  <strong className="text-xs text-slate-900 dark:text-white">{o.area}</strong>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${impactClass[o.impact_level] || impactClass.BAJO}`}>
                    {o.impact_level === "ALTO" ? "Alto impacto" : o.impact_level === "MEDIO" ? "Medio impacto" : "Bajo impacto"}
                  </span>
                </div>
                <div className="text-[11px] text-slate-600 dark:text-slate-400 mt-1">
                  <Markdown text={o.detail} />
                </div>
                {o.evidence_kpi && (
                  <code className="block mt-2 px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded text-[10px] font-mono text-slate-500">Respaldo: {o.evidence_kpi}</code>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {insight.recommendations?.length > 0 && (
        <div>
          <span className="flex items-center gap-1.5 text-xs font-bold text-slate-900 dark:text-white mb-2 uppercase tracking-wider">
            <Lightbulb className="w-3.5 h-3.5 text-amber-500" /> Plan de Acción
          </span>
          <ol className="space-y-2">
            {insight.recommendations.map((r, i) => (
              <li key={i} className="flex gap-2 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                <span className="flex items-center justify-center w-5 h-5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-[10px] font-bold shrink-0">{r.priority}</span>
                <div className="flex flex-col gap-0.5">
                  <strong className="text-xs text-slate-900 dark:text-white">{r.action}</strong>
                  <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">Meta: {r.expected_outcome}</span>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

export default function AnswerCard({ payload }) {
  if (!payload) return null;

  if (!payload.is_safe) {
    return (
      <div className="flex gap-2.5 p-3 rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800/50 text-rose-900 dark:text-rose-200">
        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
        <div className="text-xs">
          <strong className="block mb-1">Consulta no procesable</strong>
          <p>{payload.formatted_message}</p>
        </div>
      </div>
    );
  }

  const hasInsight = Boolean(payload.qualitative_insight);
  const hasKpis = Boolean(payload.verified_deterministic_kpis);

  return (
    <div className="flex flex-col">
      {hasInsight ? (
        <InsightAnswer insight={payload.qualitative_insight} />
      ) : hasKpis ? (
        <DeterministicAnswer kpis={payload.verified_deterministic_kpis} />
      ) : (
        <div className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
          <Markdown text={payload.formatted_message} />
        </div>
      )}

      {(hasInsight || hasKpis) && (
        <VerifiedTag />
      )}
    </div>
  );
}
import { BarChart3, Map, Layers, Building2, Database, RefreshCw, ChevronRight, Activity, BedDouble, GitBranch } from "lucide-react";
import { playTone } from "../utils/soundEffects";
import { showToast } from "./ToastContainer";
import { useCountUp } from "../hooks/useCountUp";

const fmt = (value) =>
  Number(value || 0).toLocaleString("es-CO", { maximumFractionDigits: 0 });

function KpiCard({ label, value, hint, icon: Icon, isFloat = false, decimals = 0, onInspect, question }) {
  const animated = useCountUp(Number(value) || 0, 1600, isFloat, decimals);
  return (
    <div className="p-5 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200/80 dark:border-slate-800/80 shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition-all flex flex-col justify-between min-h-[8.5rem]">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{label}</span>
        <Icon className="w-4 h-4 text-slate-400" />
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-4xl font-extrabold font-mono text-slate-900 dark:text-white">
          {isFloat ? animated.toFixed(decimals) : fmt(animated)}
        </span>
      </div>
      <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800/50">
        <span className="text-[11px] font-mono text-slate-400">{hint}</span>
        {question && (
          <button
            onClick={() => { playTone("default"); onInspect(question); }}
            className="text-[11px] text-emerald-500 font-semibold hover:underline flex items-center gap-0.5"
          >
            Inspeccionar <ChevronRight className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
}

function BreakdownCard({ title, subtitle, items, valueKey, color, onInspect, question, max }) {
  const top = Math.max(max || 0, ...items.map((i) => Number(i[valueKey]) || 0), 1);
  return (
    <div className="p-6 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200/80 dark:border-slate-800/80 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">{title}</h2>
          {subtitle && <p className="text-[11px] text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
        {question && (
          <button
            onClick={() => { playTone("default"); onInspect(question); }}
            className="text-[11px] text-emerald-500 font-semibold hover:underline flex items-center gap-0.5 shrink-0"
          >
            Preguntar <ChevronRight className="w-3 h-3" />
          </button>
        )}
      </div>
      <div className="space-y-2.5">
        {items.length === 0 && (
          <p className="text-xs text-slate-400">Sin datos para mostrar.</p>
        )}
        {items.map((item) => {
          const value = Number(item[valueKey]) || 0;
          const pct = Math.round((value / top) * 100);
          return (
            <div key={String(item.valor)} className="group/item">
              <div className="flex items-center justify-between text-xs mb-1">
                <span className="font-medium text-slate-700 dark:text-slate-200 truncate pr-2">
                  {item.valor === null || item.valor === "" ? "Sin clasificar" : item.valor}
                </span>
                <span className="font-mono font-bold text-slate-900 dark:text-white">{fmt(value)}</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.max(pct, 2)}%` }}></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function BIDashboard({ data, loading, error, onRetry, onInspect, sidebarOpen, setSidebarOpen }) {
  const kpis = data?.kpis || {};
  const byDepartamento = data?.by_departamento || [];
  const byNaturaleza = data?.by_naturaleza || [];
  const byNivel = data?.by_nivel || [];
  const capacityByGrupo = data?.capacity_by_grupo || [];
  const recent = data?.recent_records || [];
  const fuente = data?.fuente || {};

  const navPrompt = (q) => { playTone("default"); setSidebarOpen(false); onInspect(q); };

  return (
    <>
      <aside className={`w-64 border-r border-slate-200 dark:border-slate-800/80 bg-white/70 dark:bg-[#0c0f14]/80 backdrop-blur-md shrink-0 flex-col justify-between transition-all z-30 ${sidebarOpen ? "flex absolute inset-y-0 left-0" : "hidden lg:flex"}`}>
        <div className="p-4 space-y-6">
          <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-slate-100/70 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800/60">
            <div className="w-7 h-7 rounded-lg bg-slate-900 dark:bg-emerald-500 text-white dark:text-slate-950 flex items-center justify-center font-black text-xs">
              N
            </div>
            <div className="truncate">
              <p className="font-bold text-xs tracking-tight leading-tight">Nexo IA</p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">Analítica de IPS · Colombia</p>
            </div>
          </div>

          <nav className="space-y-1">
            <button className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs bg-slate-200/80 dark:bg-slate-800 text-slate-900 dark:text-white font-semibold">
              <BarChart3 className="w-4 h-4 text-emerald-500" />
              <span>Dashboard</span>
            </button>
            <button onClick={() => navPrompt("Compara la cobertura de IPS por departamento en Colombia")} className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white font-medium transition-all">
              <Map className="w-4 h-4" />
              <span>Análisis territorial</span>
            </button>
            <button onClick={() => navPrompt("¿Cuál es la capacidad instalada total por tipo de unidad?")} className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white font-medium transition-all">
              <Layers className="w-4 h-4" />
              <span>Capacidad instalada</span>
            </button>
            <button onClick={() => navPrompt("Compara IPS públicas y privadas en el país")} className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white font-medium transition-all">
              <Building2 className="w-4 h-4" />
              <span>Públicas vs Privadas</span>
            </button>
            <button onClick={() => navPrompt("Lista los departamentos con más registros de IPS")} className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white font-medium transition-all">
              <GitBranch className="w-4 h-4" />
              <span>Listados</span>
            </button>
          </nav>
        </div>

        <div className="p-4 border-t border-slate-200 dark:border-slate-800/80">
          <div className="px-3 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[11px] text-emerald-600 dark:text-emerald-400">
            <span className="flex items-center gap-1.5 font-semibold">
              <Database className="w-3.5 h-3.5" /> Fuente verificada
            </span>
            <p className="mt-1 text-[10px] font-mono leading-snug">
              datos.gov.co · {fuente.dataset_id || "s2ru-bqt6"}
            </p>
          </div>
        </div>
      </aside>

      <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Dashboard</h1>
            <p className="text-xs font-mono uppercase tracking-wider text-slate-400 mt-1">Cobertura y capacidad de IPS en Colombia</p>
          </div>
          <button onClick={() => { playTone("default"); onRetry(); }} title="Recargar métricas" className="self-start p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-850 text-slate-600 dark:text-slate-300 transition-colors">
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-emerald-500" : ""}`} />
          </button>
        </div>

        {error && (
          <div className="p-4 mb-4 rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800/50 text-rose-900 dark:text-rose-200 text-xs">
            <strong className="block mb-1">No se pudo cargar el tablero</strong>
            {error}
          </div>
        )}

        {loading && !data && (
          <div className="text-xs text-slate-400 font-mono py-10 text-center">Cargando datos verificados…</div>
        )}

        {data && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4 mb-4">
              <KpiCard label="Sedes de IPS" value={kpis.total_registros} hint="registros REPS" icon={Database} onInspect={onInspect} question="¿Cuántas sedes de IPS hay en Colombia?" />
              <KpiCard label="Prestadores (IPS)" value={kpis.total_prestadores} hint="IPS distintas" icon={Building2} onInspect={onInspect} question="¿Cuántos prestadores de salud hay en Colombia?" />
              <KpiCard label="Departamentos" value={kpis.total_departamentos} hint="con oferta" icon={Map} onInspect={onInspect} question="Lista los departamentos con más registros de IPS" />
              <KpiCard label="Capacidad total" value={kpis.total_capacidad} hint="unidades instaladas" icon={Activity} onInspect={onInspect} question="¿Cuál es la capacidad instalada total por tipo de unidad?" />
              <KpiCard label="Camas" value={kpis.total_camas} hint="grupo CAMAS" icon={BedDouble} onInspect={onInspect} question="¿Cuántas camas hay en Colombia?" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
              <BreakdownCard
                title="Sedes por departamento"
                subtitle="Top 10 por número de registros"
                items={byDepartamento.slice(0, 10)}
                valueKey="registros"
                color="bg-emerald-500"
                onInspect={onInspect}
                question="Analiza por qué algunos departamentos concentran más IPS que otros"
              />
              <BreakdownCard
                title="Capacidad instalada por tipo"
                subtitle="Suma de unidades por grupo"
                items={capacityByGrupo}
                valueKey="capacidad"
                color="bg-slate-700 dark:bg-slate-300"
                onInspect={onInspect}
                question="¿Qué tipo de capacidad instalada predomina en el país?"
              />
              <BreakdownCard
                title="Naturaleza de las IPS"
                subtitle="Públicas, privadas y mixtas"
                items={byNaturaleza}
                valueKey="registros"
                color="bg-amber-500"
                onInspect={onInspect}
                question="Compara IPS públicas y privadas en el país"
              />
              <BreakdownCard
                title="Nivel de atención"
                subtitle="1 primario · 2 medio · 3 alto"
                items={byNivel}
                valueKey="registros"
                color="bg-rose-500"
                onInspect={onInspect}
                question="¿Cuántas IPS de nivel 3 hay en el país?"
              />
            </div>

            <div className="p-6 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200/80 dark:border-slate-800/80 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">Muestra analítica de capacidad</h2>
                  <p className="text-[11px] text-slate-400 mt-0.5">Ubicación y tipo de recurso, sin identificadores de IPS</p>
                </div>
                <button onClick={() => { playTone("default"); onInspect("Desglosa la capacidad instalada por departamento y tipo de recurso"); }} className="text-[11px] text-emerald-500 font-semibold hover:underline flex items-center gap-0.5">
                  Consultar distribución <ChevronRight className="w-3 h-3" />
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-200 dark:border-slate-800">
                      <th className="py-2 pr-4 font-semibold">Departamento</th>
                      <th className="py-2 pr-4 font-semibold">Municipio</th>
                      <th className="py-2 pr-4 font-semibold">Naturaleza</th>
                      <th className="py-2 pr-4 font-semibold">Nivel</th>
                      <th className="py-2 pr-4 font-semibold">Grupo</th>
                      <th className="py-2 pr-4 font-semibold">Descripción</th>
                      <th className="py-2 pr-4 font-semibold text-right">Cantidad</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((r, i) => (
                      <tr key={i} className="border-b border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="py-2 pr-4 text-slate-700 dark:text-slate-200">{r.departamento || "—"}</td>
                        <td className="py-2 pr-4 text-slate-500 dark:text-slate-400">{r.municipio || "—"}</td>
                        <td className="py-2 pr-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">{r.naturaleza || "—"}</span>
                        </td>
                        <td className="py-2 pr-4 text-slate-500 dark:text-slate-400">{r.num_nivel_atencion || "—"}</td>
                        <td className="py-2 pr-4 text-slate-500 dark:text-slate-400">{r.nom_grupo_capacidad || "—"}</td>
                        <td className="py-2 pr-4 text-slate-500 dark:text-slate-400">{r.nom_descripcion_capacidad || "—"}</td>
                        <td className="py-2 pr-4 text-right tabular-nums text-slate-700 dark:text-slate-200">{r.num_cantidad_capacidad_instalada || "0"}</td>
                      </tr>
                    ))}
                    {recent.length === 0 && (
                      <tr>
                        <td colSpan={7} className="py-6 text-center text-slate-400">Sin registros disponibles.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/50 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400 font-mono">
                <span>{fuente.nombre}</span>
                <span
                  className="cursor-pointer hover:text-emerald-500"
                  onClick={() => showToast("Fuente de datos", `${fuente.fuente} · corte ${fuente.data_updated_at}`)}
                >
                  corte {fuente.data_updated_at}
                </span>
              </div>
            </div>
          </>
        )}
      </main>
    </>
  );
}

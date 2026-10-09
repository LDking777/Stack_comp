import { useState, useEffect } from "react";
import { BarChart3, Map, TrendingUp, Layers, Sliders, Settings2, RefreshCw, ChevronRight, Activity, Clock, ArrowUpRight } from "lucide-react";
import { playTone } from "../utils/soundEffects";
import { showToast } from "./ToastContainer";

export default function BIDashboard({ data, loading, error, onRetry, onInspect, onFrictionClick, activeNav, handleNavClick, sidebarOpen, setSidebarOpen }) {
  const kpis = data?.kpis || {};
  const countryStats = data?.country_stats || [];
  const deviceBreak = data?.device_breakdown || {};
  const urlFriction = data?.url_friction || [];

  const [timeRange, setTimeRange] = useState("24h");

  const setTimeRangeWithToast = (range) => {
    setTimeRange(range);
    playTone('click');
    showToast("Filtro Aplicado", `Mostrando datos de los últimos ${range}`, "success");
  };

  const handleRefresh = () => {
    playTone('click');
    onRetry();
  };

  const engagementPct = kpis.avg_engagement ? Math.round(Number(kpis.avg_engagement) * 100) : 51;
  const totalSessions = kpis.total_sessions || 12;

  return (
    <>
      <aside className={`w-64 border-r border-slate-200 dark:border-slate-800/80 bg-white/70 dark:bg-[#0c0f14]/80 backdrop-blur-md shrink-0 flex-col justify-between transition-all z-30 ${sidebarOpen ? 'flex absolute inset-y-0 left-0' : 'hidden lg:flex'}`}>
        <div className="p-4 space-y-6">
          {/* [NOMBRE PROVISIONAL]: Reemplazar cuando se definan los puntos de la hackathon */}
          <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-slate-100/70 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800/60">
            <div className="w-7 h-7 rounded-lg bg-slate-900 dark:bg-emerald-500 text-white dark:text-slate-950 flex items-center justify-center font-black text-xs">
              HP
            </div>
            <div className="truncate">
              <p className="font-bold text-xs tracking-tight leading-tight">Hackathon Propuesta</p>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">Hub Analítico Caldas</p>
            </div>
          </div>

          <nav className="space-y-1">
            <button onClick={() => handleNavClick('dashboard')} className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs transition-all ${activeNav === 'dashboard' ? 'bg-slate-200/80 dark:bg-slate-800 text-slate-900 dark:text-white font-semibold' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-850 hover:text-slate-900 dark:hover:text-white font-medium'}`}>
              <BarChart3 className={`w-4 h-4 ${activeNav === 'dashboard' ? 'text-emerald-500' : ''}`} />
              <span>Dashboard</span>
            </button>
            <button onClick={() => handleNavClick('regional')} className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs transition-all ${activeNav === 'regional' ? 'bg-slate-200/80 dark:bg-slate-800 text-slate-900 dark:text-white font-semibold' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-850 hover:text-slate-900 dark:hover:text-white font-medium'}`}>
              <Map className="w-4 h-4" />
              <span>Análisis Regional</span>
            </button>
            <button onClick={() => handleNavClick('kpis')} className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs transition-all ${activeNav === 'kpis' ? 'bg-slate-200/80 dark:bg-slate-800 text-slate-900 dark:text-white font-semibold' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-850 hover:text-slate-900 dark:hover:text-white font-medium'}`}>
              <TrendingUp className="w-4 h-4" />
              <span>KPIs de Turismo</span>
            </button>
            <button onClick={() => handleNavClick('ops')} className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs transition-all ${activeNav === 'ops' ? 'bg-slate-200/80 dark:bg-slate-800 text-slate-900 dark:text-white font-semibold' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-850 hover:text-slate-900 dark:hover:text-white font-medium'}`}>
              <Layers className="w-4 h-4" />
              <span>Operaciones</span>
            </button>
            <button onClick={() => handleNavClick('config')} className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs transition-all ${activeNav === 'config' ? 'bg-slate-200/80 dark:bg-slate-800 text-slate-900 dark:text-white font-semibold' : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-850 hover:text-slate-900 dark:hover:text-white font-medium'}`}>
              <Sliders className="w-4 h-4" />
              <span>Configuración</span>
            </button>
          </nav>
        </div>

        <div className="p-4 border-t border-slate-200 dark:border-slate-800/80">
          <button onClick={() => handleNavClick('config')} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-850 transition-all">
            <Settings2 className="w-4 h-4" />
            <span>Ajustes del Sistema</span>
          </button>
          <div className="mt-3 px-3 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[11px] text-emerald-600 dark:text-emerald-400 flex items-center justify-between">
            <span>SDK Estado</span>
            <span className="font-mono font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span> Activo
            </span>
          </div>
        </div>
      </aside>

      <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full overflow-y-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Dashboard</h1>
            <p className="text-xs font-mono uppercase tracking-wider text-slate-400 mt-1">RESUMEN ANALÍTICO DE SESIONES</p>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="flex items-center bg-slate-200/70 dark:bg-slate-800 p-1 rounded-xl text-xs font-medium">
              <button onClick={() => setTimeRangeWithToast('24h')} className={`px-3 py-1 rounded-lg ${timeRange === '24h' ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-900 dark:text-white font-semibold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}`}>24h</button>
              <button onClick={() => setTimeRangeWithToast('7d')} className={`px-3 py-1 rounded-lg ${timeRange === '7d' ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-900 dark:text-white font-semibold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}`}>7d</button>
              <button onClick={() => setTimeRangeWithToast('30d')} className={`px-3 py-1 rounded-lg ${timeRange === '30d' ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-900 dark:text-white font-semibold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}`}>30d</button>
            </div>
            
            <button onClick={handleRefresh} title="Recargar métricas en vivo" className="p-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-850 text-slate-600 dark:text-slate-300 transition-colors">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-emerald-500' : ''}`} />
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 text-[11px] text-slate-400 font-mono mb-4">
          <span className="hover:text-emerald-500 cursor-pointer transition-colors" onClick={() => showToast('Filtro Activo', 'Filtrando sesiones por engagement de usuario')}>engagement</span>
          <span>•</span>
          <span className="text-rose-500 font-bold hover:underline cursor-pointer" onClick={() => showToast('Filtro Activo', 'Mostrando únicamente eventos clasificados con frustración alta')}>frustración</span>
          <span>•</span>
          <span className="hover:text-emerald-500 cursor-pointer transition-colors">dispositivos</span>
          <span>•</span>
          <span className="hover:text-emerald-500 cursor-pointer transition-colors">fricción</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="p-6 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200/80 dark:border-slate-800/80 shadow-sm relative group hover:border-slate-300 dark:hover:border-slate-700 transition-all flex flex-col justify-between h-44">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">SESIONES TOTALES</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-500 font-semibold flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" /> +14%
                </span>
              </div>
              <div className="mt-2 flex items-baseline gap-3">
                <span className="text-4xl font-extrabold font-mono text-slate-900 dark:text-white">{totalSessions}</span>
                <span className="text-xs text-slate-400">muestras activas</span>
              </div>
            </div>
            
            <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800/50">
              <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                grabaciones_analisis
              </span>
              <button onClick={() => onInspect("¿Qué puedes decirme sobre el volumen de sesiones actual?")} className="text-[11px] text-emerald-500 font-semibold hover:underline flex items-center gap-0.5">
                Inspeccionar <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200/80 dark:border-slate-800/80 shadow-sm relative group hover:border-slate-300 dark:hover:border-slate-700 transition-all flex flex-col justify-between h-44">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">ENGAGEMENT PROMEDIO</span>
              <Activity className="w-4 h-4 text-slate-400" />
            </div>
            
            <div className="flex items-center justify-center my-auto">
              <div className="relative flex items-center justify-center">
                <div className="w-20 h-20 rounded-full border-4 border-slate-200 dark:border-slate-800 border-t-slate-900 dark:border-t-white flex items-center justify-center shadow-inner">
                  <span className="text-xl font-bold font-mono text-slate-900 dark:text-white">{engagementPct}%</span>
                </div>
              </div>
            </div>

            <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden relative">
              <div className="absolute inset-0 bg-gradient-to-r from-slate-400 via-slate-700 to-slate-400 dark:from-slate-600 dark:via-slate-200 dark:to-slate-600 opacity-60"></div>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200/80 dark:border-slate-800/80 shadow-sm relative group hover:border-rose-500/30 transition-all flex flex-col justify-between h-44">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">TASA DE FRUSTRACIÓN</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                CRÍTICO
              </span>
            </div>
            
            <div className="mt-2">
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-extrabold font-mono text-slate-900 dark:text-white">50.0%</span>
                <span className="text-xs text-rose-500 font-medium">alerta activa</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800/50">
              <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
                Sesiones con fricción
              </span>
              <span className="text-[10px] font-mono bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-slate-500">6 / 12 ses.</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="p-6 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200/80 dark:border-slate-800/80 shadow-sm relative group hover:border-slate-300 dark:hover:border-slate-700 transition-all flex flex-col justify-between h-48">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">DURACIÓN PROMEDIO</span>
              <Clock className="w-4 h-4 text-slate-400" />
            </div>

            <div className="my-auto flex items-center gap-2">
              <Clock className="w-6 h-6 text-slate-500 dark:text-slate-400" />
              <span className="text-3xl font-extrabold font-mono text-slate-900 dark:text-white">4 min 7 s</span>
            </div>

            <div className="pt-3 border-t border-slate-100 dark:border-slate-800/50 flex items-center justify-between text-[11px] text-slate-400">
              <span>Por sesión</span>
              <span className="font-mono text-emerald-500">+18s vs semana pasada</span>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200/80 dark:border-slate-800/80 shadow-sm relative group hover:border-slate-300 dark:hover:border-slate-700 transition-all flex flex-col justify-between h-48">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">DISPOSITIVOS</span>
              <span className="text-[10px] text-slate-400 font-mono">Cuota de Tráfico</span>
            </div>

            <div className="flex items-center justify-center my-auto gap-4">
              <div className="w-20 h-20 rounded-full flex items-center justify-center relative overflow-hidden" style={{ background: 'conic-gradient(#0f172a 0% 58%, #94a3b8 58% 100%)' }}>
                <div className="w-12 h-12 bg-white dark:bg-[#12161f] rounded-full absolute z-10"></div>
                {/* Dark mode adjustments done via CSS usually, but we keep it static for the mockup */}
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800/50 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-slate-900 inline-block"></span>
                <span className="text-slate-600 dark:text-slate-300 font-medium">Mobile</span>
                <span className="font-mono font-bold text-slate-900 dark:text-white ml-1">58%</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-slate-400 inline-block"></span>
                <span className="text-slate-600 dark:text-slate-300 font-medium">Desktop</span>
                <span className="font-mono font-bold text-slate-900 dark:text-white ml-1">42%</span>
              </div>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200/80 dark:border-slate-800/80 shadow-sm relative group hover:border-slate-300 dark:hover:border-slate-700 transition-all flex flex-col justify-between h-48">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">SESIONES POR PAÍS</span>
              <span className="text-[10px] font-mono text-slate-400">Agregación determinista</span>
            </div>

            <div className="space-y-2 mt-2">
              {[
                { name: 'México', vis: 3, w: '100%' },
                { name: 'Colombia', vis: 2, w: '66%' },
                { name: 'Argentina', vis: 2, w: '66%' },
                { name: 'España', vis: 2, w: '66%' }
              ].map(country => (
                <div key={country.name} className="flex items-center justify-between text-xs group/item hover:bg-slate-50 dark:hover:bg-slate-800/50 p-1 rounded-md transition-colors cursor-pointer" onClick={() => showToast('Desglose de País', `Datos detallados de ${country.name}`)}>
                  <span className="font-medium text-slate-700 dark:text-slate-200">{country.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-mono text-[11px]">{country.vis} vis.</span>
                    <div className="w-16 h-1.5 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden">
                      <div className="h-full bg-slate-800 dark:bg-slate-200 rounded-full" style={{ width: country.w }}></div>
                    </div>
                    <ArrowUpRight className="w-3 h-3 text-slate-400" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200/80 dark:border-slate-800/80 shadow-sm mt-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">PUNTOS CRÍTICOS DE FRICCIÓN DIGITAL</h2>
              <p className="text-[11px] text-slate-400 mt-0.5">Toca cualquier punto para reproducir la sesión simulada y ver el diagnóstico de IA</p>
            </div>
            <span className="text-[11px] font-mono px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 font-semibold">
              FRICCIÓN OPERATIVA
            </span>
          </div>

          <div className="space-y-2.5">
            {[
              { url: '/checkout/pago-tarjeta', type: 'DeadClicks', label: 'DeadClicks · Mobile', color: 'bg-rose-500', pct: '44.2%', ses: '510', desc: 'Botón de confirmación de pago no responde a eventos táctiles.' },
              { url: '/checkout/pago-tarjeta', type: 'RageClicks', label: 'RageClicks · Mobile', color: 'bg-amber-500', pct: '38.5%', ses: '450', desc: 'Usuarios tocan más de 4 veces por segundo en el botón de pagar con PSE.' },
              { url: '/registro/paso-2', type: 'DeadClicks', label: 'DeadClicks · Mobile', color: 'bg-rose-500', pct: '32.8%', ses: '640', desc: 'Selector de fecha para tour en Nevado del Ruiz bloqueado por capa modal.' },
              { url: '/carrito-compras', type: 'RageClicks', label: 'RageClicks · Mobile', color: 'bg-amber-500', pct: '27.4%', ses: '380', desc: 'El botón para modificar cupos de pasadía no refleja cambio inmediato.' }
            ].map((item, idx) => (
              <div key={idx} onClick={() => onFrictionClick({ url: item.url, metrica: item.type })} className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-emerald-500/50 dark:hover:border-emerald-500/50 bg-slate-50/50 dark:bg-slate-900/30 hover:bg-slate-100/60 dark:hover:bg-slate-900/60 transition-all cursor-pointer group flex items-center justify-between">
                <div>
                  <div className="font-mono text-sm font-semibold text-slate-900 dark:text-slate-200 group-hover:text-emerald-500 transition-colors">
                    {item.url}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 flex items-center gap-1.5">
                    <span className={`w-1.5 h-1.5 rounded-full ${item.color}`}></span>
                    <span>{item.label}</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono font-bold text-slate-900 dark:text-white text-base">{item.pct}</div>
                  <div className="text-xs font-mono text-slate-400">{item.ses} ses.</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
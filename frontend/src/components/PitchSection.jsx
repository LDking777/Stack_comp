import React from 'react';
import { Award, Play, Cpu, AlertOctagon, XCircle, CheckCheck, CheckCircle } from 'lucide-react';
import { playTone } from '../utils/soundEffects';

export default function PitchSection({ onExploreDashboard }) {
  return (
    <div id="view-pitch" className="w-full flex flex-col transition-all duration-300">
      
      {/* Hero Section */}
      <section className="relative overflow-hidden py-16 lg:py-24 border-b border-slate-200 dark:border-slate-800/80 bg-gradient-to-b from-white via-slate-50 to-slate-100/50 dark:from-[#0c0f14] dark:via-[#111620] dark:to-[#0c0f14]">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(16,185,129,0.15),rgba(255,255,255,0))] dark:bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(16,185,129,0.22),rgba(0,0,0,0))] pointer-events-none"></div>
        
        <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10 text-center">
          {/* Hackathon Badge */}
          {/* [NOMBRE PROVISIONAL]: Reemplazar cuando se definan los puntos de la hackathon */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 dark:bg-emerald-500/15 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-6">
            <Award className="w-4 h-4 text-emerald-500" />
            Hackathon Propuesta — Desafío Turismo Inteligente
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-[1.15] max-w-4xl mx-auto">
            Transformando datos de turismo en <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 via-teal-400 to-amber-500">experiencias digitales fluidas</span> y sin fricción.
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-slate-600 dark:text-slate-300 max-w-3xl mx-auto font-normal leading-relaxed">
            Plataforma determinista de telemetría de comportamiento y analítica preventiva para operadores, hoteles y portales turísticos de Caldas. Detecta abandono, frustración y micro-bloqueos en tiempo real.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <button onClick={() => { playTone('high'); onExploreDashboard(); }} className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-sm shadow-xl shadow-emerald-600/25 hover:shadow-emerald-600/40 transform hover:-translate-y-0.5 transition-all flex items-center gap-2">
              <Play className="w-4 h-4 fill-white" />
              Explorar Dashboard Interactivo
            </button>
            <a href="#solucion" className="px-6 py-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-850 text-slate-800 dark:text-slate-200 font-semibold text-sm transition-all flex items-center gap-2">
              <Cpu className="w-4 h-4 text-emerald-500" />
              Arquitectura & Propuesta
            </a>
          </div>

          {/* Quick Metrics Banner */}
          <div className="mt-14 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto">
            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-sm text-left">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Tasa de Pérdida Actual</p>
              <p className="text-2xl font-bold text-rose-500 mt-1 font-mono">50.0%</p>
              <p className="text-[11px] text-slate-500 mt-1">Visitantes con eventos de frustración</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-sm text-left">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Fricción en Checkouts</p>
              <p className="text-2xl font-bold text-amber-500 mt-1 font-mono">44.2%</p>
              <p className="text-[11px] text-slate-500 mt-1">DeadClicks en pasarelas móviles</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-sm text-left">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Ahorro Estimado</p>
              <p className="text-2xl font-bold text-emerald-500 mt-1 font-mono">+38%</p>
              <p className="text-[11px] text-slate-500 mt-1">En recuperación de reservas directas</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-sm text-left">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Latencia de Alerta</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1 font-mono">&lt; 1.2s</p>
              <p className="text-[11px] text-slate-500 mt-1">Detección heurística en cliente</p>
            </div>
          </div>
        </div>
      </section>

      {/* Problem vs Solution Section */}
      <section id="solucion" className="py-16 max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <span className="text-xs font-bold text-emerald-500 uppercase tracking-widest">Diagnóstico Regional</span>
          <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white mt-1 tracking-tight">El dilema digital del turismo en Caldas</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
            Miles de turistas internacionales y nacionales intentan reservar experiencias cafeteras, termales y ecoturismo, pero abandonan antes de pagar debido a fallas sutiles en la UX móvil.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* The Problem */}
          <div className="p-6 rounded-2xl bg-rose-500/5 border border-rose-500/20 relative overflow-hidden">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 text-rose-600 flex items-center justify-center">
                <AlertOctagon className="w-5 h-5" />
              </div>
              <h3 className="font-bold text-lg text-slate-900 dark:text-white">La Fricción Invisible (El Problema)</h3>
            </div>
            <ul className="space-y-3 text-sm text-slate-600 dark:text-slate-300">
              <li className="flex items-start gap-2.5">
                <XCircle className="w-4 h-4 text-rose-500 mt-0.5 shrink-0" />
                <span><strong>Dead Clicks en smartphones:</strong> Botones de pago o reserva que parecen clicables pero no responden por desfase de viewport o CSS.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <XCircle className="w-4 h-4 text-rose-500 mt-0.5 shrink-0" />
                <span><strong>Rage Clicks en Pasarelas:</strong> Usuarios tocando repetidamente el botón PSE o tarjeta creyendo que el sistema está colgado (38.5% en checkout).</span>
              </li>
              <li className="flex items-start gap-2.5">
                <XCircle className="w-4 h-4 text-rose-500 mt-0.5 shrink-0" />
                <span><strong>Desconexión de datos territoriales:</strong> Google Analytics tradicional sólo muestra que el usuario se fue, no <em>por qué</em> se frustró ni en cuál coordenada digital.</span>
              </li>
            </ul>
          </div>

          {/* The Solution */}
          <div className="p-6 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 relative overflow-hidden">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center">
                <CheckCheck className="w-5 h-5" />
              </div>
              {/* [NOMBRE PROVISIONAL]: Reemplazar cuando se definan los puntos de la hackathon */}
              <h3 className="font-bold text-lg text-slate-900 dark:text-white">Hackathon Propuesta (Nuestra Solución)</h3>
            </div>
            <ul className="space-y-3 text-sm text-slate-600 dark:text-slate-300">
              <li className="flex items-start gap-2.5">
                <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                <span><strong>Telemetría Heurística Ultra-Ligera (3.2KB):</strong> Captura eventos de rage click, dead click y scroll desorientado sin ralentizar la web de los prestadores.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                <span><strong>Simulador Determinista de Replay:</strong> Los operadores pueden ver exactamente los 10 segundos previos a la pérdida de una reserva de $350.000 COP.</span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                <span><strong>Recomendaciones Prescriptivas con IA:</strong> Sugerencias de código listas para copiar (ej. CSS `touch-action`, debounce en botones de pago).</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Tech Stack Pill Row */}
        <div className="mt-12 p-6 rounded-2xl bg-white dark:bg-slate-900/50 border border-slate-200 dark:border-slate-800 text-center">
          <p className="text-xs uppercase font-mono tracking-widest text-slate-400 mb-4">Arquitectura Tecnológica del Proyecto</p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <span className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">Python FastTelemetry</span>
            <span className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">Tailwind UX System</span>
            <span className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">Chart.js Analytics</span>
            <span className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">Web Audio API / Tone.js</span>
            <span className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">Heuristic Rage Engine</span>
          </div>
        </div>
      </section>

    </div>
  );
}

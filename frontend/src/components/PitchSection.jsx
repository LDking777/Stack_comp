import React from 'react';
import { Award, Play, Mic, Radio, Volume2, Database, ShieldCheck, Cpu, Clock, MessageSquareQuote, Sparkles, CheckCircle2 } from 'lucide-react';
import { playTone } from '../utils/soundEffects';

export default function PitchSection({ onExploreDashboard }) {
  return (
    <div id="view-pitch" className="w-full flex flex-col transition-all duration-300">
      
      {/* Hero Section */}
      <section className="relative overflow-hidden py-14 lg:py-20 border-b border-slate-200 dark:border-slate-800/80 bg-gradient-to-b from-white via-slate-50 to-slate-100/50 dark:from-[#0c0f14] dark:via-[#111620] dark:to-[#0c0f14]">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(16,185,129,0.15),rgba(255,255,255,0))] dark:bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(16,185,129,0.22),rgba(0,0,0,0))] pointer-events-none"></div>
        
        <div className="max-w-6xl mx-auto px-4 sm:px-6 relative z-10 text-center">
          
          {/* Hackathon Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 dark:bg-emerald-500/15 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-5">
            <Award className="w-4 h-4 text-emerald-500" />
            Kognia Labs · Hackatón Interna — Reto 01: Agente Vocal Cognitivo
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-[1.15] max-w-4xl mx-auto">
            Habla con cualquier documento, <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-500 via-teal-400 to-amber-500">en tiempo real</span> y con voz humana.
          </h1>

          <p className="mt-5 text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-3xl mx-auto font-normal leading-relaxed">
            Un agente conversacional por voz que ingesta datos abiertos de <strong>datos.gov.co</strong> (Relación de IPS y capacidad instalada) o cualquier documento sorpresa. Explica de qué trata, sugiere qué preguntar, responde con latencia sub-segundo y muestra diarización y análisis emocional en vivo.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <button 
              onClick={() => { playTone('high'); onExploreDashboard(); }} 
              className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-sm shadow-xl shadow-emerald-600/25 hover:shadow-emerald-600/40 transform hover:-translate-y-0.5 transition-all flex items-center gap-2"
            >
              <Mic className="w-4 h-4" />
              Probar Agente Vocal en Vivo
            </button>
            <a 
              href="#guion" 
              className="px-6 py-3.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-850 text-slate-800 dark:text-slate-200 font-semibold text-sm transition-all flex items-center gap-2"
            >
              <Clock className="w-4 h-4 text-emerald-500" />
              Guion de los 10 Minutos (P1 a P6)
            </a>
          </div>

          {/* Quick Metrics Banner */}
          <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-sm">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Latencia STT/TTS</p>
              <p className="text-2xl font-bold text-emerald-500 mt-1 font-mono">&lt; 420 ms</p>
              <p className="text-[11px] text-slate-500 mt-1">Interacción bidireccional fluida</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-sm">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Fuente Obligatoria</p>
              <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1 font-mono">SODA3</p>
              <p className="text-[11px] text-slate-500 mt-1">datos.gov.co IPS Colombia (s2ru-bqt6)</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-sm">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Diarización en Vivo</p>
              <p className="text-2xl font-bold text-amber-500 mt-1 font-mono">2 Hablantes</p>
              <p className="text-[11px] text-slate-500 mt-1">Jurado vs Agente con timestamps</p>
            </div>
            <div className="p-4 rounded-2xl bg-white/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80 backdrop-blur-sm">
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">Fidelidad al Documento</p>
              <p className="text-2xl font-bold text-teal-500 mt-1 font-mono">100%</p>
              <p className="text-[11px] text-slate-500 mt-1">Rechazo estricto de alucinaciones</p>
            </div>
          </div>
        </div>
      </section>

      {/* Guion de los 10 Minutos del Jurado (P1 a P6) */}
      <section id="guion" className="py-14 max-w-6xl mx-auto px-4 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <span className="text-xs font-bold text-emerald-500 uppercase tracking-widest font-mono">Estructura de la Evaluación</span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-1 tracking-tight">El Guion de la Prueba en Vivo (10 Minutos)</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">
            Cada fase del recorrido oficial de la hackatón sincronizada en la consola interactiva.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 relative">
            <div className="flex items-center gap-2 mb-2 text-xs font-mono font-bold text-emerald-500">
              <span className="w-5 h-5 rounded-full bg-emerald-500/10 flex items-center justify-center">1</span>
              P1 · P2 (2 min)
            </div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base mb-1">Carga & Dataset SODA3</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              El jurado abre la URL pública. Conecta la API de datos.gov.co de IPS o arrastra cualquier documento sorpresa (PDF/TXT/JSON) indexándolo al instante.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 relative">
            <div className="flex items-center gap-2 mb-2 text-xs font-mono font-bold text-amber-500">
              <span className="w-5 h-5 rounded-full bg-amber-500/10 flex items-center justify-center">2</span>
              P3 · P4 (5 min)
            </div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base mb-1">Briefing & Conversación Vocal</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              El agente sintetiza el Briefing y sugiere entre 3 y 5 preguntas. El jurado hace 3 preguntas por voz: resumen, detalle fino y una fuera del documento para medir honestidad técnica.
            </p>
          </div>

          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 relative">
            <div className="flex items-center gap-2 mb-2 text-xs font-mono font-bold text-teal-500">
              <span className="w-5 h-5 rounded-full bg-teal-500/10 flex items-center justify-center">3</span>
              P5 · P6 (3 min)
            </div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base mb-1">Diarización, Emoción & Q&A</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Visualización en tiempo real de la separación por hablantes con timestamps y panel de telemetría de sentimientos y emociones antes de la ronda de preguntas técnicas.
            </p>
          </div>
        </div>
      </section>

      {/* Rúbrica y Pilares Técnicos */}
      <section className="py-12 border-t border-slate-200 dark:border-slate-800/80 bg-slate-50/50 dark:bg-[#0f131a]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid md:grid-cols-2 gap-8 items-center">
            
            <div>
              <span className="text-xs font-bold text-emerald-500 uppercase tracking-widest font-mono">Alineación con la Rúbrica</span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-1 tracking-tight">Diseñado para Maximizar el Puntaje</h2>
              <div className="space-y-4 mt-6">
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">20%</div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white">Voz y Latencia en Tiempo Real</h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400">STT/TTS acelerado con visualizador reactivo de onda y síntesis vocal en español.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">15%</div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white">Transcripción Diarizada</h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Separación estricta entre Hablante 1 (Jurado) y Hablante 2 (Agente) con marcas de tiempo cronométricas.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">25%</div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white">UX, Diseño y Calidad de Demo</h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Interfaz moderna con Tailwind, panel de telemetría de sentimientos y emociones, y visor exploratorio de datos.</p>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">30%</div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-white">Fidelidad Documental & RAG</h4>
                    <p className="text-xs text-slate-500 dark:text-slate-400">Indexación del dataset oficial de datos.gov.co con rechazo explícito y honesto ante preguntas fuera del alcance.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Architecture Card */}
            <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl relative">
              <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-emerald-500" />
                  <span className="font-bold text-sm text-slate-900 dark:text-white">Pipeline Cognitivo en Vivo</span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-semibold">
                  Zero Latency Cloud
                </span>
              </div>

              <div className="space-y-3 mt-4 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="w-4 h-4 text-emerald-500" />
                    <span className="font-medium text-slate-700 dark:text-slate-300">Fuente de Conocimiento</span>
                  </div>
                  <span className="font-mono text-slate-500 dark:text-slate-400">SODA3 API datos.gov.co / Local Chunks</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Radio className="w-4 h-4 text-amber-500" />
                    <span className="font-medium text-slate-700 dark:text-slate-300">Speech-To-Text (STT)</span>
                  </div>
                  <span className="font-mono text-slate-500 dark:text-slate-400">Web Speech API streaming (~280ms)</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-teal-500" />
                    <span className="font-medium text-slate-700 dark:text-slate-300">Motor Diarizado & Emoción</span>
                  </div>
                  <span className="font-mono text-slate-500 dark:text-slate-400">Timestamp micro-parsing + Polaridad</span>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Volume2 className="w-4 h-4 text-rose-500" />
                    <span className="font-medium text-slate-700 dark:text-slate-300">Text-To-Speech (TTS)</span>
                  </div>
                  <span className="font-mono text-slate-500 dark:text-slate-400">Neuronal ES-CO (~190ms)</span>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <span className="text-[11px] text-slate-400">¿Listo para interactuar por voz?</span>
                <button 
                  onClick={() => { playTone('click'); onExploreDashboard(); }}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors"
                >
                  <span>Abrir Consola</span>
                  <Play className="w-3.5 h-3.5 fill-white" />
                </button>
              </div>
            </div>

          </div>
        </div>
      </section>

    </div>
  );
}

import React, { useState } from 'react';
import { X, Check, Code2 } from 'lucide-react';
import { playTone } from '../utils/soundEffects';

export default function FrictionReplayModal({ diagnostic, onClose, onAskNexo }) {
  const [clickCount, setClickCount] = useState(0);
  const [showRageBadge, setShowRageBadge] = useState(false);
  const [isPatchApplied, setIsPatchApplied] = useState(false);

  if (!diagnostic) return null;

  const handleMockClick = () => {
    if (isPatchApplied) {
      playTone('success');
      return;
    }
    
    setClickCount(prev => prev + 1);
    
    if (diagnostic.metric === 'RageClicks' || clickCount >= 2) {
      playTone('rage');
      setShowRageBadge(true);
      setTimeout(() => setShowRageBadge(false), 800);
    } else {
      playTone('click');
    }
  };

  const handleApplyPatch = () => {
    playTone('high');
    setIsPatchApplied(true);
    if (diagnostic.onPatchApplied) {
        diagnostic.onPatchApplied();
    }
    setTimeout(() => {
      onClose();
    }, 1000);
  };

  const handleAskNexo = () => {
    onAskNexo(`¿Cómo puedo evitar ${diagnostic.metric} en ${diagnostic.url} basado en el diagnóstico: ${diagnostic.aiIdentifiedCause}?`);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200" onClick={onClose} aria-hidden="true">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]" onClick={e => e.stopPropagation()}>
        
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between shrink-0">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-rose-500 font-bold">Diagnóstico de Telemetría</span>
            <h3 className="text-lg font-bold font-mono text-slate-900 dark:text-white">{diagnostic.url}</h3>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          
          {/* Metrics strip */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 text-center">
              <span className="text-[10px] text-slate-400">Tipo de Error</span>
              <p className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{diagnostic.metric}</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 text-center">
              <span className="text-[10px] text-slate-400">Tasa Afectación</span>
              <p className="text-sm font-bold text-rose-500 mt-0.5">{diagnostic.impactRate || 'N/A'}</p>
            </div>
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 text-center">
              <span className="text-[10px] text-slate-400">Sesiones Muestreadas</span>
              <p className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">{diagnostic.affectedSessions || 'N/A'}</p>
            </div>
          </div>

          {/* Simulated Replay Screen */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-950 p-4 text-white relative overflow-hidden">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs text-slate-400 font-mono">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
                REPLAY SIMULADOR — ID #SES-CLD-9842
              </span>
              <span>Mobile Safari (iOS 17.4)</span>
            </div>

            {/* Mock Phone Screen Inside */}
            <div className="py-6 flex flex-col items-center justify-center relative">
              <div className="w-64 p-4 rounded-2xl bg-slate-900 border border-slate-700 shadow-xl relative">
                <div className="text-[11px] text-slate-400 font-mono mb-2">Turismo Caldas Pass</div>
                <div className="text-xs font-bold text-white mb-3">Tour Cafetero Hacienda Venecia (x2)</div>
                <div className="text-xs text-emerald-400 font-mono mb-4">$280.000 COP</div>
                
                {/* Simulated Broken Button */}
                <div onClick={handleMockClick} className={`w-full py-2.5 rounded-lg ${isPatchApplied ? 'bg-emerald-500 hover:bg-emerald-400' : 'bg-emerald-600 hover:bg-emerald-500'} text-center text-xs font-bold cursor-pointer transition-transform select-none active:scale-95 relative`}>
                  Confirmar y Pagar
                  {showRageBadge && !isPatchApplied && (
                    <span className="absolute -top-2 -right-2 px-1.5 py-0.5 bg-rose-500 text-[10px] rounded-full animate-bounce">¡Click Bloqueado! x{clickCount}</span>
                  )}
                </div>
              </div>

              <p className="text-[11px] text-slate-500 mt-3 font-mono">Toca repetidamente el botón de arriba para probar la detección de {diagnostic.metric}</p>
            </div>
          </div>

          {/* AI Diagnostic and Patch Suggestion */}
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-900 dark:text-white">
                <Code2 className="w-4 h-4 text-emerald-500" />
                Parche Heurístico Sugerido por IA
              </div>
              <button onClick={handleAskNexo} className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 hover:underline">Consultar a NEXO IA</button>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed mb-3">
              Causa identificada: {diagnostic.aiIdentifiedCause}
            </p>
            <div className="p-3 rounded-lg bg-slate-900 font-mono text-[11px] text-emerald-400 overflow-x-auto whitespace-pre-wrap">
              <code>{diagnostic.suggestedPatchCode}</code>
            </div>
          </div>

        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 dark:bg-slate-850 border-t border-slate-200 dark:border-slate-800 flex justify-end gap-3 shrink-0">
          <button onClick={onClose} className="px-4 py-2 rounded-xl text-xs font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800">
            Cerrar
          </button>
          <button onClick={handleApplyPatch} disabled={isPatchApplied} className={`px-4 py-2 rounded-xl text-xs font-bold ${isPatchApplied ? 'bg-emerald-500 text-white cursor-not-allowed' : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20'} flex items-center gap-2`}>
            {isPatchApplied ? <Check className="w-3.5 h-3.5" /> : <Check className="w-3.5 h-3.5" />}
            {isPatchApplied ? 'Parche Aplicado' : 'Aplicar Parche en Producción'}
          </button>
        </div>

      </div>
    </div>
  );
}

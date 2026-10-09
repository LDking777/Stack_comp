import React from 'react';
import { X, Layers } from 'lucide-react';

export default function SubmoduleModal({ moduleInfo, onClose }) {
  if (!moduleInfo) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose} aria-hidden="true">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden p-6 animate-in fade-in zoom-in-95 duration-200" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center font-bold">
              <Layers className="w-4 h-4" />
            </div>
            <h3 className="font-bold text-slate-900 dark:text-white text-base">{moduleInfo.title || 'Módulo'}</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <p className="text-xs text-slate-600 dark:text-slate-300 mt-4 leading-relaxed">
          {moduleInfo.description || 'Módulo en construcción.'}
        </p>
        
        {moduleInfo.features && (
          <ul className="mt-4 space-y-2">
            {moduleInfo.features.map((feat, i) => (
              <li key={i} className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></span>
                {feat}
              </li>
            ))}
          </ul>
        )}
        
        <div className="mt-6 flex justify-end">
          <button onClick={onClose} className="px-4 py-2 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:opacity-90 transition-opacity text-xs font-bold">
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { X, CheckCircle, Info, AlertTriangle, XCircle } from 'lucide-react';
import { playTone } from '../utils/soundEffects';

// Global singleton array and listeners
let toasts = [];
let listeners = [];

export function showToast(title, message, status = 'info') {
  const id = Date.now().toString() + Math.random().toString(36).substr(2, 5);
  const newToast = { id, title, message, status };
  toasts = [...toasts, newToast];
  listeners.forEach(listener => listener(toasts));
  
  // Play sound based on status
  if (status === 'success') playTone('success');
  else if (status === 'error' || status === 'warning') playTone('warning');
  else playTone('notification');

  setTimeout(() => {
    removeToast(id);
  }, 4000);
}

function removeToast(id) {
  toasts = toasts.filter(t => t.id !== id);
  listeners.forEach(listener => listener(toasts));
}

const ICONS = {
  success: <CheckCircle className="text-emerald-500 w-5 h-5 shrink-0 mt-0.5" />,
  info: <Info className="text-blue-500 w-5 h-5 shrink-0 mt-0.5" />,
  warning: <AlertTriangle className="text-amber-500 w-5 h-5 shrink-0 mt-0.5" />,
  error: <XCircle className="text-rose-500 w-5 h-5 shrink-0 mt-0.5" />
};

const TOAST_STYLES = {
  success: "bg-white/90 dark:bg-slate-900/90 border-emerald-500/20",
  info: "bg-white/90 dark:bg-slate-900/90 border-blue-500/20",
  warning: "bg-white/90 dark:bg-slate-900/90 border-amber-500/20",
  error: "bg-white/90 dark:bg-slate-900/90 border-rose-500/20"
};

export default function ToastContainer() {
  const [currentToasts, setCurrentToasts] = useState(toasts);

  useEffect(() => {
    const listener = (newToasts) => setCurrentToasts(newToasts);
    listeners.push(listener);
    return () => {
      listeners = listeners.filter(l => l !== listener);
    };
  }, []);

  return (
    <div className="fixed top-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm pointer-events-none">
      {currentToasts.map(toast => (
        <div key={toast.id} className={`pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl border shadow-xl backdrop-blur-md transition-all animate-in slide-in-from-right-5 fade-in duration-300 ${TOAST_STYLES[toast.status] || TOAST_STYLES.info}`}>
          {ICONS[toast.status] || ICONS.info}
          <div className="flex-1 flex flex-col">
            <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-tight">{toast.title}</h4>
            {toast.message && <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{toast.message}</p>}
          </div>
          <button className="text-slate-400 hover:text-slate-700 dark:hover:text-white transition-colors shrink-0" onClick={() => removeToast(toast.id)}>
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}

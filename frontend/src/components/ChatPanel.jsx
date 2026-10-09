import { useState, useEffect, useRef, useCallback } from "react";
import { Send, RotateCcw, X, MessageSquare } from "lucide-react";
import AnswerCard from "./AnswerCard";
import Markdown from "./Markdown";

const GREETING = {
  role: "assistant",
  text: `👋 ¡Hola! He detectado **2 anomalías críticas** en los portales turísticos de Caldas en los últimos 20 minutos:
  
- Bloqueo en botón de pago tarjeta para celulares Xiaomi y Motorola.
- Alta tasa de rebote en turistas de México buscando reservas para el Parque Los Nevados.`,
};

const THINKING_STEPS = [
  "Entendiendo tu consulta…",
  "Consultando datos de Supabase RPC…",
  "Comparando mercados y segmentos…",
  "Redactando respuesta analítica…",
];

const STEP_MS = 2500;

function ThinkingBubble() {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const step = THINKING_STEPS[Math.min(Math.floor((tick * 1000) / STEP_MS), THINKING_STEPS.length - 1)];
  return (
    <div className="flex gap-2.5">
      <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-500 flex items-center justify-center font-bold text-xs shrink-0">
        AI
      </div>
      <div className="p-3 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
        <span className="flex items-center gap-2">
          <span className="flex gap-0.5">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce"></span>
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
          </span>
          <span className="text-xs">{step}</span>
        </span>
      </div>
    </div>
  );
}

export default function ChatPanel({ ask, isThinking, pendingQuestion, onPendingHandled }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const lastQRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isThinking]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 120);
  }, [open]);

  const send = useCallback(async (text) => {
    if (!text?.trim() || isThinking) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    const answer = await ask(text);
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        payload: answer.ok ? answer.data : null,
        error: answer.ok ? null : answer.error,
      },
    ]);
  }, [ask, isThinking]);

  const restart = () => {
    lastQRef.current = null;
    setMessages([GREETING]);
    setInput("");
  };

  useEffect(() => {
    if (!pendingQuestion || lastQRef.current === pendingQuestion) return;
    lastQRef.current = pendingQuestion;
    setOpen(true);
    send(pendingQuestion);
    onPendingHandled?.();
  }, [pendingQuestion, send, onPendingHandled]);

  const unreadCount = messages.filter((m, i) => i > 0 && m.role === "assistant").length || 2;

  return (
    <>
      <div className="fixed bottom-6 right-6 z-50">
        <button 
          onClick={() => setOpen(!open)} 
          className="w-14 h-14 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-950 flex items-center justify-center shadow-2xl hover:scale-105 active:scale-95 transition-all group relative border-2 border-slate-700/20"
        >
          <MessageSquare className="w-6 h-6" />
          {!open && unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-rose-500 text-white font-mono font-bold text-[11px] flex items-center justify-center ring-2 ring-white dark:ring-slate-900">
              {unreadCount}
            </span>
          )}
        </button>
      </div>

      <div className={`fixed bottom-24 right-6 w-96 max-w-[calc(100vw-3rem)] rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl z-50 flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150 ${open ? 'flex' : 'hidden'}`}>
        <div className="p-4 bg-slate-100 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-500 flex items-center justify-center font-bold text-xs">
              AI
            </div>
            <div>
              <h4 className="font-bold text-xs text-slate-900 dark:text-white">CaldasUX Copilot</h4>
              <p className="text-[10px] text-slate-400">Asistente heurístico en tiempo real</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={restart} className="text-slate-400 hover:text-slate-700 dark:hover:text-white" title="Reiniciar conversación">
              <RotateCcw className="w-4 h-4" />
            </button>
            <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-700 dark:hover:text-white" title="Cerrar">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="p-4 space-y-4 max-h-80 overflow-y-auto text-xs bg-slate-50 dark:bg-slate-900" ref={scrollRef}>
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-2.5 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
              {m.role === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-500 flex items-center justify-center font-bold text-xs shrink-0">
                  AI
                </div>
              )}
              <div className={`p-3 rounded-xl max-w-[85%] ${m.role === 'user' ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 ml-auto' : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'}`}>
                {m.text ? <Markdown text={m.text} /> : <AnswerCard payload={m.payload} />}
                {m.error && <div className="text-rose-500 mt-2 font-mono text-[10px]">{m.error}</div>}
              </div>
            </div>
          ))}
          {isThinking && <ThinkingBubble />}
        </div>

        <div className="p-3 border-t border-slate-200 dark:border-slate-800 flex items-center gap-2 bg-slate-50 dark:bg-slate-900">
          <input 
            type="text" 
            ref={inputRef}
            placeholder="Pregunta sobre la fricción de usuarios..." 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            className="flex-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <button 
            onClick={() => send(input)} 
            disabled={isThinking || !input.trim()}
            className="p-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white transition-colors"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </>
  );
}
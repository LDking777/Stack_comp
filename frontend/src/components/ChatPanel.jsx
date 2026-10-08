import { useState, useEffect, useRef, useCallback } from "react";
import {
  Send,
  RotateCcw,
  Bot,
  X,
  MessageCircle,
  Minimize2,
} from "lucide-react";
import AnswerCard from "./AnswerCard";

export const STARTER_QUESTIONS = [
  "¿Por qué se frustran los usuarios de México?",
  "¿Cuál es la tasa de frustración en Colombia?",
  "Compara engagement en celular vs escritorio",
  "¿Qué páginas tienen más rage clicks?",
];

const GREETING = {
  role: "assistant",
  text: `Hola. ¿Necesitas ayuda para analizar los datos turísticos de la región hoy, ${new Date().toLocaleDateString("es-CO", { day: "numeric", month: "long", year: "numeric" })}?`,
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
    <div className="msg-assistant">
      <div className="msg-assistant-icon" aria-hidden="true"><Bot size={13} /></div>
      <div className="thinking-bubble">
        <div className="thinking-dots" aria-hidden="true"><span /><span /><span /></div>
        <span className="thinking-text">{step}</span>
      </div>
    </div>
  );
}

export default function ChatPanel({ ask, isThinking, pendingQuestion, onPendingHandled }) {
  const [open,     setOpen]     = useState(false);
  const [messages, setMessages] = useState([GREETING]);
  const [input,    setInput]    = useState("");
  const scrollRef = useRef(null);
  const inputRef  = useRef(null);
  const lastQRef  = useRef(null);

  // Auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isThinking]);

  // Focus al abrir
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
        error:   answer.ok ? null : answer.error,
      },
    ]);
  }, [ask, isThinking]);

  const restart = () => {
    lastQRef.current = null;
    setMessages([GREETING]);
    setInput("");
  };

  // Pending question desde el dashboard
  useEffect(() => {
    if (!pendingQuestion || lastQRef.current === pendingQuestion) return;
    lastQRef.current = pendingQuestion;
    setOpen(true);
    send(pendingQuestion);
    onPendingHandled?.();
  }, [pendingQuestion, send, onPendingHandled]);

  // Unread badge count
  const unreadCount = messages.filter((m, i) => i > 0 && m.role === "assistant").length;

  return (
    <>
      {/* ── POPUP DE CHAT ── */}
      <div
        className={`chat-popup ${open ? "chat-popup--open" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-label="CALDAS IA — Asistente Analítico"
        aria-hidden={!open}
      >
        {/* Header del popup */}
        <div className="chat-popup-head">
          <div className="chat-identity">
            <div className="chat-avatar-ring" aria-hidden="true">
              <Bot size={15} />
            </div>
            <div className="chat-id-text">
              <strong>CALDAS IA</strong>
              <span>Asistente Analítico</span>
            </div>
          </div>
          <div className="chat-head-right">
            <span className="chat-status-dot" aria-label="Activo">Active</span>
            <button
              className="btn-caldas-icon"
              onClick={restart}
              title="Reiniciar"
              aria-label="Reiniciar conversación"
            >
              <RotateCcw size={13} />
            </button>
            <button
              className="btn-caldas-icon"
              onClick={() => setOpen(false)}
              title="Cerrar"
              aria-label="Cerrar asistente"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Mensajes */}
        <div className="chat-scroll" ref={scrollRef} aria-live="polite">
          {messages.map((m, i) => (
            <div key={i} className="chat-turn">
              {m.role === "assistant" ? (
                <div className="msg-assistant">
                  <div className="msg-assistant-icon" aria-hidden="true"><Bot size={13} /></div>
                  <div className="msg-bubble-assistant">
                    {m.text
                      ? <p style={{ margin: 0 }}>{m.text}</p>
                      : <AnswerCard payload={m.payload} />}
                    {m.error && <div className="msg-error">{m.error}</div>}
                    {m.payload?.verified_deterministic_kpis && (
                      <span className="msg-kpi-badge">KPI EXACTO</span>
                    )}
                  </div>
                </div>
              ) : (
                <div className="msg-user">
                  <div className="msg-bubble-user">{m.text}</div>
                </div>
              )}
            </div>
          ))}
          {isThinking && <ThinkingBubble />}
        </div>

        {/* Chips de sugerencias */}
        <div className="suggestion-chips" style={{ borderTop: "1px solid var(--border-sidebar)", paddingTop: "8px" }}>
          <span className="chips-label">Preguntas rápidas</span>
          {STARTER_QUESTIONS.map((q) => (
            <button
              key={q}
              className="chip-btn"
              onClick={() => send(q)}
              disabled={isThinking}
              aria-label={`Preguntar: ${q}`}
            >
              {q}
            </button>
          ))}
        </div>

        {/* Input */}
        <form
          className="chat-input-bar"
          onSubmit={(e) => { e.preventDefault(); send(input.trim()); }}
        >
          <input
            ref={inputRef}
            id="chat-input-field"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Escribe tu consulta operativa…"
            disabled={isThinking}
            aria-label="Escribe tu pregunta"
            autoComplete="off"
          />
          <button
            type="submit"
            id="chat-send-btn"
            className="chat-send-btn"
            disabled={isThinking || !input.trim()}
            aria-label="Enviar"
          >
            <Send size={14} />
          </button>
        </form>
      </div>

      {/* ── BURBUJA FLOTANTE ── */}
      <button
        id="chat-fab-btn"
        className={`chat-fab ${open ? "chat-fab--hidden" : ""}`}
        onClick={() => setOpen(true)}
        aria-label="Abrir asistente CALDAS IA"
        aria-expanded={open}
      >
        <MessageCircle size={22} />
        {!open && unreadCount > 0 && (
          <span className="chat-fab-badge" aria-label={`${unreadCount} mensajes`}>
            {unreadCount}
          </span>
        )}
        <span className="chat-fab-label">CALDAS IA</span>
      </button>
    </>
  );
}
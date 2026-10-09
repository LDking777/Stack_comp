import { useState, useEffect, useRef, useCallback } from "react";
import {
  Send,
  RotateCcw,
  X,
  Mic,
  MicOff,
  Loader2,
  Upload,
  FileText,
  Trash2,
} from "lucide-react";
import AnswerCard from "./AnswerCard";
import Markdown from "./Markdown";
import { useGeminiLive } from "../hooks/useGeminiLive";
import {
  clearConversationHistory,
  clearSessionMemory,
  listDocuments,
  uploadDocument,
} from "../api";

const GREETING = {
  role: "assistant",
  text: `👋 ¡Hola! Soy **Nexo IA**, tu analista del dataset público de **IPS colombianas** (datos.gov.co).

Puedo darte cifras exactas y diagnósticos sobre:

- Cobertura por departamento y municipio.
- Capacidad instalada (camas, consultorios, salas…).
- IPS públicas vs privadas y niveles de atención.`,
};

const THINKING_STEPS = [
  "Entendiendo tu consulta…",
  "Consultando datos.gov.co vía SoQL…",
  "Agregando cifras deterministas…",
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

export default function ChatPanel({
  ask,
  isThinking,
  pendingQuestion,
  onPendingHandled,
  sessionId,
  openRequest = 0,
  embedded = false,
}) {
  const [open, setOpen] = useState(embedded);
  const storageKey = `nexo_chat_history_${sessionId || "anonymous"}`;
  const [messages, setMessages] = useState(() => {
    if (typeof window === "undefined") return [GREETING];
    try {
      const cached = window.localStorage.getItem(storageKey);
      if (cached) {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {
      /* historia en localStorage no disponible */
    }
    return [GREETING];
  });
  const [input, setInput] = useState("");
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [useDocuments, setUseDocuments] = useState(false);
  const [documentStatusError, setDocumentStatusError] = useState("");
  const fileInputRef = useRef(null);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);
  const lastQRef = useRef(null);

  const handleUserUtterance = useCallback((text) => {
    setMessages((prev) => [...prev, { role: "user", text }]);
  }, []);
  const handleAssistantAnswer = useCallback((text) => {
    setMessages((prev) => [...prev, { role: "assistant", text }]);
  }, []);

  const live = useGeminiLive({
    onUserUtterance: handleUserUtterance,
    onAssistantAnswer: handleAssistantAnswer,
  });
  const voiceBusy = live.status === "requesting-permission" || live.status === "connecting";
  const voiceOn = live.status === "connected";
  const toggleVoice = useCallback(() => {
    if (voiceBusy) return;
    if (voiceOn) live.stop();
    else live.start();
  }, [voiceBusy, voiceOn, live]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isThinking, live.userText, live.modelText]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(messages.slice(-100)));
      } catch (error) {
        console.error("No se pudo guardar el historial local del navegador.", error);
      }
    }
  }, [messages, storageKey]);

  useEffect(() => {
    let active = true;
    listDocuments(sessionId)
      .then((result) => {
        if (!active) return;
        const loadedDocuments = result.documentos || [];
        setDocuments(loadedDocuments);
        setUseDocuments(loadedDocuments.length > 0);
      })
      .catch((error) => {
        if (active) setDocumentStatusError(error.message);
      });
    return () => {
      active = false;
    };
  }, [sessionId]);

  useEffect(() => {
    if (open && !embedded) setTimeout(() => inputRef.current?.focus(), 120);
  }, [embedded, open]);

  const handledOpenRequest = useRef(0);
  useEffect(() => {
    if (embedded) return;
    if (openRequest > handledOpenRequest.current) {
      handledOpenRequest.current = openRequest;
      setOpen(true);
    }
  }, [embedded, openRequest]);

  const send = useCallback(async (text) => {
    if (!text?.trim() || isThinking) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    const answer = await ask(text, { useDocuments });
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        payload: answer.ok ? answer.data : null,
        error: answer.ok ? null : answer.error,
      },
    ]);
  }, [ask, isThinking, useDocuments]);

  const restart = async () => {
    lastQRef.current = null;
    setMessages([GREETING]);
    setInput("");
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(storageKey);
    }
    try {
      await clearConversationHistory(sessionId);
      setDocumentStatusError("");
    } catch (error) {
      setDocumentStatusError(error.message);
    }
  };

  const clearSession = async () => {
    if (!window.confirm("¿Borrar los documentos subidos y la memoria guardada de esta sesión?")) {
      return;
    }
    try {
      await clearSessionMemory(sessionId);
      setDocuments([]);
      setUseDocuments(false);
      setMessages([GREETING]);
      window.localStorage.removeItem(storageKey);
      setDocumentStatusError("");
    } catch (error) {
      setDocumentStatusError(error.message);
    }
  };

  const handleUploadDocument = useCallback(async (event) => {
    const file = event.target.files?.[0];
    if (!file || !sessionId) return;

    setUploadingDocument(true);
    try {
      const result = await uploadDocument(sessionId, file);
      if (!result.ok) {
        throw new Error(result.error || "El backend no indexó el documento.");
      }
      if (result.documento) {
        setDocuments((previous) => [...previous, result.documento]);
        setUseDocuments(true);
      }
      setDocumentStatusError("");
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `📄 Documento cargado: **${file.name}**. Ya quedó indexado para esta sesión. Puedes preguntarle sobre él y responderé usando esos fragmentos como fuente.\n\n- Archivos en sesión: ${result.documentos_sesion ?? 1}\n- Fragmentos indexados: ${result.total_chunks ?? 0}`,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `⚠️ No pude cargar el documento. ${error.message || "Revisa el formato y vuelve a intentarlo."}`,
        },
      ]);
    } finally {
      setUploadingDocument(false);
      event.target.value = "";
    }
  }, [sessionId]);

  useEffect(() => {
    if (!pendingQuestion || lastQRef.current === pendingQuestion) return;
    lastQRef.current = pendingQuestion;
    setOpen(true);
    send(pendingQuestion);
    onPendingHandled?.();
  }, [pendingQuestion, send, onPendingHandled]);

  const unreadCount = messages.filter((m, i) => i > 0 && m.role === "assistant").length;

  return (
    <>
      {!embedded && (
        <div className="fixed bottom-6 right-6 z-50">
          <button
            onClick={() => setOpen(!open)}
            className="w-14 h-14 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-950 flex items-center justify-center shadow-2xl hover:scale-105 active:scale-95 transition-all group relative border-2 border-slate-700/20"
            aria-label={open ? "Ocultar chat" : "Abrir chat"}
          >
            <span className="text-lg font-bold">N</span>
            {!open && unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-rose-500 text-white font-mono font-bold text-[11px] flex items-center justify-center ring-2 ring-white dark:ring-slate-900">
                {unreadCount}
              </span>
            )}
          </button>
        </div>
      )}

      <div className={embedded
        ? "home-chat-panel flex flex-1 min-h-0 flex-col overflow-hidden"
        : `fixed bottom-24 right-6 w-96 max-w-[calc(100vw-3rem)] rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl z-50 flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150 ${open ? "flex" : "hidden"}`}>
        <div className="p-4 bg-slate-100 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-500 flex items-center justify-center font-bold text-xs">
              AI
            </div>
            <div>
              <h4 className="font-bold text-xs text-slate-900 dark:text-white">Nexo IA</h4>
              <p className={`text-[10px] ${voiceOn ? "text-emerald-500 font-semibold" : "text-slate-400"}`}>
                {live.status === "requesting-permission"
                  ? "Pidiendo permiso de micrófono…"
                  : live.status === "connecting"
                    ? "Conectando a Gemini Live…"
                    : voiceOn
                      ? "● En vivo — habla ahora"
                      : "Analista de datos de IPS · cifras verificadas"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleVoice}
              disabled={voiceBusy}
              className={`p-1.5 rounded-lg transition-colors disabled:opacity-50 ${voiceOn ? "text-emerald-500 bg-emerald-500/10" : "text-slate-400 hover:text-slate-700 dark:hover:text-white"}`}
              title={voiceOn ? "Terminar la voz" : "Conversar por voz (Gemini Live)"}
              aria-label={voiceOn ? "Terminar conversación de voz" : "Iniciar conversación de voz"}
            >
              {voiceBusy ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : voiceOn ? (
                <MicOff className="w-4 h-4" />
              ) : (
                <Mic className="w-4 h-4" />
              )}
            </button>
            <button onClick={restart} className="text-slate-400 hover:text-slate-700 dark:hover:text-white" title="Reiniciar conversación">
              <RotateCcw className="w-4 h-4" />
            </button>
            <button onClick={clearSession} className="text-slate-400 hover:text-rose-500" title="Borrar documentos y memoria de esta sesión" aria-label="Borrar documentos y memoria de esta sesión">
              <Trash2 className="w-4 h-4" />
            </button>
            {!embedded && (
              <button onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-700 dark:hover:text-white" title="Cerrar">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        <div className={`p-4 space-y-4 overflow-y-auto text-xs bg-slate-50 dark:bg-slate-900 ${embedded ? "flex-1 min-h-0" : "max-h-80"}`} ref={scrollRef}>
          {documentStatusError && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-[10px] text-amber-700 dark:text-amber-300">
              {documentStatusError}
            </div>
          )}
          {documents.length > 0 && (
            <div className="text-[10px] text-slate-500 dark:text-slate-400">
              {documents.length} documento{documents.length === 1 ? "" : "s"} de salud/IPS indexado{documents.length === 1 ? "" : "s"}.
              {useDocuments ? " Las consultas usarán estos documentos." : ""}
            </div>
          )}
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
          {(live.userText || live.modelText) && (
            <div className="flex flex-col gap-1.5 p-2.5 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
              <span className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
                Transcripción en vivo · asignada por turno
              </span>
              {live.userText && (
                <div className="text-xs text-slate-600 dark:text-slate-300">
                  <span className="font-bold">Tú:</span> {live.userText}
                </div>
              )}
              {live.modelText && (
                <div className="text-xs text-slate-700 dark:text-slate-200">
                  <span className="font-bold text-emerald-600 dark:text-emerald-400">Nexo:</span> {live.modelText}
                </div>
              )}
            </div>
          )}
          {live.error && (
            <div className="text-[10px] text-rose-500 font-mono">{live.error}</div>
          )}
          {isThinking && <ThinkingBubble />}
        </div>

        <div className="p-3 border-t border-slate-200 dark:border-slate-800 flex items-center gap-2 bg-slate-50 dark:bg-slate-900">
          <label className="cursor-pointer rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 transition-colors disabled:opacity-50" title="Subir documento PDF/Word/TXT/MD">
            <input ref={fileInputRef} type="file" accept=".pdf,.docx,.txt,.md" className="hidden" disabled={uploadingDocument} onChange={handleUploadDocument} />
            {uploadingDocument ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
          </label>
          {documents.length > 0 && (
            <button
              type="button"
              onClick={() => setUseDocuments((enabled) => !enabled)}
              className={`rounded-lg border p-2 transition-colors ${useDocuments ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" : "border-slate-200 dark:border-slate-700 text-slate-500"}`}
              title={useDocuments ? "Desactivar respuestas basadas solo en documentos" : "Activar respuestas basadas solo en documentos"}
              aria-pressed={useDocuments}
              aria-label={useDocuments ? "Desactivar modo documentos" : "Activar modo documentos"}
            >
              <FileText className="w-3.5 h-3.5" />
            </button>
          )}
          <input 
            type="text" 
            ref={inputRef}
            placeholder="Pregunta sobre las IPS: camas, cobertura, naturaleza..." 
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
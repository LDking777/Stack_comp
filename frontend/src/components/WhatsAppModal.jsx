import React from "react";
import { MessageCircle, X, ExternalLink, CheckCircle2, Smartphone, ShieldCheck, Sparkles, Copy } from "lucide-react";
import { playTone } from "../utils/soundEffects";
import { showToast } from "./ToastContainer";

export default function WhatsAppModal({ isOpen, onClose, config }) {
  if (!isOpen) return null;

  const waLink = config?.wa_link || (config?.phone_number ? `https://wa.me/${config.phone_number.replace(/\D/g, "")}?text=Hola%20Nexo%20IA` : "https://wa.me/?text=Hola%20Nexo%20IA");
  const webhookUrl = `${window.location.origin}/api/v1/whatsapp/webhook`.replace("5173", "8000").replace("3000", "8000");

  const copyToClipboard = (text, label) => {
    playTone("click");
    navigator.clipboard.writeText(text);
    showToast("Copiado", `${label} copiado al portapapeles`, "success");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg rounded-3xl bg-white dark:bg-[#12161f] border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden p-6 sm:p-8 animate-in zoom-in-95 duration-200">
        
        {/* Header con botón de cierre */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-500 text-white flex items-center justify-center shadow-lg shadow-emerald-500/25">
              <MessageCircle className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-extrabold text-base text-slate-900 dark:text-white">
                  Nexo IA en WhatsApp
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                  Canal Oficial
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Consulta la capacidad y cobertura de IPS de Colombia por chat
              </p>
            </div>
          </div>
          <button
            onClick={() => { playTone("click"); onClose(); }}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Contenido Principal */}
        <div className="mt-5 space-y-4">
          
          {/* Tarjeta de Conexión */}
          <div className="p-4 rounded-2xl bg-gradient-to-tr from-emerald-500/10 via-teal-500/5 to-transparent border border-emerald-500/20">
            <div className="flex items-start gap-3">
              <Smartphone className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-xs font-bold text-slate-900 dark:text-white">
                  Conversación 24/7 con Cifras Verificadas
                </h4>
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">
                  Envía cualquier pregunta en lenguaje natural y recibe cifras de datos.gov.co sin alucinaciones, con memoria de diálogo por usuario.
                </p>
              </div>
            </div>

            <div className="mt-4 flex flex-col sm:flex-row items-center gap-2.5">
              <a
                href={waLink}
                target="_blank"
                rel="noreferrer"
                onClick={() => playTone("high")}
                className="w-full sm:flex-1 py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-emerald-600/25 transition-all transform hover:-translate-y-0.5"
              >
                <MessageCircle className="w-4 h-4" />
                <span>Abrir Chat en WhatsApp</span>
                <ExternalLink className="w-3.5 h-3.5 opacity-80" />
              </a>
              {config?.phone_number && (
                <button
                  onClick={() => copyToClipboard(config.phone_number, "Número de WhatsApp")}
                  className="w-full sm:w-auto py-3 px-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-750 flex items-center justify-center gap-1.5 transition-colors"
                  title="Copiar número de teléfono"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span className="font-mono">{config.phone_number}</span>
                </button>
              )}
            </div>
          </div>

          {/* Preguntas Sugeridas para WhatsApp */}
          <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800/80">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400 block mb-2">
              Prueba enviando por WhatsApp:
            </span>
            <div className="space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
              <div className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-white dark:hover:bg-slate-800 cursor-pointer" onClick={() => copyToClipboard("¿Cuántas camas de UCI hay en Bogotá y Antioquia?", "Pregunta")}>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>«¿Cuántas camas de UCI hay en Bogotá y Antioquia?»</span>
              </div>
              <div className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-white dark:hover:bg-slate-800 cursor-pointer" onClick={() => copyToClipboard("¿Cuáles son las IPS de Nivel 3 en Caldas?", "Pregunta")}>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>«¿Cuáles son las IPS de Nivel 3 en Caldas?»</span>
              </div>
              <div className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-white dark:hover:bg-slate-800 cursor-pointer" onClick={() => copyToClipboard("Compara la capacidad de IPS públicas vs privadas", "Pregunta")}>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>«Compara la capacidad de IPS públicas vs privadas»</span>
              </div>
            </div>
          </div>

          {/* Información Técnica de Webhook para Desarrolladores / Jurado */}
          <div className="p-3.5 rounded-2xl bg-slate-100/70 dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-500 dark:text-slate-400 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                Meta Webhook Endpoint (Cloud API)
              </span>
              <button
                onClick={() => copyToClipboard(webhookUrl, "URL del Webhook")}
                className="text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-1 font-sans text-xs font-semibold"
              >
                <Copy className="w-3 h-3" /> Copiar URL
              </button>
            </div>
            <div className="p-2 rounded-lg bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 break-all select-all text-[10px]">
              /api/v1/whatsapp/webhook
            </div>
            <p className="text-[10px] font-sans text-slate-400 leading-tight">
              Soporta verificación handshake (GET) y eventos en tiempo real (POST) de Meta Graph API.
            </p>
          </div>

        </div>

      </div>
    </div>
  );
}

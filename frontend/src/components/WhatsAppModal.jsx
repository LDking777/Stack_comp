import {
  Copy,
  ExternalLink,
  MessageCircle,
  ShieldCheck,
  Smartphone,
  X,
} from "lucide-react";
import { getWhatsAppWebhookUrl } from "../api";
import { playTone } from "../utils/soundEffects";
import { showToast } from "./ToastContainer";

const SUGGESTED_QUESTIONS = [
  "¿Cuántas camas de UCI hay en Bogotá y Antioquia?",
  "Compara la capacidad de CAMAS entre IPS públicas y privadas.",
  "¿Cuántas camas pediátricas hay en Caldas?",
];

export default function WhatsAppModal({ isOpen, onClose, config }) {
  if (!isOpen) return null;

  const copyToClipboard = async (text, label) => {
    try {
      await navigator.clipboard.writeText(text);
      playTone("click");
      showToast("Copiado", `${label} copiado al portapapeles`, "success");
    } catch (error) {
      showToast("No se pudo copiar", error.message || "Revisa los permisos del navegador.", "error");
    }
  };

  const webhookUrl = getWhatsAppWebhookUrl();

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="whatsapp-modal-title"
        className="relative w-full max-w-lg overflow-hidden rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-[#12161f] sm:p-8"
      >
        <header className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-emerald-500 text-white">
              <MessageCircle className="h-5 w-5" />
            </div>
            <div>
              <h2
                id="whatsapp-modal-title"
                className="font-extrabold text-slate-900 dark:text-white"
              >
                Nexo IA en WhatsApp
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Consulta cifras agregadas de IPS de Colombia.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Cerrar"
            className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="mt-5 space-y-4">
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
            <div className="flex items-start gap-3">
              <Smartphone className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500" />
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Cifras verificadas con datos.gov.co
                </h3>
                <p className="mt-1 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                  Pregunta por capacidad instalada, ubicación, nivel de atención
                  o naturaleza pública y privada. Nexo IA no consulta nombres,
                  códigos ni NIT de IPS individuales.
                </p>
              </div>
            </div>
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <a
                href={config?.wa_link}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => playTone("high")}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-xs font-bold text-white hover:bg-emerald-500"
              >
                <MessageCircle className="h-4 w-4" />
                Abrir WhatsApp
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
              {config?.phone_number && (
                <button
                  type="button"
                  onClick={() =>
                    copyToClipboard(config.phone_number, "Número de WhatsApp")
                  }
                  className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-xs dark:border-slate-700"
                >
                  <Copy className="h-3.5 w-3.5" />
                  {config.phone_number}
                </button>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/60">
            <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">
              Preguntas agregadas de ejemplo
            </h3>
            <ul className="space-y-1">
              {SUGGESTED_QUESTIONS.map((question) => (
                <li key={question}>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(question, "Pregunta")}
                    className="w-full rounded-lg p-2 text-left text-xs text-slate-700 hover:bg-white dark:text-slate-300 dark:hover:bg-slate-800"
                  >
                    <span className="mr-2 text-emerald-500">•</span>
                    {question}
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {config?.webhook_configured && (
            <div className="rounded-2xl border border-slate-200 bg-slate-100/70 p-3.5 text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/90">
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-1.5 font-semibold">
                  <ShieldCheck className="h-4 w-4 text-emerald-500" />
                  Endpoint de webhook para Meta
                </span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(webhookUrl, "URL del webhook")}
                  className="flex items-center gap-1 text-emerald-600 hover:underline dark:text-emerald-400"
                >
                  <Copy className="h-3.5 w-3.5" />
                  Copiar URL
                </button>
              </div>
              <p className="mt-2 break-all font-mono">{webhookUrl}</p>
              <p className="mt-1">
                El endpoint valida la firma HMAC-SHA256 de Meta antes de
                procesar mensajes.
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

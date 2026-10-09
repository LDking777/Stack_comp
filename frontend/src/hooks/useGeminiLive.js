import { useCallback, useEffect, useRef, useState } from "react";
import { GoogleGenAI, Modality } from "@google/genai";
import { getLiveToken, askLiveTool } from "../api";
import { createMicCapture, createPcmPlayer, bytesToBase64 } from "../utils/pcmAudio";

// El modelo Live solo narra; cualquier cifra pasa por la herramienta, que
// reutiliza el pipeline SoQL determinista. Así se conserva el invariante del
// proyecto: el LLM nunca calcula números (AGENTS.md §1).
const SYSTEM_INSTRUCTION = `Eres Nexo IA, el asistente por voz de datos de IPS (instituciones prestadoras de servicios de salud) de Colombia, sobre el dataset público de datos.gov.co.

REGLA ABSOLUTA: nunca inventes ni calcules cifras. Para cualquier pregunta sobre números, conteos, camas, capacidad instalada, cobertura, departamentos, naturaleza (pública/privada/mixta) o niveles de atención, llama SIEMPRE a la herramienta consultar_ips y narra únicamente lo que devuelva. Si no hay dato, dilo con franqueza.

Responde en español, en frases cortas y naturales, apropiadas para ser escuchadas. Si la pregunta está fuera del dominio de IPS colombianas, indícalo brevemente y ofrece un ejemplo de pregunta válida.`;

const CONSULTAR_IPS = {
  name: "consultar_ips",
  description:
    "Obtiene cifras EXACTAS y verificadas del dataset público de IPS de Colombia (datos.gov.co). Úsala siempre que la pregunta requiera números, capacidades, coberturas, comparaciones o diagnósticos. Devuelve texto plano verificado.",
  parameters: {
    type: "object",
    properties: {
      pregunta: {
        type: "string",
        description: "La pregunta del usuario, literal y en lenguaje natural.",
      },
    },
    required: ["pregunta"],
  },
};

/**
 * Conversación de voz bidireccional con Gemini Live sobre la sesión existente.
 *
 * - Usa credenciales efímeras: la API key vive solo en el backend.
 * - La transcripción de usuario/agente se expone en `userText`/`modelText`
 *   (asignación POR TURNO, no diarización acústica).
 * - Las cifras salen de la herramienta `consultar_ips` → pipeline SoQL.
 */
export function useGeminiLive(options = {}) {
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);
  const [userText, setUserText] = useState("");
  const [modelText, setModelText] = useState("");

  const optionsRef = useRef(options);
  useEffect(() => {
    optionsRef.current = options;
  });

  const sessionRef = useRef(null);
  const micRef = useRef(null);
  const playerRef = useRef(null);
  const streamRef = useRef(null);
  const activeRef = useRef(false);
  const sendPartsRef = useRef([]);
  const sendBytesRef = useRef(0);
  const inputBufferRef = useRef("");
  const pendingAnswerRef = useRef(null);

  const resetTurn = useCallback(() => {
    inputBufferRef.current = "";
    pendingAnswerRef.current = null;
    setUserText("");
    setModelText("");
  }, []);

  const cleanup = useCallback(async () => {
    activeRef.current = false;
    sendPartsRef.current = [];
    sendBytesRef.current = 0;
    if (micRef.current) {
      await micRef.current.stop();
      micRef.current = null;
    }
    if (playerRef.current) {
      await playerRef.current.stop();
      playerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (sessionRef.current) {
      try {
        sessionRef.current.close();
      } catch {
        /* sesión ya cerrada */
      }
      sessionRef.current = null;
    }
    resetTurn();
  }, [resetTurn]);

  const stop = useCallback(async () => {
    await cleanup();
    setStatus("idle");
  }, [cleanup]);

  const flushAudio = useCallback(() => {
    const session = sessionRef.current;
    if (!session || sendBytesRef.current === 0) return;
    const bytes = new Uint8Array(sendBytesRef.current);
    let offset = 0;
    for (const part of sendPartsRef.current) {
      bytes.set(part, offset);
      offset += part.length;
    }
    sendPartsRef.current = [];
    sendBytesRef.current = 0;
    try {
      session.sendRealtimeInput({
        audio: {
          data: bytesToBase64(bytes),
          mimeType: "audio/pcm;rate=16000",
        },
      });
    } catch {
      /* sesión cerrada durante el envío */
    }
  }, []);

  const start = useCallback(async () => {
    if (activeRef.current) return;
    setError(null);
    setStatus("requesting-permission");
    resetTurn();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = stream;

      const token = await getLiveToken();

      const player = createPcmPlayer({ sampleRate: 24000 });
      playerRef.current = player;
      player.resume();

      setStatus("connecting");
      const ai = new GoogleGenAI({
        apiKey: token.token,
        httpOptions: { apiVersion: "v1alpha" },
      });

      const handleToolCall = async (call) => {
        if (call?.name !== "consultar_ips") return;
        const pregunta = call?.args?.pregunta || call?.args?.query || "";
        let output = { output: "No obtuve datos verificados.", verificado: false };
        try {
          const data = await askLiveTool(pregunta);
          output = { output: data.respuesta, verificado: data.verificado };
          pendingAnswerRef.current = data.respuesta;
        } catch {
          output = { output: "No pude consultar los datos en este momento.", verificado: false };
        }
        try {
          sessionRef.current?.sendToolResponse({
            functionResponses: [{ id: call?.id, name: call.name, response: output }],
          });
        } catch {
          /* sesión cerrada antes de responder la herramienta */
        }
      };

      const onMessage = (message) => {
        const content = message?.serverContent;
        if (content) {
          const inputText = content.inputTranscription?.text;
          if (inputText) {
            inputBufferRef.current += inputText;
            setUserText(inputBufferRef.current);
          }

          const outputText = content.outputTranscription?.text;
          if (outputText) setModelText((prev) => prev + outputText);

          const parts = content.modelTurn?.parts || [];
          for (const part of parts) {
            const data = part?.inlineData?.data || part?.inline_data?.data;
            if (data) playerRef.current?.play(data);
          }

          if (content.interrupted) playerRef.current?.interrupt();

          if (content.turnComplete || content.generationComplete) {
            const spoken = inputBufferRef.current.trim();
            if (spoken) optionsRef.current.onUserUtterance?.(spoken);
            if (pendingAnswerRef.current) {
              optionsRef.current.onAssistantAnswer?.(pendingAnswerRef.current);
            }
            resetTurn();
          }
        }

        const calls =
          message?.toolCall?.functionCalls ||
          message?.tool_call?.function_calls ||
          [];
        for (const call of calls) handleToolCall(call);
      };

      const session = await ai.live.connect({
        model: token.model,
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: { parts: [{ text: SYSTEM_INSTRUCTION }] },
          inputAudioTranscription: {},
          outputAudioTranscription: {},
          tools: [{ functionDeclarations: [CONSULTAR_IPS] }],
        },
        callbacks: {
          onopen: () => {},
          onmessage: onMessage,
          onerror: (e) => {
            setError(e?.message || "Error en la sesión de voz.");
            setStatus("error");
          },
          onclose: () => {
            if (activeRef.current) setStatus("idle");
          },
        },
      });

      sessionRef.current = session;
      activeRef.current = true;
      setStatus("connected");

      const mic = await createMicCapture(stream, {
        onChunk: (pcmBytes) => {
          sendPartsRef.current.push(pcmBytes);
          sendBytesRef.current += pcmBytes.length;
          // ~100 ms a 16 kHz mono 16-bit = 3200 bytes.
          if (sendBytesRef.current >= 3200) flushAudio();
        },
      });
      micRef.current = mic;
    } catch (err) {
      const message =
        err?.name === "NotAllowedError"
          ? "Permiso de micrófono denegado. Actívalo para conversar por voz."
          : err?.message || "No se pudo iniciar la conversación de voz.";
      await cleanup();
      setError(message);
      setStatus("error");
    }
  }, [cleanup, flushAudio, resetTurn]);

  useEffect(() => () => { cleanup(); }, [cleanup]);

  return { status, error, userText, modelText, start, stop };
}

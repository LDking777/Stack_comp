// Utilidades PCM para Gemini Live API.
//
// Formato oficial confirmado en la documentación de Google:
//   - Entrada:  PCM 16-bit little-endian, 16 kHz, mono.
//   - Salida:   PCM 16-bit little-endian, 24 kHz, mono.
// El navegador entrega floats vía Web Audio; aquí se convierte a/desde PCM y
// se codifica en base64, que es lo que viaja por el WebSocket de Live.

const CAPTURE_WORKLET = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    if (input && input[0]) {
      this.port.postMessage(input[0].slice(0));
    }
    return true;
  }
}
registerProcessor("pcm-capture", PcmCaptureProcessor);
`;

function audioContextCtor() {
  return window.AudioContext || window.webkitAudioContext;
}

export function floatTo16BitPCM(float32) {
  const buffer = new ArrayBuffer(float32.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Uint8Array(buffer);
}

export function bytesToBase64(bytes) {
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

export function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/**
 * Captura el micrófono y entrega bloques PCM 16-bit (16 kHz) vía `onChunk`.
 * El stream se obtiene fuera (para pedir permiso antes de mintear el token).
 */
export async function createMicCapture(stream, { onChunk } = {}) {
  const Ctx = audioContextCtor();
  const context = new Ctx({ sampleRate: 16000 });
  const blob = new Blob([CAPTURE_WORKLET], { type: "application/javascript" });
  const url = URL.createObjectURL(blob);
  try {
    await context.audioWorklet.addModule(url);
  } finally {
    URL.revokeObjectURL(url);
  }

  const source = context.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(context, "pcm-capture");
  node.port.onmessage = (event) => {
    if (onChunk) onChunk(floatTo16BitPCM(event.data));
  };
  source.connect(node);

  // Algunos navegadores no ejecutan el worklet sin un destino conectado; un
  // gain a 0 lo mantiene vivo sin realimentar audio al altavoz.
  const sink = context.createGain();
  sink.gain.value = 0;
  node.connect(sink).connect(context.destination);
  await context.resume();

  return {
    async stop() {
      try {
        node.port.onmessage = null;
        source.disconnect();
        node.disconnect();
        sink.disconnect();
      } catch {
        /* nodos ya desconectados */
      }
      try {
        await context.close();
      } catch {
        /* contexto ya cerrado */
      }
    },
  };
}

/**
 * Reproductor de PCM 24 kHz. Encola y programa cada bloque para que el audio
 * del modelo se escuche continuo y permita barge-in (al interrumpir, se corta).
 */
export function createPcmPlayer({ sampleRate = 24000 } = {}) {
  const Ctx = audioContextCtor();
  const context = new Ctx({ sampleRate });
  let cursor = 0;
  const sources = new Set();

  const play = (base64) => {
    const bytes = base64ToBytes(base64);
    const samples = new Float32Array(bytes.length / 2);
    for (let i = 0; i < samples.length; i++) {
      const value = (bytes[i * 2 + 1] << 8) | bytes[i * 2];
      samples[i] = (value >= 0x8000 ? value - 0x10000 : value) / 0x8000;
    }
    const buffer = context.createBuffer(1, samples.length, sampleRate);
    buffer.copyToChannel(samples, 0);
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    sources.add(source);
    source.onended = () => sources.delete(source);
    const startAt = Math.max(context.currentTime, cursor);
    source.start(startAt);
    cursor = startAt + buffer.duration;
  };

  const interrupt = () => {
    for (const source of sources) {
      try {
        source.stop();
      } catch {
        /* la fuente ya terminó */
      }
    }
    sources.clear();
    cursor = context.currentTime;
  };

  return {
    play,
    interrupt,
    resume: () => context.resume().catch(() => {}),
    async stop() {
      interrupt();
      cursor = 0;
      try {
        await context.close();
      } catch {
        /* contexto ya cerrado */
      }
    },
  };
}

const API_BASE = (
  import.meta.env.VITE_API_URL || "http://localhost:8000"
).replace(/\/+$/, "");

const SESSION_KEY = "nexo_session_id";

function getOrCreateSessionId() {
  if (typeof window === "undefined") return "browser-session";
  try {
    const current = window.localStorage.getItem(SESSION_KEY);
    if (current) return current;
    const randomId = window.crypto?.randomUUID?.()
      || `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    const next = `nexo-${randomId}`;
    window.localStorage.setItem(SESSION_KEY, next);
    return next;
  } catch {
    return `nexo-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }
}

async function getDashboard() {
  let res;
  try {
    res = await fetch(`${API_BASE}/api/v1/dashboard`);
  } catch (e) {
    throw new Error(
      `Backend no disponible en ${API_BASE}. Sin conexión no hay datos verificados que mostrar. (${e.message})`
    );
  }
  if (!res.ok) {
    throw new Error(`El backend respondió ${res.status} al cargar el tablero.`);
  }
  return res.json();
}

async function askNexo(question, { sessionId, useDocuments = false } = {}) {
  const payload = { query: question };
  if (sessionId) payload.session_id = sessionId;
  if (useDocuments) payload.use_documents = true;

  let res;
  try {
    res = await fetch(`${API_BASE}/api/v1/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    throw new Error(
      `Backend no disponible en ${API_BASE}: no hay datos verificados para responder. (${e.message})`
    );
  }

  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json())?.detail || "";
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new Error(`El backend respondió con error ${res.status}. ${detail}`.trim());
  }

  return res.json();
}

async function uploadDocument(sessionId, file) {
  if (!sessionId || !file) {
    throw new Error("Se requiere una sesión activa y un archivo válido.");
  }

  const form = new FormData();
  form.append("file", file);
  form.append("session_id", sessionId);

  const res = await fetch(`${API_BASE}/api/v1/documents`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json())?.detail || "";
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new Error(detail || `El backend respondió ${res.status} al subir el documento.`);
  }

  return res.json();
}

async function listDocuments(sessionId) {
  const res = await fetch(`${API_BASE}/api/v1/documents/${sessionId}`);
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json())?.detail || "";
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new Error(detail || `No pude listar los documentos de la sesión.`);
  }
  return res.json();
}

async function clearSessionMemory(sessionId) {
  const res = await fetch(`${API_BASE}/api/v1/documents/${sessionId}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(`No pude limpiar la sesión ${sessionId}.`);
  }
  return res.json();
}

async function clearConversationHistory(sessionId) {
  const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}/history`, {
    method: "DELETE",
  });
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json())?.detail || "";
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new Error(detail || "No pude borrar la memoria de conversación.");
  }
  return res.json();
}

async function getHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/v1/health`);
    if (!res.ok) throw new Error("Sin conexión");
    return res.json();
  } catch {
    return { status: "offline", service: "Nexo IA" };
  }
}

async function getLiveToken() {
  let res;
  try {
    res = await fetch(`${API_BASE}/api/v1/live/token`, { method: "POST" });
  } catch (e) {
    throw new Error(
      `Backend no disponible en ${API_BASE} para iniciar la voz. (${e.message})`
    );
  }
  if (!res.ok) {
    let detail = "";
    try {
      detail = (await res.json())?.detail || "";
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new Error(
      detail || `El backend respondió ${res.status} al pedir la credencial de voz.`
    );
  }
  return res.json();
}

async function askLiveTool(pregunta) {
  const res = await fetch(`${API_BASE}/api/v1/live/tool`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pregunta }),
  });
  if (!res.ok) {
    throw new Error(`El backend respondió ${res.status} a la herramienta de voz.`);
  }
  return res.json();
}

export {
  getDashboard,
  askNexo,
  getHealth,
  getLiveToken,
  askLiveTool,
  uploadDocument,
  listDocuments,
  clearSessionMemory,
  clearConversationHistory,
  getOrCreateSessionId,
  API_BASE,
};

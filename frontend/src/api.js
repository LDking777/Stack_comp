const API_BASE = (
  import.meta.env.VITE_API_URL || "http://localhost:8000"
).replace(/\/+$/, "");

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

async function askNexo(question) {
  let res;
  try {
    res = await fetch(`${API_BASE}/api/v1/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: question }),
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

export { getDashboard, askNexo, getHealth, getLiveToken, askLiveTool, API_BASE };

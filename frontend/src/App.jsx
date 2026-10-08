import { useState, useEffect, useCallback } from "react";
import {
  BarChart3,
  Map,
  TrendingUp,
  Settings,
  Layers,
  Bell,
  Settings2,
  User,
} from "lucide-react";
// ChatPanel ahora es burbuja flotante — se renderiza fuera del grid
import BIDashboard from "./components/BIDashboard";
import ChatPanel from "./components/ChatPanel";
import { getDashboard, askNexo } from "./api";
import "./App.css";

// Fecha actual formateada en español
function formatDate() {
  return new Date().toLocaleDateString("es-CO", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).replace(/^\w/, (c) => c.toUpperCase());
}

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard",        icon: BarChart3 },
  { id: "regional",  label: "Análisis Regional", icon: Map },
  { id: "kpis",      label: "KPIs de Turismo",   icon: TrendingUp },
  { id: "ops",       label: "Operaciones",        icon: Layers },
  { id: "config",    label: "Configuración",      icon: Settings },
];

export default function App() {
  const [data,           setData]           = useState(null);
  const [loading,        setLoading]        = useState(true);
  const [error,          setError]          = useState(null);
  const [thinking,       setThinking]       = useState(false);
  const [pendingQ,       setPendingQ]       = useState(null);
  const [activeNav,      setActiveNav]      = useState("dashboard");

  // Carga del dashboard
  const fetchDashboard = useCallback(async () => {
    try {
      const result = await getDashboard();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message || "Verifica que el servidor esté activo (puerto 8000).");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDashboard = useCallback(() => {
    setLoading(true);
    return fetchDashboard();
  }, [fetchDashboard]);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  // Pregunta al asistente
  const handleAsk = useCallback(async (question) => {
    setThinking(true);
    try {
      const res = await askNexo(question);
      return { ok: true, data: res };
    } catch (err) {
      return { ok: false, error: err.message || "No se pudo consultar." };
    } finally {
      setThinking(false);
    }
  }, []);

  // Abre el chat con una pregunta pre-cargada
  const openChatWith = useCallback((question) => {
    setPendingQ(question ?? "");
  }, []);

  return (
    <div className="app-shell">

      {/* ── SIDEBAR IZQUIERDO ── */}
      <nav className="sidebar" role="navigation" aria-label="Navegación principal">
        <div className="sidebar-brand">
          <div className="sidebar-brand-icon" aria-hidden="true">
            <BarChart3 size={18} />
          </div>
          <span className="sidebar-brand-name">
            Turismo Caldas <em>5.0</em>
          </span>
        </div>

        <div className="sidebar-nav">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-item ${activeNav === id ? "active" : ""}`}
              onClick={() => setActiveNav(id)}
              aria-current={activeNav === id ? "page" : undefined}
            >
              <span className="nav-icon" aria-hidden="true">
                <Icon size={16} />
              </span>
              {label}
            </button>
          ))}
        </div>

        <div className="sidebar-bottom">
          <button className="nav-item" onClick={() => {}}>
            <span className="nav-icon"><Settings2 size={16} /></span>
            Ajustes del Sistema
          </button>
        </div>
      </nav>

      {/* ── COLUMNA PRINCIPAL (Topbar + Dashboard + Chat) ── */}
      <div className="main-col">

        {/* Topbar */}
        <header className="topbar" role="banner">
          <div className="topbar-left">
            <h1 className="topbar-page-title">Dashboard</h1>
          </div>

          <div className="topbar-right">
            <div className="topbar-location" aria-label="Ubicación y fecha">
              <span className="topbar-location-name">Manizales, Caldas, Colombia</span>
              <span className="topbar-location-date">{formatDate()}</span>
            </div>

            <button className="topbar-icon-btn notif-badge" aria-label="Notificaciones">
              <Bell size={16} />
            </button>

            <button className="topbar-icon-btn" aria-label="Configuración">
              <Settings size={15} />
            </button>

            <div className="topbar-avatar" role="img" aria-label="Perfil de usuario">
              <User size={15} />
            </div>
          </div>
        </header>

        {/* Dashboard a pantalla completa */}
        <div className="dashboard-scroll">
          <BIDashboard
            data={data}
            loading={loading}
            error={error}
            onRetry={loadDashboard}
            onInspect={openChatWith}
          />
        </div>
      </div>

      {/* ── Burbuja flotante de CALDAS IA ── */}
      <ChatPanel
        ask={handleAsk}
        isThinking={thinking}
        pendingQuestion={pendingQ}
        onPendingHandled={() => setPendingQ(null)}
      />
    </div>
  );
}
import { useState, useEffect, useCallback } from "react";
import { getDashboard, askNexo } from "./api";
import { useTheme } from "./context/ThemeContext";
import { toggleSoundEnabled, isSoundEnabled } from "./utils/soundEffects";
import BIDashboard from "./components/BIDashboard";
import ChatPanel from "./components/ChatPanel";
import ToastContainer, { showToast } from "./components/ToastContainer";
import { Menu, Volume2, VolumeX, Moon, Sun, Database, MapPin } from "lucide-react";
import "./App.css";

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [thinking, setThinking] = useState(false);
  const [pendingQ, setPendingQ] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [soundOn, setSoundOn] = useState(isSoundEnabled());

  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  const fetchDashboard = useCallback(async () => {
    try {
      const result = await getDashboard();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message || "Verifica que el servidor esté activo.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

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

  const openChatWith = useCallback((question) => {
    setPendingQ(question ?? "");
  }, []);

  const handleSoundToggle = () => {
    setSoundOn(toggleSoundEnabled());
  };

  return (
    <div className="font-sans text-slate-800 dark:text-slate-100 bg-slate-50 dark:bg-[#0c0f14] min-h-screen selection:bg-brand-500 selection:text-white transition-colors duration-200">
      <header className="sticky top-0 z-40 w-full border-b border-slate-200 dark:border-slate-800/80 bg-white/80 dark:bg-[#0c0f14]/85 backdrop-blur-md transition-all">
        <div className="px-4 lg:px-6 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="lg:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-600 via-emerald-500 to-amber-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white font-black text-sm">
                N
              </div>
              <div>
                <span className="font-bold tracking-tight text-sm md:text-base text-slate-900 dark:text-white flex items-center gap-2">
                  Nexo IA
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 hidden sm:inline-flex items-center gap-1">
                    <Database className="w-3 h-3" /> IPS Colombia
                  </span>
                </span>
              </div>
            </div>
          </div>

          <div className="hidden md:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <MapPin className="w-3.5 h-3.5 text-emerald-500" />
            <span className="font-medium">Fuente: datos.gov.co · REPS (corte nov 2022)</span>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={handleSoundToggle} title="Activar/Desactivar micro-sonidos" className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 dark:text-slate-400 transition-colors">
              {soundOn ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>
            <button onClick={toggleTheme} className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 dark:text-slate-400 transition-colors" title="Cambiar tema">
              {theme === "dark" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            </button>
            <div
              className="flex items-center gap-2 pl-1 cursor-pointer"
              onClick={() => showToast("Nexo IA", "Asistente de datos de IPS colombianas")}
            >
              <div className="w-8 h-8 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 flex items-center justify-center font-bold text-xs shadow-md">
                N
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="min-h-[calc(100vh-3.5rem)] flex relative">
        <BIDashboard
          data={data}
          loading={loading}
          error={error}
          onRetry={fetchDashboard}
          onInspect={openChatWith}
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
        />
      </div>

      <ChatPanel
        ask={handleAsk}
        isThinking={thinking}
        pendingQuestion={pendingQ}
        onPendingHandled={() => setPendingQ(null)}
      />

      <ToastContainer />
    </div>
  );
}

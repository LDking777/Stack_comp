import { useState, useEffect, useCallback } from "react";
import { getDashboard, askNexo, getOrCreateSessionId } from "./api";
import { useTheme } from "./context/ThemeContext";
import { toggleSoundEnabled, isSoundEnabled, playTone } from "./utils/soundEffects";
import BIDashboard from "./components/BIDashboard";
import CognitiveDashboard from "./components/CognitiveDashboard";
import PitchSection from "./components/PitchSection";
import ChatPanel from "./components/ChatPanel";
import HomePage from "./pages/HomePage";
import ToastContainer, { showToast } from "./components/ToastContainer";
import { Menu, Sparkles, LayoutDashboard, Volume2, VolumeX, Moon, Sun, Database, MapPin, Radio, House } from "lucide-react";
import "./App.css";

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [thinking, setThinking] = useState(false);
  const [pendingQ, setPendingQ] = useState(null);
  const [consolePendingQ, setConsolePendingQ] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeView, setActiveView] = useState("home"); // 'home' | 'cognitive' | 'bi' | 'pitch'
  const [soundOn, setSoundOn] = useState(isSoundEnabled());
  const [currentTime, setCurrentTime] = useState(new Date());
  const [sessionId] = useState(() => getOrCreateSessionId());

  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

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

  useEffect(() => {
    if (activeView === "bi") {
      fetchDashboard();
    }
  }, [fetchDashboard, activeView]);

  const handleAsk = useCallback(async (question, options = {}) => {
    setThinking(true);
    try {
      const res = await askNexo(question, { ...options, sessionId });
      return { ok: true, data: res };
    } catch (err) {
      return { ok: false, error: err.message || "No se pudo consultar el backend." };
    } finally {
      setThinking(false);
    }
  }, [sessionId]);

  const openChatWith = useCallback((question) => {
    setPendingQ(question ?? "");
  }, []);

  const openConsoleWith = useCallback((question) => {
    setConsolePendingQ(question ?? "");
    setActiveView("cognitive");
  }, []);

  const handleSoundToggle = () => {
    setSoundOn(toggleSoundEnabled());
  };

  return (
    <div className="font-sans text-slate-800 dark:text-slate-100 bg-slate-50 dark:bg-[#0c0f14] min-h-screen selection:bg-emerald-500 selection:text-white transition-colors duration-200">
      
      {/* Header Unificado Nexo IA */}
      <header className={`app-header sticky top-0 z-40 w-full border-b border-slate-200 dark:border-slate-800/80 bg-white/80 dark:bg-[#0c0f14]/85 backdrop-blur-md transition-all ${activeView === "home" ? "home-header" : ""}`}>
        <div className="px-4 lg:px-6 h-14 flex items-center justify-between gap-4">
          
          {/* Logo y Nombre */}
          <div className="flex items-center gap-3">
            {activeView === "bi" && (
              <button 
                onClick={() => setSidebarOpen(!sidebarOpen)} 
                className="lg:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <Menu className="w-5 h-5" />
              </button>
            )}
            <div 
              className="flex items-center gap-2.5 cursor-pointer" 
              onClick={() => { playTone("click"); setActiveView("home"); }}
            >
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
            {activeView === "home" && (
              <span className="home-brand-divider">VOICE INTELLIGENCE</span>
            )}
          </div>

          {/* Switcher de Vistas: Inicio vs Consola Vocal vs Tablero BI vs Pitch */}
          <div className="flex items-center bg-slate-100 dark:bg-slate-900/90 p-1 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-semibold overflow-x-auto">
            <button 
              onClick={() => { setActiveView("home"); playTone("click"); }} 
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeView === "home" 
                  ? "bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white font-bold" 
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <House className="w-3.5 h-3.5 text-emerald-500" />
              <span>Inicio</span>
            </button>
            <button 
              onClick={() => { setActiveView("cognitive"); playTone("click"); }} 
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeView === "cognitive" 
                  ? "bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white font-bold" 
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <Radio className="w-3.5 h-3.5 text-emerald-500" />
              <span>Consola Vocal</span>
            </button>
            <button 
              onClick={() => { setActiveView("bi"); playTone("click"); }} 
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeView === "bi" 
                  ? "bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white font-bold" 
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <LayoutDashboard className="w-3.5 h-3.5 text-blue-500" />
              <span>Tablero BI</span>
            </button>
            <button 
              onClick={() => { setActiveView("pitch"); playTone("click"); }} 
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                activeView === "pitch" 
                  ? "bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white font-bold" 
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              <span className="hidden sm:inline">Pitch & Arquitectura</span>
              <span className="sm:hidden">Pitch</span>
            </button>
          </div>

          {/* Controles de Header */}
          <div className="flex items-center gap-2">
            <div className="hidden xl:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 border-r border-slate-200 dark:border-slate-800 pr-3">
              <MapPin className="w-3.5 h-3.5 text-emerald-500" />
              <span className="font-medium">datos.gov.co · REPS</span>
              <span className="text-slate-300 dark:text-slate-700">•</span>
              <span className="font-mono font-medium text-slate-700 dark:text-slate-300">
                {currentTime.toLocaleTimeString("es-CO", { timeZone: "America/Bogota", hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>

            <button 
              onClick={handleSoundToggle} 
              title="Activar/Desactivar micro-sonidos" 
              className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 dark:text-slate-400 transition-colors"
            >
              {soundOn ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>
            
            <button 
              onClick={toggleTheme} 
              className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 dark:text-slate-400 transition-colors" 
              title="Cambiar tema"
            >
              {theme === "dark" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            </button>
            
            <div
              className="flex items-center gap-2 pl-1 cursor-pointer"
              onClick={() => showToast("Nexo IA", "Asistente Cognitivo de IPS de Colombia")}
            >
              <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold text-xs shadow-md">
                N
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Contenido Principal segun la vista seleccionada */}
      <div className="min-h-[calc(100vh-3.5rem)] flex relative">
        {activeView === "home" && (
          <HomePage>
            <ChatPanel
              embedded
              ask={handleAsk}
              isThinking={thinking}
              pendingQuestion={pendingQ}
              onPendingHandled={() => setPendingQ(null)}
              sessionId={sessionId}
            />
          </HomePage>
        )}
        {activeView === "cognitive" && (
          <CognitiveDashboard 
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
            onOpenPitch={() => setActiveView("pitch")} 
            onAskAI={handleAsk}
            initialQuestion={consolePendingQ}
            onClearInitialQuestion={() => setConsolePendingQ(null)}
          />
        )}
        {activeView === "bi" && (
          <BIDashboard
            data={data}
            loading={loading}
            error={error}
            onRetry={fetchDashboard}
            onInspect={openChatWith}
            onVoiceInspect={openConsoleWith}
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
          />
        )}
        {activeView === "pitch" && (
          <PitchSection 
            onExploreDashboard={() => setActiveView("cognitive")} 
            onExploreWithQuestion={(q) => openConsoleWith(q)}
          />
        )}
      </div>

      {/* Asistente Flotante Secundario Nexo IA (activo cuando no es home embebido) */}
      {activeView !== "home" && (
        <ChatPanel
          ask={handleAsk}
          isThinking={thinking}
          pendingQuestion={pendingQ}
          onPendingHandled={() => setPendingQ(null)}
          sessionId={sessionId}
        />
      )}

      <ToastContainer />
    </div>
  );
}

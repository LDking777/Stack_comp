import { useState, useEffect, useCallback } from "react";
import { getDashboard, askNexo } from "./api";
import { useTheme } from "./context/ThemeContext";
import { getFrictionDiagnostic, submodulesInfo } from "./data/frictionDiagnostics";
import { toggleSoundEnabled, isSoundEnabled, playTone } from "./utils/soundEffects";
import BIDashboard from "./components/BIDashboard";
import ChatPanel from "./components/ChatPanel";
import PitchSection from "./components/PitchSection";
import FrictionReplayModal from "./components/FrictionReplayModal";
import SubmoduleModal from "./components/SubmoduleModal";
import ToastContainer, { showToast } from "./components/ToastContainer";
import { Menu, Sparkles, LayoutDashboard, MapPin, Volume2, VolumeX, Moon, Sun, Bell, Settings, ArrowRight } from "lucide-react";
import "./App.css";

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [thinking, setThinking] = useState(false);
  const [pendingQ, setPendingQ] = useState(null);
  const [activeNav, setActiveNav] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeView, setActiveView] = useState("pitch");
  const [soundOn, setSoundOn] = useState(isSoundEnabled());
  const [modalState, setModalState] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
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

  const handleNavClick = (id) => {
    setActiveNav(id);
    setSidebarOpen(false);
    if (id === "dashboard") {
      setActiveView("dashboard");
    } else {
      const info = submodulesInfo?.find(m => m.id === id) || { 
        id, 
        title: id, 
        description: "Módulo en construcción." 
      };
      setModalState({ type: "submodule", data: info });
    }
  };

  const handleFrictionClick = (f) => {
    const diagnostic = getFrictionDiagnostic(f.url, f.metrica);
    setModalState({ type: "friction", data: diagnostic });
  };

  return (
    <div className="font-sans text-slate-800 dark:text-slate-100 bg-slate-50 dark:bg-[#0c0f14] min-h-screen selection:bg-brand-500 selection:text-white transition-colors duration-200">
      
      <header className="sticky top-0 z-40 w-full border-b border-slate-200 dark:border-slate-800/80 bg-white/80 dark:bg-[#0c0f14]/85 backdrop-blur-md transition-all">
        <div className="px-4 lg:px-6 h-14 flex items-center justify-between gap-4">
          
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="lg:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => setActiveView('pitch')}>
              {/* [NOMBRE PROVISIONAL]: Reemplazar cuando se definan los puntos de la hackathon */}
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-600 via-emerald-500 to-amber-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white font-black text-sm">
                HP
              </div>
              <div>
                <span className="font-bold tracking-tight text-sm md:text-base text-slate-900 dark:text-white flex items-center gap-2">
                  Hackathon Propuesta
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 hidden sm:inline-flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Eje Cafetero AI
                  </span>
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center bg-slate-100 dark:bg-slate-900/90 p-1 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-semibold">
            <button onClick={() => { setActiveView('pitch'); playTone('click'); }} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${activeView === 'pitch' ? 'bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white font-bold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}`}>
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              <span>Pitch & Innovación</span>
            </button>
            <button onClick={() => { setActiveView('dashboard'); setActiveNav('dashboard'); playTone('click'); }} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${activeView === 'dashboard' ? 'bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white font-bold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}`}>
              <LayoutDashboard className="w-3.5 h-3.5 text-emerald-500" />
              <span>Dashboard En Vivo</span>
            </button>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden xl:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 border-r border-slate-200 dark:border-slate-800 pr-3">
              <MapPin className="w-3.5 h-3.5 text-rose-500" />
              <span className="font-medium">Manizales, Caldas, Colombia</span>
              <span className="text-slate-300 dark:text-slate-700">•</span>
              <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{currentTime.toLocaleTimeString("es-CO", { timeZone: "America/Bogota", hour: '2-digit', minute:'2-digit' })}</span>
            </div>

            <button onClick={handleSoundToggle} title="Activar/Desactivar micro-sonidos" className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 dark:text-slate-400 transition-colors">
              {soundOn ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>

            <button onClick={toggleTheme} className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 dark:text-slate-400 transition-colors" title="Cambiar tema">
              {theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            </button>

            <div className="relative">
              <button onClick={() => { playTone('error'); showToast('Alerta de fricción', 'Pico de RageClicks detectado en pasarela de pagos PSE', 'warning'); }} className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 dark:text-slate-400 transition-colors relative">
                <Bell className="w-4 h-4" />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full ring-2 ring-white dark:ring-slate-900"></span>
              </button>
            </div>

            <button onClick={() => handleNavClick("config")} className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 dark:text-slate-400 transition-colors">
              <Settings className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-2 pl-1 cursor-pointer" onClick={() => showToast('Sesión Activa', 'Analista Principal: Hackathon Team Caldas Tech')}>
              <div className="w-8 h-8 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 flex items-center justify-center font-bold text-xs shadow-md">
                HP
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="min-h-[calc(100vh-3.5rem)] flex relative">
        {activeView === 'pitch' ? (
          <PitchSection onExploreDashboard={() => { setActiveView("dashboard"); setActiveNav("dashboard"); }} />
        ) : (
          <BIDashboard
            data={data}
            loading={loading}
            error={error}
            onRetry={fetchDashboard}
            onInspect={openChatWith}
            onFrictionClick={handleFrictionClick}
            activeNav={activeNav}
            handleNavClick={handleNavClick}
            sidebarOpen={sidebarOpen}
            setSidebarOpen={setSidebarOpen}
          />
        )}
      </div>

      <ChatPanel
        ask={handleAsk}
        isThinking={thinking}
        pendingQuestion={pendingQ}
        onPendingHandled={() => setPendingQ(null)}
      />

      {modalState?.type === "friction" && (
        <FrictionReplayModal 
          diagnostic={modalState.data} 
          onClose={() => setModalState(null)} 
          onAskNexo={(q) => { setModalState(null); openChatWith(q); }}
        />
      )}
      
      {modalState?.type === "submodule" && (
        <SubmoduleModal 
          moduleInfo={modalState.data} 
          onClose={() => setModalState(null)} 
        />
      )}

      <ToastContainer />
    </div>
  );
}
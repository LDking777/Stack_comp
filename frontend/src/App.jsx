import { useState, useEffect, useCallback } from "react";
import { getDashboard, askNexo } from "./api";
import { useTheme } from "./context/ThemeContext";
import { toggleSoundEnabled, isSoundEnabled, playTone } from "./utils/soundEffects";
import CognitiveDashboard from "./components/CognitiveDashboard";
import PitchSection from "./components/PitchSection";
import ChatPanel from "./components/ChatPanel";
import ToastContainer, { showToast } from "./components/ToastContainer";
import { Menu, Sparkles, LayoutDashboard, Volume2, VolumeX, Moon, Sun, Bell, Bot, Radio } from "lucide-react";
import "./App.css";

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [pendingQ, setPendingQ] = useState(null);
  const [activeView, setActiveView] = useState("pitch"); // 'pitch' | 'dashboard'
  const [soundOn, setSoundOn] = useState(isSoundEnabled());
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

  const handleAsk = useCallback(async (question) => {
    setThinking(true);
    try {
      const res = await askNexo(question);
      return { ok: true, data: res };
    } catch (err) {
      return { ok: false, error: err.message || "No se pudo consultar el backend." };
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
    <div className="font-sans text-slate-800 dark:text-slate-100 bg-slate-50 dark:bg-[#0c0f14] min-h-screen selection:bg-emerald-500 selection:text-white transition-colors duration-200">
      
      {/* Header Oficial Kognia Labs */}
      <header className="sticky top-0 z-40 w-full border-b border-slate-200 dark:border-slate-800/80 bg-white/80 dark:bg-[#0c0f14]/85 backdrop-blur-md transition-all">
        <div className="px-4 lg:px-6 h-14 flex items-center justify-between gap-4">
          
          {/* Logo y Nombre del Proyecto */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => setActiveView('pitch')}>
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-600 via-teal-500 to-amber-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white font-black text-sm">
                KL
              </div>
              <div>
                <span className="font-bold tracking-tight text-sm md:text-base text-slate-900 dark:text-white flex items-center gap-2">
                  Kognia Labs
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 hidden sm:inline-flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Reto 01 · Agente Vocal
                  </span>
                </span>
              </div>
            </div>
          </div>

          {/* Switcher de Vistas: Pitch vs Consola Vocal / Dashboard */}
          <div className="flex items-center bg-slate-100 dark:bg-slate-900/90 p-1 rounded-xl border border-slate-200 dark:border-slate-800 text-xs font-semibold">
            <button 
              onClick={() => { setActiveView('pitch'); playTone('click'); }} 
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${activeView === 'pitch' ? 'bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white font-bold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}`}
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              <span>Pitch & Arquitectura</span>
            </button>
            <button 
              onClick={() => { setActiveView('dashboard'); playTone('click'); }} 
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${activeView === 'dashboard' ? 'bg-white dark:bg-slate-800 shadow-sm text-slate-900 dark:text-white font-bold' : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'}`}
            >
              <Radio className="w-3.5 h-3.5 text-emerald-500" />
              <span>Consola Vocal en Vivo</span>
            </button>
          </div>

          {/* Controles y Ajustes */}
          <div className="flex items-center gap-3">
            <div className="hidden xl:flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 border-r border-slate-200 dark:border-slate-800 pr-3">
              <span className="font-medium">Hackatón Kognia Labs</span>
              <span className="text-slate-300 dark:text-slate-700">•</span>
              <span className="font-mono font-medium text-slate-700 dark:text-slate-300">
                {currentTime.toLocaleTimeString("es-CO", { timeZone: "America/Bogota", hour: '2-digit', minute:'2-digit' })}
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
              title="Cambiar tema oscuro/claro"
            >
              {theme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
            </button>

            <div className="flex items-center gap-2 pl-1 cursor-pointer" onClick={() => showToast('Demo de Hackatón', 'Agente Vocal Cognitivo preparado para el jurado')}>
              <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold text-xs shadow-md">
                KL
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Contenido Principal */}
      <div className="min-h-[calc(100vh-3.5rem)] flex relative">
        {activeView === 'pitch' ? (
          <PitchSection onExploreDashboard={() => setActiveView("dashboard")} />
        ) : (
          <CognitiveDashboard onOpenPitch={() => setActiveView("pitch")} />
        )}
      </div>

      {/* Asistente Flotante Secundario Nexo IA */}
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
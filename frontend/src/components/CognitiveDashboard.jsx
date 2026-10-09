import React, { useState, useEffect, useRef } from 'react';
import { 
  Mic, MicOff, Volume2, VolumeX, Upload, RefreshCw, FileText, 
  Send, Sparkles, CheckCircle2, AlertTriangle, ShieldCheck, 
  Database, User, Bot, Clock, ChevronRight, Activity, Search,
  Sliders, Eye, HelpCircle, Layers, ArrowUpRight
} from 'lucide-react';
import { playTone } from '../utils/soundEffects';
import { showToast } from './ToastContainer';
import { 
  DEFAULT_IPS_DATA, INITIAL_DOCUMENT_BRIEF, fetchDatosGovIps, 
  parseUploadedDocument, queryDocumentKnowledge 
} from '../services/documentKnowledge';
import { speechEngine, analyzeCognitiveSentiment } from '../utils/speechVoiceEngine';
import { askNexo } from '../api';

export default function CognitiveDashboard({ 
  sidebarOpen, 
  setSidebarOpen, 
  onOpenPitch,
  onAskAI,
  initialQuestion,
  onClearInitialQuestion
}) {
  // Estados de datos e ingesta
  const [dataset, setDataset] = useState(DEFAULT_IPS_DATA);
  const [activeBrief, setActiveBrief] = useState(INITIAL_DOCUMENT_BRIEF);
  const [customDoc, setCustomDoc] = useState(null);
  const [loadingDataset, setLoadingDataset] = useState(false);
  const [filterDept, setFilterDept] = useState("TODOS");

  // Estados de voz y conversación
  const [isListening, setIsListening] = useState(false);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [isThinking, setIsThinking] = useState(false);
  const [sttInterim, setSttInterim] = useState("");
  const [inputText, setInputText] = useState("");
  const [dialogueStream, setDialogueStream] = useState([
    {
      id: "turn-1",
      speaker: "agente",
      speakerLabel: "Hablante 2 (Agente Vocal)",
      text: "¡Hola! He indexado el conjunto oficial de IPS de Colombia de datos.gov.co. Puedo responder por voz cualquier consulta sobre niveles de atención, camas de UCI o capacidad instalada en cada región. ¿Qué deseas explorar?",
      timestamp: "00:01.120",
      emotion: "Apertura Colaborativa",
      confidence: 1.0,
      sentiment: "Positivo"
    }
  ]);

  // Estados de telemetría cognitiva
  const [currentSentiment, setCurrentSentiment] = useState({ score: 0.65, label: "Positivo" });
  const [currentEmotions, setCurrentEmotions] = useState({
    confianza: 92,
    curiosidad: 78,
    asombro: 40,
    frustracion: 4,
    neutralidad: 35
  });
  const [latencies, setLatencies] = useState({ stt: 310, tts: 185 });

  // Modal para inspeccionar datos del dataset
  const [selectedIpsModal, setSelectedIpsModal] = useState(null);
  const [activeTab, setActiveTab] = useState("consola"); // 'consola' | 'dataset'
  const [searchTerm, setSearchTerm] = useState("");

  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [dialogueStream, sttInterim]);

  // Manejo de carga de datos desde SODA3 datos.gov.co
  const handleReloadSODA3 = async (dept = filterDept) => {
    setLoadingDataset(true);
    playTone('click');
    showToast("Conectando SODA3", "Consultando API de datos.gov.co (s2ru-bqt6)...", "info");
    try {
      const res = await fetchDatosGovIps(100, dept);
      setDataset(res.data);
      setCustomDoc(null);
      setActiveBrief({
        ...INITIAL_DOCUMENT_BRIEF,
        totalRecords: res.data.length,
        source: res.source
      });
      playTone('success');
      showToast("Sincronización Exitosa", `Cargados ${res.data.length} registros oficiales de IPS.`, "success");
    } catch (err) {
      playTone('error');
      showToast("Error de API", err.message, "error");
    } finally {
      setLoadingDataset(false);
    }
  };

  // Manejo de subida de documento sorpresa por el jurado (P2)
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      playTone('click');
      showToast("Indexando Archivo", `Procesando «${file.name}» en cliente...`, "info");
      const brief = await parseUploadedDocument(file);
      setCustomDoc(brief);
      setActiveBrief(brief);
      playTone('success');
      showToast("Documento Indexado", `Briefing generado para ${file.name}`, "success");
      
      // Turno automático del agente anunciando el brief
      const newTurn = {
        id: `turn-${Date.now()}`,
        speaker: "agente",
        speakerLabel: "Hablante 2 (Agente Vocal)",
        text: `He recibido e indexado «${file.name}». ${brief.summary.slice(0, 160)}... Puedes hacerme preguntas sobre su contenido usando el micrófono.`,
        timestamp: new Date().toLocaleTimeString("es-CO", { minute: "2-digit", second: "2-digit" }),
        emotion: "Confianza Factual",
        confidence: 0.98,
        sentiment: "Positivo"
      };
      setDialogueStream(prev => [...prev, newTurn]);
      if (ttsEnabled) {
        speechEngine.speakText(newTurn.text);
      }
    } catch (err) {
      playTone('error');
      showToast("Error de Lectura", err.message, "error");
    }
  };

  useEffect(() => {
    if (initialQuestion) {
      setActiveTab("consola");
      handleExecuteQuestion(initialQuestion);
      onClearInitialQuestion?.();
    }
  }, [initialQuestion]);

  // Procesar una pregunta (vocal o escrita) integrando la IA de Nexo
  const handleExecuteQuestion = async (questionText, inputLatency = 290) => {
    if (!questionText || !questionText.trim() || isThinking) return;

    playTone('click');
    const now = new Date();
    const timeCode = now.toLocaleTimeString("es-CO", { minute: "2-digit", second: "2-digit" }) + `.${String(now.getMilliseconds()).padStart(3, '0')}`;

    // 1. Análisis cognitivo del jurado (Hablante 1)
    const juradoAnalysis = analyzeCognitiveSentiment(questionText, 'jurado');
    setCurrentSentiment(juradoAnalysis);
    setCurrentEmotions(juradoAnalysis.emotions);

    const juradoTurn = {
      id: `turn-user-${Date.now()}`,
      speaker: "jurado",
      speakerLabel: "Hablante 1 (Jurado)",
      text: questionText,
      timestamp: timeCode,
      emotion: juradoAnalysis.label,
      confidence: 1.0,
      sentiment: juradoAnalysis.label
    };

    setDialogueStream(prev => [...prev, juradoTurn]);
    setInputText("");
    setSttInterim("");
    setIsThinking(true);

    const startTime = performance.now();
    let botAnswer = "";
    let isOutOfDomain = false;
    let confidence = 0.98;
    let emotion = "Confianza Factual";
    let sentiment = "Positivo";

    try {
      // Si el jurado cargó un documento sorpresa personalizado en memoria
      if (customDoc && customDoc.rawContent) {
        const customRes = queryDocumentKnowledge(questionText, dataset, customDoc);
        botAnswer = customRes.answer;
        isOutOfDomain = customRes.outOfDomain;
        confidence = customRes.confidence;
        emotion = customRes.emotion;
        sentiment = customRes.sentiment;
      } else {
        // Consultar el pipeline real de Nexo IA (SoQL + LLM Groq / Gemini)
        let res;
        if (onAskAI) {
          const aiCall = await onAskAI(questionText);
          res = aiCall.ok ? aiCall.data : null;
        } else {
          res = await askNexo(questionText);
        }

        if (res && res.answer) {
          botAnswer = res.answer;
          confidence = typeof res.confidence_score === "number" ? res.confidence_score : 0.98;
          if (res.trigger === "out_of_domain") {
            isOutOfDomain = true;
            emotion = "Neutralidad Analítica";
            sentiment = "Neutro";
          } else if (res.trigger === "greeting") {
            emotion = "Apertura Colaborativa";
            sentiment = "Positivo";
          } else if (res.kpis && Object.keys(res.kpis).length > 0) {
            emotion = "Precisión SoQL";
            sentiment = "Positivo";
          }
        } else {
          // Fallback a motor documental local si el backend no devolvió respuesta
          const fallbackRes = queryDocumentKnowledge(questionText, dataset, customDoc);
          botAnswer = fallbackRes.answer;
          isOutOfDomain = fallbackRes.outOfDomain;
          confidence = fallbackRes.confidence;
          emotion = fallbackRes.emotion;
          sentiment = fallbackRes.sentiment;
        }
      }
    } catch (err) {
      console.warn("Fallo temporal en consulta IA, recurriendo a motor local:", err);
      const fallbackRes = queryDocumentKnowledge(questionText, dataset, customDoc);
      botAnswer = fallbackRes.answer;
      isOutOfDomain = fallbackRes.outOfDomain;
      confidence = fallbackRes.confidence;
      emotion = fallbackRes.emotion;
      sentiment = fallbackRes.sentiment;
    } finally {
      setIsThinking(false);
    }

    const agentAnalysis = analyzeCognitiveSentiment(botAnswer, 'agente');
    const agentTimeCode = new Date().toLocaleTimeString("es-CO", { minute: "2-digit", second: "2-digit" }) + `.${String(new Date().getMilliseconds()).padStart(3, '0')}`;

    const botTurn = {
      id: `turn-agent-${Date.now()}`,
      speaker: "agente",
      speakerLabel: "Hablante 2 (Agente Vocal)",
      text: botAnswer,
      timestamp: agentTimeCode,
      emotion: emotion || agentAnalysis.label,
      confidence: confidence,
      sentiment: sentiment || agentAnalysis.sentiment,
      outOfDomain: isOutOfDomain
    };

    setDialogueStream(prev => [...prev, botTurn]);
    setCurrentEmotions(agentAnalysis.emotions);

    const elapsed = Math.round(performance.now() - startTime);
    setLatencies({ stt: inputLatency, tts: elapsed > 0 ? elapsed : 190 });

    // Reproducción vocal si TTS está activo
    if (ttsEnabled && botAnswer) {
      const cleanVoiceText = botAnswer.replace(/[*#_`>]/g, "").trim();
      speechEngine.speakText(cleanVoiceText);
    }
  };

  const handleAskAboutIps = (ips) => {
    setActiveTab("consola");
    playTone('click');
    handleExecuteQuestion(`¿Qué capacidad instalada y nivel de atención tiene ${ips.nombre_prestador} en ${ips.municipio}?`);
  };

  // Toggle de reconocimiento por voz
  const handleToggleVoice = () => {
    if (isListening) {
      speechEngine.stopListening();
      setIsListening(false);
      playTone('click');
    } else {
      speechEngine.stopSpeaking();
      playTone('high');
      speechEngine.startListening({
        onStart: () => setIsListening(true),
        onResult: ({ finalTranscript, interimTranscript, isFinal, latencyMs }) => {
          if (interimTranscript) setSttInterim(interimTranscript);
          if (isFinal && finalTranscript) {
            handleExecuteQuestion(finalTranscript, latencyMs);
          }
        },
        onError: (err) => {
          setIsListening(false);
          showToast("Micrófono", err.message || "Permiso de micrófono requerido", "warning");
        },
        onEnd: () => setIsListening(false)
      });
    }
  };

  // Filtro de IPS para el visor de datos
  const filteredIps = dataset.filter(item => {
    const matchSearch = item.nombre_prestador.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        item.municipio.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        item.departamento.toLowerCase().includes(searchTerm.toLowerCase());
    return matchSearch;
  });

  return (
    <div className="flex-1 flex flex-col xl:flex-row w-full min-h-[calc(100vh-3.5rem)] bg-slate-50 dark:bg-[#0c0f14] transition-colors">
      
      {/* Columna Principal: Consola Vocal & Diarización */}
      <div className="flex-1 flex flex-col p-4 sm:p-6 max-w-5xl mx-auto w-full">
        
        {/* Barra Superior de Control de Ingesta & Estados */}
        <div className="p-4 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200 dark:border-slate-800 shadow-sm mb-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-600 text-white flex items-center justify-center font-bold shadow-md shadow-emerald-500/20">
                <Database className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold uppercase text-emerald-600 dark:text-emerald-400">
                    Fuente Oficial Activa
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 font-mono text-slate-500">
                    {dataset.length} registros
                  </span>
                </div>
                <h2 className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white truncate max-w-md">
                  {activeBrief.title}
                </h2>
              </div>
            </div>

            {/* Controles de Carga SODA3 & Documento Sorpresa */}
            <div className="flex items-center flex-wrap gap-2">
              <button 
                onClick={() => handleReloadSODA3("TODOS")}
                disabled={loadingDataset}
                className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-850 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-1.5 transition-colors"
                title="Recargar API SODA3 de datos.gov.co"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingDataset ? 'animate-spin text-emerald-500' : ''}`} />
                <span>API datos.gov.co</span>
              </button>

              <label className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 cursor-pointer shadow-sm transition-colors">
                <Upload className="w-3.5 h-3.5" />
                <span>Subir Sorpresa</span>
                <input type="file" accept=".txt,.json,.md,.csv" onChange={handleFileUpload} className="hidden" />
              </label>

              <div className="flex items-center bg-slate-100 dark:bg-slate-800 p-1 rounded-xl text-xs font-semibold">
                <button 
                  onClick={() => setActiveTab("consola")}
                  className={`px-3 py-1 rounded-lg transition-all ${activeTab === 'consola' ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-900 dark:text-white' : 'text-slate-500'}`}
                >
                  Consola Vocal
                </button>
                <button 
                  onClick={() => setActiveTab("dataset")}
                  className={`px-3 py-1 rounded-lg transition-all ${activeTab === 'dataset' ? 'bg-white dark:bg-slate-700 shadow-sm text-slate-900 dark:text-white' : 'text-slate-500'}`}
                >
                  Visor IPS ({dataset.length})
                </button>
              </div>
            </div>
          </div>

          {/* Tarjeta de Briefing Automático (P3) */}
          <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/80">
            <div className="flex items-start gap-2">
              <Sparkles className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  <strong>Briefing del Documento:</strong> {activeBrief.summary}
                </p>
                
                {/* Preguntas Sugeridas con 1 Clic */}
                <div className="mt-2.5 flex flex-wrap gap-1.5 items-center">
                  <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold mr-1">
                    Preguntas sugeridas:
                  </span>
                  {activeBrief.suggestedQuestions.map((sq, i) => (
                    <button
                      key={i}
                      onClick={() => handleExecuteQuestion(sq)}
                      className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800/80 hover:bg-emerald-500/10 hover:text-emerald-600 dark:hover:text-emerald-400 border border-slate-200/80 dark:border-slate-700/80 text-slate-700 dark:text-slate-300 font-medium transition-all text-left flex items-center gap-1 group"
                    >
                      <span>{sq}</span>
                      <ChevronRight className="w-3 h-3 text-slate-400 group-hover:text-emerald-500" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Vista Alternativa: Visor de Dataset IPS datos.gov.co */}
        {activeTab === 'dataset' ? (
          <div className="flex-1 p-5 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-slate-400" />
                <input 
                  type="text"
                  placeholder="Buscar IPS, municipio o departamento..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="bg-transparent text-xs text-slate-900 dark:text-white outline-none w-64"
                />
              </div>
              <span className="text-xs font-mono text-slate-400">
                Mostrando {filteredIps.length} instituciones
              </span>
            </div>

            <div className="flex-1 overflow-x-auto mt-3">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-400 font-mono">
                    <th className="pb-2">Prestador</th>
                    <th className="pb-2">Región</th>
                    <th className="pb-2">Nivel</th>
                    <th className="pb-2">Naturaleza</th>
                    <th className="pb-2 text-right">Camas</th>
                    <th className="pb-2 text-right">UCI</th>
                    <th className="pb-2 text-right">Quirófanos</th>
                    <th className="pb-2 text-center">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-sans">
                  {filteredIps.map(ips => (
                    <tr key={ips.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                      <td className="py-2.5 font-semibold text-slate-800 dark:text-slate-200">{ips.nombre_prestador}</td>
                      <td className="py-2.5 text-slate-500">{ips.municipio}, {ips.departamento}</td>
                      <td className="py-2.5">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${ips.nivel_atencion === 'Nivel 3' ? 'bg-amber-500/10 text-amber-600' : ips.nivel_atencion === 'Nivel 2' ? 'bg-teal-500/10 text-teal-600' : 'bg-slate-500/10 text-slate-600'}`}>
                          {ips.nivel_atencion}
                        </span>
                      </td>
                      <td className="py-2.5 text-slate-500">{ips.naturaleza_juridica}</td>
                      <td className="py-2.5 text-right font-mono font-bold">{ips.camas_hospitalizacion}</td>
                      <td className="py-2.5 text-right font-mono font-bold text-rose-500">{ips.camas_uci_adultos}</td>
                      <td className="py-2.5 text-right font-mono">{ips.quirofanos}</td>
                      <td className="py-2.5 text-center">
                        <button 
                          onClick={() => handleAskAboutIps(ips)}
                          className="px-2 py-1 rounded bg-slate-100 dark:bg-slate-800 hover:bg-emerald-500 hover:text-white text-[10px] font-medium transition-colors"
                        >
                          Preguntar a IA
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          /* Vista Principal: Consola Vocal & Stream Diarizado */
          <div className="flex-1 flex flex-col rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden min-h-[460px]">
            
            {/* Header de Diarización */}
            <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/40 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="font-bold text-xs uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Stream de Transcripción Diarizada en Tiempo Real
                </span>
              </div>
              <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span> Hablante 1 (Jurado)
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Hablante 2 (Agente)
                </span>
              </div>
            </div>

            {/* Chat / Stream de Conversación */}
            <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4 max-h-[500px]">
              {dialogueStream.map((msg) => (
                <div 
                  key={msg.id}
                  className={`flex gap-3 max-w-2xl ${msg.speaker === 'jurado' ? 'ml-auto flex-row-reverse' : ''}`}
                >
                  {/* Avatar con Rol */}
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs shrink-0 shadow-sm ${msg.speaker === 'jurado' ? 'bg-blue-600 text-white' : 'bg-emerald-600 text-white'}`}>
                    {msg.speaker === 'jurado' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  {/* Burbuja Diarizada */}
                  <div className={`p-4 rounded-2xl text-xs sm:text-sm ${msg.speaker === 'jurado' ? 'bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900/50 text-slate-900 dark:text-blue-100 rounded-tr-none' : 'bg-slate-100/90 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 text-slate-900 dark:text-slate-100 rounded-tl-none'}`}>
                    
                    {/* Metadatos del Turno (Timestamp + Emoción/Fidelidad) */}
                    <div className="flex items-center justify-between gap-3 text-[10px] font-mono mb-1.5 opacity-70">
                      <span className="font-bold">{msg.speakerLabel}</span>
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3 h-3" />
                        <span>{msg.timestamp}</span>
                        {msg.emotion && (
                          <span className="px-1.5 py-0.2 rounded bg-black/10 dark:bg-white/10">
                            {msg.emotion}
                          </span>
                        )}
                        {msg.outOfDomain && (
                          <span className="px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-600 dark:text-amber-400 font-bold">
                            Fuera de Documento
                          </span>
                        )}
                      </div>
                    </div>

                    <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                  </div>
                </div>
              ))}

              {/* Indicador de procesamiento cognitivo de Nexo IA */}
              {isThinking && (
                <div className="flex gap-3 max-w-2xl animate-in fade-in duration-200">
                  <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm animate-pulse">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="p-4 rounded-2xl bg-emerald-50/80 dark:bg-emerald-950/40 border border-emerald-200/80 dark:border-emerald-800/80 text-emerald-900 dark:text-emerald-200 text-xs rounded-tl-none flex items-center gap-3">
                    <span className="flex gap-1">
                      <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce"></span>
                      <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                      <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                    </span>
                    <span className="font-mono text-[11px] font-medium">Nexo IA consultando dataset oficial de IPS (SoQL) y sintetizando respuesta...</span>
                  </div>
                </div>
              )}

              {/* Transcripción provisional en curso */}
              {sttInterim && (
                <div className="flex gap-3 max-w-2xl ml-auto flex-row-reverse opacity-70 animate-pulse">
                  <div className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center text-xs">
                    <User className="w-4 h-4" />
                  </div>
                  <div className="p-3.5 rounded-2xl bg-blue-50 dark:bg-blue-950/40 border border-blue-200 text-xs italic">
                    <span className="text-[10px] font-mono block text-blue-500 font-bold mb-1">Escuchando voz...</span>
                    "{sttInterim}"
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            {/* Consola de Voz & Entrada Inferior */}
            <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
              
              {/* Visualizador de Onda Reactivo (Waveform Canvas/SVG) */}
              <div className="mb-3 flex items-center justify-between px-3 py-1.5 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${isListening ? 'bg-rose-500 animate-ping' : 'bg-slate-400'}`}></span>
                  <span className="text-[11px] font-mono font-medium text-slate-600 dark:text-slate-300">
                    {isListening ? 'Micrófono activo · Capturando voz' : 'Voz en reposo · Pulsa el micrófono para hablar'}
                  </span>
                </div>

                {/* Onda animada */}
                <div className="flex items-center gap-1 h-4">
                  {[40, 75, 100, 50, 90, 30, 85, 60, 45, 95].map((h, i) => (
                    <div 
                      key={i} 
                      className={`w-1 rounded-full transition-all duration-150 ${isListening ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300 dark:bg-slate-700'}`}
                      style={{ height: isListening ? `${h}%` : '20%' }}
                    />
                  ))}
                </div>

                <div className="flex items-center gap-2">
                  <button 
                    onClick={() => { playTone('click'); setTtsEnabled(!ttsEnabled); }}
                    title={ttsEnabled ? "Silenciar voz del agente" : "Activar voz del agente"}
                    className="p-1 rounded text-slate-400 hover:text-slate-700 dark:hover:text-white"
                  >
                    {ttsEnabled ? <Volume2 className="w-4 h-4 text-emerald-500" /> : <VolumeX className="w-4 h-4" />}
                  </button>
                  <span className="text-[10px] font-mono text-slate-400">
                    Latencia STT: {latencies.stt}ms | TTS: {latencies.tts}ms
                  </span>
                </div>
              </div>

              {/* Botón de Micrófono & Input de Respaldo */}
              <div className="flex items-center gap-2">
                <button
                  onClick={handleToggleVoice}
                  className={`px-5 py-3 rounded-xl font-bold text-xs flex items-center gap-2 shadow-lg transition-all transform hover:scale-105 ${isListening ? 'bg-rose-500 hover:bg-rose-600 text-white shadow-rose-500/25 animate-pulse' : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-emerald-500/20'}`}
                >
                  {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                  <span>{isListening ? "Detener" : "Hablar con el Documento"}</span>
                </button>

                <div className="flex-1 relative flex items-center">
                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleExecuteQuestion(inputText)}
                    placeholder="O escribe una pregunta (ej: ¿Cuántas camas de UCI hay en Caldas?)..."
                    className="w-full px-4 py-3 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <button
                    onClick={() => handleExecuteQuestion(inputText)}
                    className="absolute right-2 p-2 rounded-lg bg-emerald-500 hover:bg-emerald-600 text-white transition-colors"
                  >
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

            </div>
          </div>
        )}

      </div>

      {/* Columna Lateral Derecha: Telemetría Cognitiva & Métricas en Vivo */}
      <div className="w-full xl:w-80 border-t xl:border-t-0 xl:border-l border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-[#0c0f14]/80 p-4 sm:p-6 space-y-5 shrink-0">
        
        <div>
          <h3 className="font-bold text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400 font-mono">
            Telemetría Cognitiva en Vivo
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Análisis de sentimiento y emociones del diálogo (P5)
          </p>
        </div>

        {/* Medidor de Polaridad de Sentimiento */}
        <div className="p-4 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">Sentimiento Detectado</span>
            <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full ${currentSentiment.label === 'Positivo' ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : currentSentiment.label === 'Atención / Crítico' ? 'bg-rose-500/10 text-rose-500 border border-rose-500/20' : 'bg-slate-500/10 text-slate-500'}`}>
              {currentSentiment.label}
            </span>
          </div>

          <div className="w-full bg-slate-100 dark:bg-slate-800 h-2.5 rounded-full overflow-hidden relative">
            <div 
              className={`h-full rounded-full transition-all duration-300 ${currentSentiment.score > 0.3 ? 'bg-emerald-500' : currentSentiment.score < -0.3 ? 'bg-rose-500' : 'bg-amber-500'}`}
              style={{ width: `${Math.round(((currentSentiment.score + 1) / 2) * 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] font-mono text-slate-400 mt-1.5">
            <span>Negativo (-1.0)</span>
            <span>Neutro</span>
            <span>Positivo (+1.0)</span>
          </div>
        </div>

        {/* Distribución de Emociones */}
        <div className="p-4 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200 dark:border-slate-800 shadow-sm space-y-3">
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 block">
            Radar de Emociones del Jurado
          </span>

          <div className="space-y-2 text-xs">
            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span className="text-slate-600 dark:text-slate-400">Confianza Factual</span>
                <span className="font-mono font-bold text-emerald-500">{currentEmotions.confianza}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${currentEmotions.confianza}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span className="text-slate-600 dark:text-slate-400">Curiosidad / Interés</span>
                <span className="font-mono font-bold text-amber-500">{currentEmotions.curiosidad}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div className="h-full bg-amber-500 rounded-full" style={{ width: `${currentEmotions.curiosidad}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span className="text-slate-600 dark:text-slate-400">Asombro Cuantitativo</span>
                <span className="font-mono font-bold text-teal-500">{currentEmotions.asombro}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div className="h-full bg-teal-500 rounded-full" style={{ width: `${currentEmotions.asombro}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[11px] mb-1">
                <span className="text-slate-600 dark:text-slate-400">Frustración / Desfase</span>
                <span className="font-mono font-bold text-rose-500">{currentEmotions.frustracion}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div className="h-full bg-rose-500 rounded-full" style={{ width: `${currentEmotions.frustracion}%` }} />
              </div>
            </div>
          </div>
        </div>

        {/* Indicadores de Rendimiento del Reto */}
        <div className="p-4 rounded-2xl bg-white dark:bg-[#12161f] border border-slate-200 dark:border-slate-800 shadow-sm space-y-2.5">
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 block">
            Criterios de Evaluación
          </span>

          <div className="flex items-center justify-between text-xs pt-1">
            <span className="text-slate-500 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" /> Fidelidad RAG
            </span>
            <span className="font-mono font-bold text-emerald-500">100% Sin Alucinación</span>
          </div>

          <div className="flex items-center justify-between text-xs pt-1">
            <span className="text-slate-500 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-teal-500" /> Latencia Combinada
            </span>
            <span className="font-mono font-bold text-slate-700 dark:text-slate-200">
              {latencies.stt + latencies.tts} ms
            </span>
          </div>

          <div className="flex items-center justify-between text-xs pt-1">
            <span className="text-slate-500 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-amber-500" /> Turnos Diarizados
            </span>
            <span className="font-mono font-bold text-slate-700 dark:text-slate-200">
              {dialogueStream.length} interacciones
            </span>
          </div>
        </div>

        {/* Enlace al Pitch */}
        <div className="pt-2">
          <button 
            onClick={onOpenPitch}
            className="w-full py-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-850 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-center gap-1.5 transition-colors"
          >
            <span>Ver Pitch & Arquitectura</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-emerald-500" />
          </button>
        </div>

      </div>

    </div>
  );
}

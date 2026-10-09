/* [NOMBRE PROVISIONAL]: Reemplazar cuando se definan los puntos de la hackathon */
export const APP_NAME = "Hackathon Propuesta";
export const APP_SUBTITLE = "Smart Tourism Experience Analytics";

export const frictionDiagnostics = [
  {
    url: "/checkout/pago-tarjeta",
    metric: "DeadClicks",
    device: "Mobile",
    impactRate: "44.2%",
    affectedSessions: 510,
    aiIdentifiedCause: "Causa raíz de pointerdown en Safari, botón no captura eventos de toque correctamente.",
    suggestedPatchCode: "button { touch-action: manipulation; }",
    mockSessionId: "ses_001"
  },
  {
    url: "/checkout/pago-tarjeta",
    metric: "RageClicks",
    device: "Mobile",
    impactRate: "38.5%",
    affectedSessions: 450,
    aiIdentifiedCause: "Latencia alta en respuesta de PSE; el usuario cree que no ha hecho clic.",
    suggestedPatchCode: "setIsSubmitting(true);\nawait api.submit();",
    mockSessionId: "ses_002"
  },
  {
    url: "/registro/paso-2",
    metric: "DeadClicks",
    device: "Mobile",
    impactRate: "32.8%",
    affectedSessions: 640,
    aiIdentifiedCause: "Selector de fecha en tour Nevado del Ruiz bloqueado por capa invisible (z-index).",
    suggestedPatchCode: ".overlay { pointer-events: none; z-index: -1; }",
    mockSessionId: "ses_003"
  },
  {
    url: "/carrito-compras",
    metric: "RageClicks",
    device: "Mobile",
    impactRate: "27.4%",
    affectedSessions: 380,
    aiIdentifiedCause: "Botón de cupos en Termales el Otoño no refleja estado actualizado tras clic.",
    suggestedPatchCode: "mutate(data => ({...data, optimistic: true}));",
    mockSessionId: "ses_004"
  }
];

export function getFrictionDiagnostic(url, metrica) {
  const match = frictionDiagnostics.find(f => f.url === url && f.metric === metrica) 
             || frictionDiagnostics.find(f => f.url === url) 
             || frictionDiagnostics[0];
  
  return {
    url: match.url,
    impactRate: match.impactRate,
    affectedSessions: match.affectedSessions,
    aiIdentifiedCause: match.aiIdentifiedCause,
    suggestedPatchCode: match.suggestedPatchCode,
    mockSessionId: match.mockSessionId,
    device: match.device,
    metric: match.metric
  };
}

export const submodulesInfo = [
  { id: 'regional', title: 'Análisis Regional', description: 'Subregiones de Caldas: Centro Sur, Alto Occidente, Bajo Occidente, Magdalena Caldense, Norte y Alto Oriente.' },
  { id: 'kpis', title: 'KPIs de Turismo', description: 'Métricas del PND y Secretaría de Desarrollo, Empleo e Innovación: Ocupación hotelera, gasto promedio y tasa de retorno.' },
  { id: 'ops', title: 'Operaciones', description: 'Monitoreo de pasarelas de pago (PSE, Wompi, Bold), APIs de touroperadores y tiempos de respuesta de servidores.' },
  { id: 'config', title: 'Configuración', description: 'Parámetros del SDK: Frecuencia de muestreo (100%), umbral de RageClick, filtro PCI-DSS.' }
];

# ==========================================
# CAPA 1: BASE DE CONOCIMIENTOS FIJA - NEXO IA
# ==========================================

KNOWLEDGE_BASE = {
    "hola": "¡Hola! Soy NEXO IA 🤖, el núcleo analítico de CloudLabs. ¿Qué métricas o datos deseas explorar hoy?",
    
    "quien eres": "Soy NEXO IA, una inteligencia híbrida diseñada para transformar datos web en estrategias de marketing accionables para CloudLabs.",
    
    "que puedes hacer": "Puedo analizar métricas de Supabase, detectar Rage Clicks, calcular el engagement score y cruzar datos de comportamiento de usuario en tiempo real.",
    
    "quien te creo": "Fui desarrollado por Jhoann Reyes y su equipo de ingeniería como una solución de BI avanzada para la Hackathon 2026. 🚀",
    
    "dead clicks": "Los Dead Clicks son interacciones del usuario en elementos que no tienen respuesta. Un alto porcentaje indica problemas de UX que impactan directamente en tu conversión.",
    
    "engagement score": "Es nuestra métrica personalizada que combina duración de sesión, clics y profundidad de navegación para calificar el valor de cada visita.",
    
    "ayuda": "Puedes consultarme sobre: \n1. Análisis de frustración (Rage Clicks).\n2. Comportamiento por país o dispositivo.\n3. Diagnóstico de URLs específicas.",
    
    "cloudlabs": "CloudLabs es nuestra plataforma de aprendizaje líder, y mi misión es optimizar la experiencia de cada estudiante mediante el análisis de datos.",
    
    "hackathon": "Estamos compitiendo con NEXO IA, demostrando cómo la IA generativa puede realizar auditorías de marketing y UX de forma autónoma."
}

def get_fixed_response(user_input):
    """
    Busca una respuesta predefinida basada en palabras clave.
    Optimizado para detectar frases dentro de la cadena.
    """
    if not user_input:
        return None
        
    # Limpieza de input para mejorar la coincidencia
    input_limpio = user_input.lower().strip()
    
    # Prioridad: Si la palabra clave exacta está en el mensaje
    for keyword, response in KNOWLEDGE_BASE.items():
        if keyword in input_limpio:
            return response
            
    return None
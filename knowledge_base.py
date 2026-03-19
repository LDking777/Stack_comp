# ==========================================
# CAPA 1: BASE DE CONOCIMIENTOS FIJA - REVENGE
# ==========================================

# Diccionario con preguntas frecuentes y respuestas instantáneas
KNOWLEDGE_BASE = {
    "hola": "¡Hola! Soy el Asistente Inteligente de REVENGE 🤖. ¿En qué puedo ayudarte con la plataforma hoy?",
    "buenos dias": "¡Muy buenos días! Espero que tengas un excelente día. ¿Tienes alguna duda sobre REVENGE?",
    "que puedes hacer": "Puedo explicarte el funcionamiento de REVENGE, ayudarte con el registro, darte soporte técnico y mostrarte la velocidad de respuesta de nuestras IAs.",
    "que hace la plataforma": "REVENGE es una solución avanzada que optimiza [tu descripción aquí] utilizando motores de IA de última generación.",
    "quien te creo": "Fui desarrollado por Jhoann Reyes y su equipo de ingeniería para la Hackathon 2026. 🚀",
    "funciones": "Mis funciones principales son: 1. Guía de usuario, 2. Resolución de dudas técnicas, 3. Comparativa de modelos de IA en tiempo real.",
    "ayuda": "Claro, puedes preguntarme sobre cómo usar la plataforma, quiénes somos o qué tecnología utilizamos."
}

def get_fixed_response(user_input):
    """
    Busca una respuesta predefinida basada en palabras clave.
    Si encuentra una coincidencia, devuelve el texto. Si no, devuelve None.
    """
    if not user_input:
        return None
        
    # Convertimos a minúsculas para que no importe si el usuario escribe "HOLA" o "hola"
    input_limpio = user_input.lower().strip()
    
    # Recorremos el diccionario
    for keyword, response in KNOWLEDGE_BASE.items():
        if keyword in input_limpio:
            return response
            
    return None
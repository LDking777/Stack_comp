import os
import time
import telebot
import concurrent.futures
import requests
from dotenv import load_dotenv
from datetime import datetime # 👈 NUEVO: Reloj interno

# Importamos tu lógica modular
from knowledge_base import get_fixed_response
from ai_clients import call_openai, call_gemini

# CARGAMOS LAS VARIABLES DE ENTORNO
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN') # Asegúrate de que así se llame en tu .env

# 🛡️ SEGURIDAD NIVEL 1: Lista Blanca
ALLOWED_USERS_STR = os.getenv('TELEGRAM_ALLOWED_USERS', '')
ALLOWED_USERS = [int(uid.strip()) for uid in ALLOWED_USERS_STR.split(',') if uid.strip().isdigit()]

# 🛡️ SEGURIDAD NIVEL 2: Contraseña y Sesiones
BOT_PASSWORD = os.getenv('TELEGRAM_BOT_PASSWORD', 'ProtocoloRevenge2026')
usuarios_autenticados = set() 

if not TOKEN:
    print("⚠️ Advertencia: TELEGRAM_TOKEN no encontrado. El bot no se iniciará.")
    bot = None
else:
    bot = telebot.TeleBot(TOKEN)

# --- 🧠 NUEVO PROMPT UNIFICADO PARA NEXO IA ---
SYSTEM_PROMPT_BASE = (
    "Eres 'NEXO IA', el núcleo analítico de CloudLabs en Telegram. "
    "Tu especialidad es conectar métricas web con estrategias de marketing. "
    "Regla: Usa los datos de Supabase que se te proporcionan para justificar tus respuestas. "
    "Si te preguntan algo ajeno a CloudLabs o Marketing, responde amablemente que tu "
    "programación se limita a la inteligencia de datos de la plataforma. "
    "Usa formato Markdown (negritas **, listas -) para estructurar tu respuesta."
)

# --- ☁️ FUNCIÓN ESPEJO PARA SUPABASE ---
def obtener_contexto_cloud():
    """Consulta las tablas de Supabase para darle contexto al Bot"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key: return ""
    
    try:
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        # Traemos un resumen rápido para no saturar el chat de Telegram
        resp_mkt = requests.get(f"{url}/rest/v1/metricas_marketing?select=*&limit=5", headers=headers)
        resp_grab = requests.get(f"{url}/rest/v1/grabaciones_analisis?select=*&limit=5", headers=headers)
        
        contexto = "\n\n[DATOS EN TIEMPO REAL SUPABASE]:\n"
        
        if resp_mkt.status_code == 200:
            contexto += "\n📌 DATOS MARKETING:\n"
            for f in resp_mkt.json():
                contexto += f"- URL: {f.get('Url')} | Métrica: {f.get('metricName')} | Afecta: {f.get('sessionsWithMetricPercentage')}%\n"
        
        if resp_grab.status_code == 200:
            contexto += "\n📌 DATOS COMPORTAMIENTO:\n"
            for g in resp_grab.json():
                fecha = g.get('fecha', 'N/A')
                pais = g.get('pais', 'N/A')
                eng = g.get('standarized_engagement_score', 'N/A')
                contexto += f"- Fecha: {fecha} | País: {pais} | Engagement: {eng}\n"
        
        return contexto
    except Exception as e:
        print(f"Error consultando Supabase para Telegram: {e}")
        return ""

if bot:
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(message, "⚡️ NEXO IA Iniciado. Sistema de seguridad activo. Por favor, ingresa tu clave de acceso.")

    @bot.message_handler(func=lambda message: True)
    def responder_mensaje(message):
        user_id = message.from_user.id
        texto_usuario = message.text.strip() if message.text else ""
        
        # 🛑 ESCUDO 1: Lista blanca (si está configurada en .env)
        if ALLOWED_USERS and user_id not in ALLOWED_USERS:
            print(f"🚨 Bloqueado usuario no autorizado: {user_id}")
            return 

        # 🛑 ESCUDO 2: Autenticación
        if user_id not in usuarios_autenticados:
            if texto_usuario == BOT_PASSWORD:
                usuarios_autenticados.add(user_id)
                bot.reply_to(message, "🔓 ¡Acceso concedido! Soy NEXO IA. Sistemas de datos vinculados. ¿Qué analizamos?")
                return
            else:
                bot.reply_to(message, "🔒 Acceso restringido. Ingresa la clave de seguridad.")
                return

        # 🛑 ESCUDO 3: Longitud
        if len(texto_usuario) > 500:
            bot.reply_to(message, "⛔ Mensaje muy largo. Por favor, sé más breve.")
            return
            
        bot.send_chat_action(message.chat.id, 'typing')
        
        # 1. Conocimiento Fijo (opcional, actívalo o desactívalo a gusto)
        fixed = get_fixed_response(texto_usuario)
        if fixed:
            bot.reply_to(message, f"💡 {fixed}")
            return

        # 2. Carrera de IAs con Contexto de Datos
        contexto_actual = obtener_contexto_cloud()
        
        # 👈 NUEVO: Le inyectamos la fecha actual
        fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prompt_dinamico = f"INFO DE SISTEMA: La fecha y hora actual es {fecha_hoy}.\n\n" + SYSTEM_PROMPT_BASE + contexto_actual
        
        timeout_race = float(os.getenv('RACE_TIMEOUT', '25'))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(call_openai, texto_usuario, prompt_dinamico): 'OpenAI',
                executor.submit(call_gemini, texto_usuario, prompt_dinamico): 'Gemini'
            }
            
            try:
                for future in concurrent.futures.as_completed(futures, timeout=timeout_race):
                    provider = futures[future]
                    try:
                        respuesta = future.result()
                        if respuesta and not str(respuesta).startswith("Error"):
                            
                            # Limpieza rápida por si la IA devuelve Markdown inválido
                            respuesta = respuesta.replace("```markdown", "").replace("```", "")
                            
                            mensaje_final = f"{respuesta}\n\n🤖 *Motor:* {provider}"
                            
                            # Usamos try/except al enviar el mensaje por si el Markdown se rompe
                            try:
                                bot.reply_to(message, mensaje_final, parse_mode='Markdown')
                            except telebot.apihelper.ApiTelegramException:
                                # Si falla el Markdown, enviamos como texto plano
                                bot.reply_to(message, f"{respuesta}\n\n🤖 Motor: {provider}")
                            return
                    except Exception as e:
                        print(f"❌ Error interno en {provider}: {str(e)}")
                
                bot.reply_to(message, "❌ Los motores de Nexo IA están saturados. Intenta en un momento.")

            except concurrent.futures.TimeoutError:
                bot.reply_to(message, "⏳ La consulta tardó demasiado. Reintenta.")

def iniciar_bot_telegram():
    """Llamado desde app.py"""
    if bot:
        import logging
        telebot.logger.setLevel(logging.CRITICAL) 
        print("-----------------------------------------")
        print("📱 NEXO IA: Agente de Telegram Activo...")
        print("-----------------------------------------")
        try:
            bot.infinity_polling(timeout=90, long_polling_timeout=90)
        except Exception as e:
            print(f"❌ Error crítico en Telegram: {e}")

if __name__ == '__main__':
    iniciar_bot_telegram()
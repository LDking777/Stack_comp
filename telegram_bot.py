import os
import time
import telebot
import concurrent.futures
from dotenv import load_dotenv

# Importamos tu lógica
from knowledge_base import get_fixed_response
from ai_clients import call_openai, call_gemini

# CARGAMOS LAS VARIABLES DE ENTORNO
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

# 🛡️ SEGURIDAD NIVEL 1: Lista Blanca
ALLOWED_USERS_STR = os.getenv('TELEGRAM_ALLOWED_USERS', '')
ALLOWED_USERS = [int(uid.strip()) for uid in ALLOWED_USERS_STR.split(',') if uid.strip().isdigit()]

# 🛡️ SEGURIDAD NIVEL 2: Contraseña y Sesiones
BOT_PASSWORD = os.getenv('TELEGRAM_BOT_PASSWORD', 'ProtocoloRevenge2026')
usuarios_autenticados = set() # Aquí anotamos a los que ya pusieron la clave

if not TOKEN:
    print("⚠️ Advertencia: TELEGRAM_TOKEN no encontrado. El bot no se iniciará.")
    bot = None
else:
    bot = telebot.TeleBot(TOKEN)

SYSTEM_PROMPT = (
    "Eres el Asistente Inteligente oficial de la plataforma 'REVENGE'.\n"
    "CONTEXTO: Nuestra plataforma utiliza múltiples IAs para optimizar procesos tecnológicos.\n"
    "REGLA DE SEGURIDAD: Si te preguntan sobre temas ajenos (deportes, política), responde: "
    "'Lo siento, mi programación solo me permite ayudarte con temas de REVENGE.'"
)

if bot:
    @bot.message_handler(func=lambda message: True)
    def responder_mensaje(message):
        user_id = message.from_user.id
        texto_usuario = message.text.strip() if message.text else ""
        
        # 🛑 ESCUDO 1: ¿Está en la lista blanca?
        if user_id not in ALLOWED_USERS:
            print(f"🚨 ALERTA: Intento de acceso bloqueado. ID: {user_id}")
            return 

        # 🛑 ESCUDO 2: ¿Ya puso la contraseña?
        if user_id not in usuarios_autenticados:
            if texto_usuario == BOT_PASSWORD:
                usuarios_autenticados.add(user_id)
                bot.reply_to(message, "🔓 ¡Acceso concedido, Jefe! Sistemas de IA en línea. ¿En qué te ayudo?")
                print(f"✅ Usuario {user_id} se ha autenticado con éxito.")
                return
            else:
                bot.reply_to(message, "🔒 Bot asegurado. Por favor, ingresa la palabra clave para iniciar sesión.")
                print(f"⚠️ Usuario {user_id} intentó hablar sin contraseña.")
                return

        # 🛑 ESCUDO 3: Límite de caracteres (Anti-Saturación de IA)
        MAX_CHARS = 500
        if len(texto_usuario) > MAX_CHARS:
            bot.reply_to(message, f"⛔ Mensaje demasiado largo ({len(texto_usuario)}/{MAX_CHARS}). Resúmelo por favor.")
            return
            
        if len(texto_usuario) == 0:
            return

        # --- A PARTIR DE AQUÍ EL BOT RESPONDE NORMAL CON LAS IAs ---
        bot.send_chat_action(message.chat.id, 'typing')
        
        # 1. Capa de Conocimiento Fijo
        fixed = get_fixed_response(texto_usuario)
        if fixed:
            bot.reply_to(message, f"💡 {fixed}")
            return

        # 2. Carrera de IAs
        timeout_race = float(os.getenv('RACE_TIMEOUT', '30'))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(call_openai, texto_usuario, SYSTEM_PROMPT): 'OpenAI',
                executor.submit(call_gemini, texto_usuario, SYSTEM_PROMPT): 'Gemini'
            }
            
            try:
                for future in concurrent.futures.as_completed(futures, timeout=timeout_race):
                    provider = futures[future]
                    try:
                        respuesta = future.result()
                        if respuesta and not respuesta.startswith("Error"):
                            mensaje_final = f"{respuesta}\n\n⚡ _Respondido por {provider}_"
                            bot.reply_to(message, mensaje_final, parse_mode='Markdown')
                            return
                    except Exception as e:
                        print(f"❌ Error en {provider}: {str(e)}")
                
                bot.reply_to(message, "❌ Hubo un problema con los motores de IA.")

            except concurrent.futures.TimeoutError:
                bot.reply_to(message, "⏳ Tiempo de espera agotado.")

# --- LA MAGIA MODULAR (Que se nos había borrado) ---
def iniciar_bot_telegram():
    """Función que será llamada desde app.py para correr en segundo plano"""
    if bot:
        import logging
        telebot.logger.setLevel(logging.CRITICAL) 
        print("-----------------------------------------")
        print("📱 Agente de Telegram REVENGE en línea (Segundo Plano)...")
        print("-----------------------------------------")
        try:
            bot.infinity_polling(timeout=90, long_polling_timeout=90)
        except Exception as e:
            print(f"❌ Error crítico en el bot de Telegram: {e}")

# Esto permite que sigas probando el bot solo si ejecutas "python telegram_bot.py"
if __name__ == '__main__':
    iniciar_bot_telegram()
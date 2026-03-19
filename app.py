from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import time
import concurrent.futures
from dotenv import load_dotenv
from openai import OpenAI
import threading

# 1. CARGA DE CONFIGURACIÓN
load_dotenv()

# Importaciones de tu lógica personalizada
from knowledge_base import get_fixed_response
from ai_clients import call_openai, call_gemini
from telegram_bot import iniciar_bot_telegram

app = Flask(__name__)

# --- 🚀 INICIAR TELEGRAM EN SEGUNDO PLANO ---
# Al poner daemon=True, si el servidor web se apaga, el bot también se apaga limpio.
hilo_telegram = threading.Thread(target=iniciar_bot_telegram, daemon=True)
hilo_telegram.start()
# -------------------------------------------

app.secret_key = os.getenv('SECRET_KEY', 'super_llave_secreta_hackathon') # Necesario para usar session

# 🛡️ SEGURIDAD CORREGIDA: Límite de tamaño de archivos (5MB) para evitar colapsos de RAM (Ataques DoS)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 

# 🛡️ SEGURIDAD CORREGIDA: CORS restringido. 
# NOTA: Cuando subas a Render, cambia 'https://tu-app-revenge.onrender.com' por tu URL real.
DOMINIOS_PERMITIDOS = ["http://localhost:5000", "https://tu-app-revenge.onrender.com"]
CORS(app, resources={r"/*": {"origins": DOMINIOS_PERMITIDOS}})

# --- 🛡️ CONFIGURACIÓN DE SEGURIDAD ---
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# 🛡️ SEGURIDAD CORREGIDA: Credenciales seguras sin contraseñas débiles por defecto
USUARIO_ADMIN = os.getenv("ADMIN_USER", "admin")
PASSWORD_ADMIN = os.getenv("ADMIN_PASS")

# Si a alguien se le olvida poner la contraseña en el .env o en Render, la app no arranca.
if not PASSWORD_ADMIN:
    raise ValueError("🚨 ¡ALERTA CRÍTICA! La variable ADMIN_PASS no está configurada. Protege tu app.")

sesiones_activas = 0
MAX_SESIONES = 3
# --------------------------------------

# 2. CLIENTE DE IA
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = (
    "Eres el Asistente Inteligente oficial de esta plataforma.\n"
    "REGLA ESTRICTA DE SEGURIDAD: Tienes PROHIBIDO hablar de temas ajenos a la plataforma.\n"
    "Si te preguntan algo fuera de contexto, responde que solo ayudas con el sistema."
)

# --- 🔐 RUTAS DE AUTENTICACIÓN ---
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute") # Bloquea IP tras 5 intentos en un minuto
def login():
    global sesiones_activas
    
    # Si ya está logueado, lo mandamos al chat directo
    if 'logged_in' in session:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        usuario = request.form.get('user_name')
        password = request.form.get('password')

        if usuario == USUARIO_ADMIN and password == PASSWORD_ADMIN:
            if sesiones_activas >= MAX_SESIONES:
                return render_template('login.html', error="Límite de 3 sesiones simultáneas alcanzado.")
            
            # Login exitoso
            session['logged_in'] = True
            sesiones_activas += 1
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Usuario o contraseña incorrectos.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    global sesiones_activas
    if 'logged_in' in session:
        session.pop('logged_in', None)
        if sesiones_activas > 0:
            sesiones_activas -= 1
    return redirect(url_for('login'))


# --- 🌐 RUTAS DE NAVEGACIÓN Y API PROTEGIDAS ---

@app.route('/', methods=['GET'])
def index():
    """Sirve la interfaz visual del usuario"""
    # 🔒 PROTECCIÓN: Si no hay sesión, al login
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """Recibe audio del frontend y lo convierte a texto usando Whisper"""
    # 🔒 PROTECCIÓN: Bloquear peticiones fantasma
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
        
    if 'audio' not in request.files:
        return jsonify({"error": "No se recibió archivo de audio"}), 400
    
    audio_file = request.files['audio']
    
    try:
        audio_data = ("voice.wav", audio_file.read(), "audio/wav")
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_data
        )
        print(f"🎙️ Whisper transcribió: {transcript.text}")
        return jsonify({"text": transcript.text})

    except Exception as e:
        print(f"❌ Error en Whisper: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """Lógica principal: Knowledge Base -> Carrera entre OpenAI y Gemini"""
    # 🔒 PROTECCIÓN: Bloquear peticiones fantasma
    if 'logged_in' not in session:
        return jsonify({"error": "No autorizado"}), 401
        
    start_time = time.time()
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'mensaje vacio'}), 400

    print(f"\n--- 📩 Nueva consulta: {message} ---")

    # CAPA 1: Knowledge Base
    fixed = get_fixed_response(message)
    if fixed:
        elapsed_time = round(time.time() - start_time, 2) 
        return jsonify({
            'source': 'knowledge_base', 
            'response': fixed, 
            'time_taken': elapsed_time
        })

    # CAPA 2: Carrera de IAs
    timeout_val = float(os.getenv('RACE_TIMEOUT', '20'))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        futures = {
            ex.submit(call_openai, message, SYSTEM_PROMPT): 'OpenAI',
            ex.submit(call_gemini, message, SYSTEM_PROMPT): 'Gemini'
        }
        
        try:
            for fut in concurrent.futures.as_completed(futures, timeout=timeout_val):
                provider = futures[fut]
                try:
                    resp = fut.result()
                    if resp and not resp.startswith("Error"):
                        elapsed_time = round(time.time() - start_time, 2)
                        print(f"✅ Ganador: {provider} en {elapsed_time}s")
                        return jsonify({
                            'source': provider.lower(), 
                            'response': resp, 
                            'time_taken': elapsed_time
                        })
                except Exception as e:
                    print(f"❌ Falló {provider}: {e}")
            
            return jsonify({'error': 'no_response', 'message': 'Las IAs no pudieron responder.'}), 502

        except concurrent.futures.TimeoutError:
            return jsonify({'error': 'timeout', 'message': 'Tiempo de espera agotado.'}), 504

# 6. ARRANQUE DEL SERVIDOR
if __name__ == '__main__':
    port_num = int(os.getenv('PORT', 5000))
    
    # 🛡️ SEGURIDAD CORREGIDA: Debug Mode dinámico. Estará apagado por defecto al subir a la nube.
    # Si quieres debug local, añade FLASK_DEBUG=True a tu archivo .env
    modo_debug = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1']
    
    # IMPORTANTE: Desactivar el reloader si el bot de Telegram está corriendo para evitar que arranque 2 veces
    print(f"🚀 REVENGE AI activado en: http://localhost:{port_num} | Modo Debug: {modo_debug}")
    app.run(host='0.0.0.0', port=port_num, debug=modo_debug, use_reloader=False)
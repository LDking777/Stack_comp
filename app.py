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
import requests

# 1. CARGA DE CONFIGURACIÓN
load_dotenv()

from knowledge_base import get_fixed_response
from ai_clients import call_openai, call_gemini
from telegram_bot import iniciar_bot_telegram

app = Flask(__name__)

# --- 🚀 INICIAR TELEGRAM ---
hilo_telegram = threading.Thread(target=iniciar_bot_telegram, daemon=True)
hilo_telegram.start()

app.secret_key = os.getenv('SECRET_KEY', 'super_llave_secreta_hackathon')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 

DOMINIOS_PERMITIDOS = ["http://localhost:5000", "https://tu-app-revenge.onrender.com"]
CORS(app, resources={r"/*": {"origins": DOMINIOS_PERMITIDOS}})

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

USUARIO_ADMIN = os.getenv("ADMIN_USER", "admin")
PASSWORD_ADMIN = os.getenv("ADMIN_PASS")

if not PASSWORD_ADMIN:
    raise ValueError("🚨 ADMIN_PASS no configurada.")

sesiones_activas = 0
MAX_SESIONES = 3

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- 🧠 PROMPT DE NEXO IA (ACTUALIZADO PARA MULTITABLA) ---
SYSTEM_PROMPT = (
    "Eres 'NEXO IA', el núcleo de inteligencia analítica de CloudLabs. "
    "Tu especialidad es conectar datos de métricas web con estrategias de marketing. "
    "Tienes acceso a dos fuentes de datos en tiempo real de Supabase:\n"
    "1. 'metricas_marketing': Enfocada en eventos como Dead Clicks y Rage Clicks por URL.\n"
    "2. 'grabaciones_analisis': Enfocada en comportamiento de usuario, países, engagement score y frustración.\n\n"
    "REGLAS:\n"
    "1. Cruza los datos de ambas tablas para dar insights profundos.\n"
    "2. Si un país tiene bajo engagement y alta frustración, destaca ese problema.\n"
    "3. Tu tono es profesional, ejecutivo y basado 100% en evidencia."
)

# --- ☁️ CONEXIÓN A SUPABASE (MULTITABLA) ---
def consultar_datos_cloud():
    """Consulta ambas tablas en Supabase y genera un contexto unificado"""
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Aviso: Credenciales de Supabase no encontradas.")
        return ""
        
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        
        # Consulta 1: Métricas de Marketing
        resp_mkt = requests.get(f"{SUPABASE_URL}/rest/v1/metricas_marketing?select=*&limit=15", headers=headers)
        # Consulta 2: Grabaciones y Comportamiento
        resp_grab = requests.get(f"{SUPABASE_URL}/rest/v1/grabaciones_analisis?select=*&limit=15", headers=headers)
        
        contexto = "\n\n--- [BASE DE CONOCIMIENTO EN VIVO: NEXO IA] ---\n"

        if resp_mkt.status_code == 200:
            datos_mkt = resp_mkt.json()
            contexto += "\n📌 DATOS DE MARKETING Y FRUSTRACIÓN:\n"
            for f in datos_mkt:
                contexto += f"- URL: {f.get('Url')} | {f.get('metricName')}: {f.get('sessionsWithMetricPercentage')}% | Total: {f.get('subTotal')}\n"

        if resp_grab.status_code == 200:
            datos_grab = resp_grab.json()
            contexto += "\n📌 DATOS DE COMPORTAMIENTO POR SESIÓN:\n"
            for g in datos_grab:
                frustracion = "Alta" if g.get('posible_frustracion') == 1 else "Baja"
                contexto += f"- Origen: {g.get('pais')} | URL Entrada: {g.get('direccion_url_entrada')} | Engagement: {g.get('standarized_engagement_score')} | Frustración: {frustracion}\n"
        
        contexto += "\n--- FIN DEL REPORTE ---\n"
        return contexto

    except Exception as e:
        print(f"⚠️ Error Nexo Data Multi-table: {e}")
        return ""

# --- RUTAS ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    global sesiones_activas
    if 'logged_in' in session: return redirect(url_for('index'))
    if request.method == 'POST':
        if request.form.get('user_name') == USUARIO_ADMIN and request.form.get('password') == PASSWORD_ADMIN:
            if sesiones_activas >= MAX_SESIONES: return render_template('login.html', error="Límite alcanzado.")
            session['logged_in'] = True
            sesiones_activas += 1
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    global sesiones_activas
    if 'logged_in' in session:
        session.pop('logged_in', None)
        if sesiones_activas > 0: sesiones_activas -= 1
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
def index():
    if 'logged_in' not in session: return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    audio_file = request.files.get('audio')
    if not audio_file: return jsonify({"error": "No audio"}), 400
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=("voice.wav", audio_file.read(), "audio/wav")
        )
        return jsonify({"text": transcript.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    start_time = time.time()
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    
    if not message: return jsonify({'error': 'vacio'}), 400

    fixed = get_fixed_response(message)
    if fixed:
        return jsonify({'source': 'kb', 'response': fixed, 'time_taken': round(time.time()-start_time, 2)})

    # NEXO IA obtiene datos cruzados de ambas tablas
    datos_cloud = consultar_datos_cloud()
    PROMPT_DINAMICO = SYSTEM_PROMPT + datos_cloud

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        futures = {
            ex.submit(call_openai, message, PROMPT_DINAMICO): 'OpenAI',
            ex.submit(call_gemini, message, PROMPT_DINAMICO): 'Gemini'
        }
        try:
            for fut in concurrent.futures.as_completed(futures, timeout=20):
                resp = fut.result()
                if resp and not resp.startswith("Error"):
                    return jsonify({
                        'source': futures[fut].lower(), 
                        'response': resp, 
                        'time_taken': round(time.time() - start_time, 2)
                    })
        except Exception as e:
            print(f"Error en el motor de IA: {e}")
            return jsonify({'error': 'error'}), 502

if __name__ == '__main__':
    port_num = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port_num, debug=False, use_reloader=False)
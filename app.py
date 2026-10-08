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
from datetime import datetime # 🕒 Corregido: Importación de hora añadida

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

# --- 🧠 PROMPT DE NEXO IA ---
SYSTEM_PROMPT = (
    "Eres 'NEXO IA', el núcleo de inteligencia analítica de CloudLabs. "
    "Tu especialidad es conectar datos de métricas web con estrategias de marketing. "
    "Tienes acceso a dos fuentes de datos en tiempo real de Supabase:\n"
    "1. 'metricas_marketing': Enfocada en eventos como Dead Clicks y Rage Clicks por URL.\n"
    "2. 'grabaciones_analisis': Enfocada en comportamiento de usuario, países, páginas vistas y tiempos.\n\n"
    "REGLAS:\n"
    "1. Cruza los datos de ambas tablas para dar insights profundos.\n"
    "2. Si un país tiene bajo engagement y alta frustración, destaca ese problema.\n"
    "3. Si el usuario pide un cálculo (promedios, sumas), usa los datos numéricos exactos del reporte para hacerlo.\n"
    "4. Tu tono es profesional, ejecutivo y basado 100% en evidencia."
)

# --- CACHÉ SIMPLE PARA SUPABASE ---
CACHE_CONTEXTO = ""
ULTIMA_ACTUALIZACION = 0
TIEMPO_CACHE = 120 # Segundos (2 minutos)

# --- ☁️ CONEXIÓN A SUPABASE OPTIMIZADA ---
def consultar_datos_cloud():
    global CACHE_CONTEXTO, ULTIMA_ACTUALIZACION
    
    # Retornar caché si aún es válido
    if time.time() - ULTIMA_ACTUALIZACION < TIEMPO_CACHE and CACHE_CONTEXTO:
        return CACHE_CONTEXTO

    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️ Aviso: Credenciales de Supabase no encontradas.")
        return ""
        
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Consultas (Limitamos a 15 para no saturar)
        resp_mkt = requests.get(f"{SUPABASE_URL}/rest/v1/metricas_marketing?select=*&limit=15", headers=headers)
        resp_grab = requests.get(f"{SUPABASE_URL}/rest/v1/grabaciones_analisis?select=*&limit=15", headers=headers)
        
        contexto = "\n\n--- [BASE DE CONOCIMIENTO EN VIVO: NEXO IA] ---\n"

        # 1. MANEJO DE TABLA: METRICAS MARKETING
        if resp_mkt.status_code == 200:
            datos_mkt = resp_mkt.json()
            contexto += "\n📌 DATOS DE MARKETING Y EVENTOS (DeadClicks, RageClicks):\n"
            for f in datos_mkt:
                url = f.get('Url', 'Sin URL')
                metrica = f.get('metricName', 'Desconocida')
                porcentaje = f.get('sessionsWithMetricPercentage', 0.0)
                sesiones = f.get('sessionsCount', 0.0)
                dispositivo = f.get('Device', 'N/A')
                sistema_op = f.get('OS', 'N/A')
                
                contexto += f"- Métrica: {metrica} | Afecta al {porcentaje}% | URL: {url} | Dispositivo: {dispositivo} ({sistema_op}) | Sesiones Totales: {sesiones}\n"
        else:
            print(f"❌ Error Supabase (metricas): {resp_mkt.status_code} - {resp_mkt.text}")

        # 2. MANEJO DE TABLA: GRABACIONES ANALISIS (Con páginas vistas y duración agregadas)
        if resp_grab.status_code == 200:
            datos_grab = resp_grab.json()
            contexto += "\n📌 DATOS DE COMPORTAMIENTO POR SESIÓN:\n"
            for g in datos_grab:
                fecha = g.get('fecha', 'Sin fecha')
                hora = g.get('hora', 'Sin hora')
                pais = g.get('pais', 'Desconocido')
                dispositivo = g.get('dispositivo', 'N/A')
                url_entrada = g.get('direccion_url_entrada', 'N/A')
                engagement = g.get('standarized_engagement_score', 'N/A')
                
                # Campos para hacer cálculos matemáticos
                paginas = g.get('recuento_paginas', 0)
                duracion = g.get('duracion_sesion_segundos', 0)
                
                frust = g.get('posible_frustracion')
                frustracion = "Alta" if str(frust) == '1' else "Baja"
                
                contexto += f"- Fecha: {fecha} a las {hora} | País: {pais} ({dispositivo}) | Entrada: {url_entrada} | Páginas Vistas: {paginas} | Duración: {duracion}s | Engagement: {engagement} | Frustración: {frustracion}\n"
        else:
            print(f"❌ Error Supabase (grabaciones): {resp_grab.status_code} - {resp_grab.text}")
        
        contexto += "\n--- FIN DEL REPORTE ---\n"
        
        # Guardar en caché
        CACHE_CONTEXTO = contexto
        ULTIMA_ACTUALIZACION = time.time()
        
        return contexto

    except Exception as e:
        print(f"⚠️ Error crítico en Nexo Data: {e}")
        return ""

# --- RUTAS ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    global sesiones_activas
    if 'logged_in' in session: return redirect(url_for('index'))
    if request.method == 'POST':
        if request.form.get('user_name') == USUARIO_ADMIN and request.form.get('password') == PASSWORD_ADMIN:
            if sesiones_activas >= MAX_SESIONES: return render_template('login.html', error="Límite de sesiones activas alcanzado.")
            session['logged_in'] = True
            sesiones_activas += 1
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Credenciales incorrectas.")
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
    
    if 'audio' not in request.files: return jsonify({"error": "No se envió archivo de audio"}), 400
    audio_file = request.files['audio']
    
    if audio_file.filename == '': return jsonify({"error": "Archivo vacío"}), 400
    
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=("voice.wav", audio_file.read(), "audio/wav")
        )
        return jsonify({"text": transcript.text})
    except Exception as e:
        print(f"Error en transcripción: {e}")
        return jsonify({"error": "Fallo al procesar el audio"}), 500

@app.route('/chat', methods=['POST'])
def chat():
    if 'logged_in' not in session: return jsonify({"error": "No autorizado"}), 401
    
    start_time = time.time()
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    
    if not message: return jsonify({'error': 'Mensaje vacío'}), 400

    # 1. Prioridad: Knowledge Base (Respuestas fijas)
    fixed = get_fixed_response(message)
    if fixed:
        return jsonify({'source': 'kb', 'response': fixed, 'time_taken': round(time.time()-start_time, 2)})

    # 2. IA con Contexto de Datos y Hora Actual
    datos_cloud = consultar_datos_cloud()
    
    # 🕒 Inyección de fecha y hora actual para el motor de IA
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    PROMPT_DINAMICO = f"INFO DE SISTEMA: La fecha y hora actual es {fecha_actual}.\n\n" + SYSTEM_PROMPT + datos_cloud

    # Motor de IA unificado (Sin carrera de IAs)
    resp = call_openai(message, PROMPT_DINAMICO)
    if resp and not str(resp).startswith("Error"):
        return jsonify({
            'source': 'openai', 
            'response': resp, 
            'time_taken': round(time.time() - start_time, 2)
        })
            
    return jsonify({'error': 'El modelo de IA falló al procesar la solicitud.'}), 502

if __name__ == '__main__':
    port_num = int(os.getenv('PORT', 5000))
    # use_reloader=False para evitar que el bot de Telegram se ejecute dos veces
    app.run(host='0.0.0.0', port=port_num, debug=True, use_reloader=False)
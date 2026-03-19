import os
import json
import requests
from openai import OpenAI

def call_openai(message, system_prompt):
    """Llamada a OpenAI usando la librería oficial"""
    try:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key: 
            return None
        
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            timeout=8
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Error OpenAI: {e}")
        return None

def call_gemini(message, system_prompt):
    """Llamada a Gemini usando REST (Método Oficial por Headers)"""
    try:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key: 
            return None

        # 1. URL LIMPIA: Ya no le pegamos el "?key=" al final
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        
        # 2. HEADERS: Aquí es donde metemos la llave, tal como dice la documentación
        headers = {
            'Content-Type': 'application/json',
            'x-goog-api-key': api_key  # ¡El gran secreto estaba aquí!
        }
        
        # 3. PAYLOAD: La estructura de la pregunta
        payload = {
            "contents": [{
                "parts": [{"text": f"{system_prompt}\n\nPregunta: {message}"}]
            }]
        }

        # 4. LA LLAMADA
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        res_json = response.json()

        if "candidates" in res_json:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"⚠️ Gemini REST respondió con error: {res_json}")
            return None
            
    except Exception as e:
        print(f"❌ Fallo crítico REST Gemini: {e}")
        return None
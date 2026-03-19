import requests
import os
from dotenv import load_dotenv

# Cargar tu llave de la variable de entorno
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("🔍 Preguntándole a Google qué modelos están disponibles...")

# Hacemos una petición GET a la ruta de modelos
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print("✅ ¡Conexión exitosa! Estos son los modelos que puedes usar:")
    for model in data.get("models", []):
        # Filtramos para que solo nos muestre los de generación de texto
        if "generateContent" in model.get("supportedGenerationMethods", []):
            print(f" 🔹 {model['name'].replace('models/', '')}")
else:
    print(f"❌ Error al consultar: {response.json()}")
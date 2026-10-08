import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL o SUPABASE_KEY no están configuradas en el archivo .env")
    exit(1)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def verificar_conexion():
    print(f"📡 Verificando conexión con Supabase en: {SUPABASE_URL}")
    test_url = f"{SUPABASE_URL}/rest/v1/"
    try:
        r = requests.get(test_url, headers=headers, timeout=10)
        if r.status_code in [200, 404]:
            print("✅ Conexión con Supabase REST exitosa.")
            return True
        else:
            print(f"⚠️ Respuesta inesperada: {r.status_code} - {r.text}")
            return False
    except Exception as e:
        print(f"❌ Error al conectar: {e}")
        return False

def test_tablas():
    for tabla in ["metricas_marketing", "grabaciones_analisis"]:
        url = f"{SUPABASE_URL}/rest/v1/{tabla}?select=*&limit=1"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                print(f"✅ Tabla '{tabla}' existe y es accesible (filas leídas: {len(r.json())}).")
            else:
                print(f"⚠️ Tabla '{tabla}' respondió: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"❌ Error consultando '{tabla}': {e}")

if __name__ == "__main__":
    if verificar_conexion():
        print("\nComprobando estado de las tablas:")
        test_tablas()

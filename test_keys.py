import os
from dotenv import load_dotenv
from ai_clients import call_openai, call_gemini

load_dotenv()

def test():
    print("--- 🧪 Probando Conexiones ---")
    
    # Probar OpenAI
    try:
        print("Probando OpenAI...")
        res = call_openai("Hola", "Eres un asistente")
        print(f"✅ OpenAI OK: {res[:30]}...")
    except Exception as e:
        print(f"❌ OpenAI Falló: {e}")

    # Probar Gemini
    try:
        print("\nProbando Gemini...")
        res = call_gemini("Hola", "Eres un asistente")
        print(f"✅ Gemini OK: {res[:30]}...")
    except Exception as e:
        print(f"❌ Gemini Falló: {e}")

if __name__ == "__main__":
    test()
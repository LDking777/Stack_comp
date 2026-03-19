# Backend CaldasTour (minimal)

Instrucciones rápidas para levantar el backend localmente.

1) Crear y activar entorno virtual

Windows (PowerShell):

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows (cmd.exe):

```
python -m venv .venv
.\.venv\Scripts\activate.bat
```

Linux / macOS:

```
python3 -m venv .venv
source .venv/bin/activate
```

2) Instalar dependencias

```
pip install -r requirements.txt
```

3) Configurar claves en `.env` (OPENAI_API_KEY y GEMINI_API_KEY)

4) Ejecutar

```
python app.py
```

El servidor expondrá `/chat` que recibe JSON `{ "message": "..." }` y responde `{ "source": "...", "response": "..." }`.

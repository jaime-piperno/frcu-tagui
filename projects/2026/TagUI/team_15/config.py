import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RUTA_CREDENCIALES = BASE_DIR / "credentials.json"
RUTA_ENV = BASE_DIR / ".env"


def _cargar_env():
    if RUTA_ENV.exists():
        with open(RUTA_ENV, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, _, valor = linea.partition("=")
                os.environ.setdefault(clave.strip(), valor.strip())


_cargar_env()

TOKEN_TELEGRAM = os.environ.get("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
LLM_MODELO = os.environ.get("LLM_MODELO", "gemini-3.6-flash")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODELO = os.environ.get(
    "OPENROUTER_MODELO", "nvidia/nemotron-3-super-120b-a12b:free"
)

GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
URL_DASHBOARD = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
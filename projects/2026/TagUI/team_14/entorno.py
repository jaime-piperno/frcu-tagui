"""
Carga de variables de entorno desde el archivo .env del proyecto.

Con Docker Compose las variables se inyectan en los contenedores y el .env no está dentro de la
imagen, así que esta carga no tiene efecto. En modo local (sin Docker) permite que la API y el bot
lean la misma configuración (API_KEY, BOT_CODIGO_ACCESO, TELEGRAM_TOKEN, etc.).
"""
from __future__ import annotations

import os
from pathlib import Path

RUTA_ENV = Path(__file__).resolve().parent / '.env'


def cargar_env(ruta: Path = RUTA_ENV) -> None:
    """Carga un archivo .env simple (CLAVE=valor) sin pisar variables ya definidas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding='utf-8-sig').splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        clave, valor = linea.split('=', 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))

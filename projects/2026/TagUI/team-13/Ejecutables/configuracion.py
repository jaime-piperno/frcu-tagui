# configuracion.py
# Lee config.txt (en la raíz del proyecto) y devuelve sus valores.
#
# config.txt está en .gitignore porque tiene el token del bot: cada integrante
# del grupo se arma el suyo a partir de config.ejemplo.txt.
#
# Lo usan bot.py y prueba_conexion.py: la lectura está escrita una sola vez,
# acá, y los demás archivos la importan.

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_CONFIG = RAIZ / "config.txt"

CLAVES_OBLIGATORIAS = ["TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID", "GRUPO_TELEGRAM"]


def leer_config(obligatorias=CLAVES_OBLIGATORIAS):
    if not ARCHIVO_CONFIG.exists():
        raise SystemExit(
            "No existe config.txt. Copiá config.ejemplo.txt como config.txt "
            "(en la raíz del proyecto) y completalo."
        )

    config = {}
    for linea in ARCHIVO_CONFIG.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        config[clave.strip()] = valor.strip()

    faltantes = [c for c in obligatorias if not config.get(c)]
    if faltantes:
        raise SystemExit(
            "Faltan valores en config.txt: " + ", ".join(faltantes)
            + ". Mirá config.ejemplo.txt para ver qué va en cada uno."
        )

    return config

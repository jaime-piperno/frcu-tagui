# configuracion.py
# Lee config.txt (en la raíz del proyecto) y devuelve sus valores.
#
# config.txt está en .gitignore porque tiene el token del bot: cada integrante
# del grupo se arma el suyo a partir de config.ejemplo.txt.
#
# Lo usan bot.py y prueba_conexion.py: la lectura está escrita una sola vez,
# acá, y los demás archivos la importan.

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVO_CONFIG = RAIZ / "config.txt"

CLAVES_OBLIGATORIAS = ["TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID", "GRUPO_TELEGRAM"]

FACTURA_SELECTORES_ENVIAR = (
    '//button[contains(@aria-label,"Enviar") or contains(@aria-label,"Send")]',
    '//button[contains(@class,"send-button")]',
    '//button[.//mat-icon[contains(@data-mat-icon-name,"send")]]',
    '//*[@id="xap-skip-link-target"]/div/chat-window/div[2]/input-container/div/input-area-v2/div/fieldset/div/div[4]/div/div[2]/gem-icon-button/button/gem-icon/mat-icon',
    '//*[@id="xap-skip-link-target"]/div/chat-window/div[2]/input-container/div/input-area-v2/div/fieldset/div/div[3]/div/div[2]/gem-icon-button/button',
    '//input-area-v2//gem-icon-button//button[contains(@aria-label,"Send") or contains(@aria-label,"Enviar")]',
    '//input-area-v2//div[contains(@class,"send")]//button',
)

FACTURA_CONFIG_DEFAULTS = {
    "FACTURA_IA_URL": "https://gemini.google.com",
    "FACTURA_SELECTOR_ARCHIVO": "images-files-uploader input[type='file']",
    "FACTURA_SELECTOR_ADJUNTO": '//*[@id="xap-skip-link-target"]/div/chat-window/div[2]/input-container/div/input-area-v2/div/fieldset/div/div[2]/simplified-input-menu/div/span/gem-icon-button/button',
    "FACTURA_SELECTOR_OPCION_SUBIR": '//*[starts-with(@id,"cdk-overlay-")]/mat-card/mat-action-list/div[1]/uploader/div/div/div[1]/images-files-uploader/gem-button/button',
    "FACTURA_SELECTOR_PROMPT": '//input-area-v2//rich-textarea//*[@contenteditable="true"]',
    "FACTURA_SELECTOR_RESPUESTA": "//model-response[last()]",
    "FACTURA_SELECTOR_ENVIAR": "",
    "FACTURA_TIMEOUT_SECONDS": "300",
    "FACTURA_PROMPT_TEMPLATE": (
        "Lee el ticket adjunto. Devuelve solo alimentos, un renglon por alimento, sin titulo "
        "ni comentarios, con el formato exacto Nombre, cantidad, unidad. Unidades: kg, lt, "
        "unidad. Para productos conocidos, usa exactamente el nombre y la unidad indicada: "
        "{ingredientes_conocidos}. Convierte cantidades explicitas a unidad base "
        "(1 docena de huevos = 12 unidades). No cambies unidades ni inventes conversiones; "
        "omite un producto si no puedes expresarlo en su unidad indicada. No incluyas precios."
    ),
}

FACTURA_CONFIG_CAMPOS = {
    "FACTURA_IA_URL": "url",
    "FACTURA_SELECTOR_ARCHIVO": "selector_archivo",
    "FACTURA_SELECTOR_ADJUNTO": "selector_adjunto",
    "FACTURA_SELECTOR_OPCION_SUBIR": "selector_opcion_subir",
    "FACTURA_SELECTOR_PROMPT": "selector_prompt",
    "FACTURA_SELECTOR_RESPUESTA": "selector_respuesta",
    "FACTURA_SELECTOR_ENVIAR": "selector_enviar",
    "FACTURA_TIMEOUT_SECONDS": "tiempo_maximo",
    "FACTURA_PROMPT_TEMPLATE": "prompt_template",
}


# Lee y valida los valores de configuración del bot.
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


def leer_configuracion_factura():
    """Devuelve parámetros de Gemini; los valores locales pueden sobrescribir defaults."""
    config = leer_config(obligatorias=[])
    valores = {
        FACTURA_CONFIG_CAMPOS[clave]: os.environ.get(
            clave, config.get(clave, predeterminado)
        ).strip()
        for clave, predeterminado in FACTURA_CONFIG_DEFAULTS.items()
    }
    selector_configurado = valores.pop("selector_enviar")
    valores["selectores_enviar"] = (
        (selector_configurado,) if selector_configurado else FACTURA_SELECTORES_ENVIAR
    )
    return valores

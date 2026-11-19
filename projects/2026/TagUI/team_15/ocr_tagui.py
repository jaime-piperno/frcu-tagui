import logging
import os
import subprocess
from pathlib import Path

import config

logger = logging.getLogger(__name__)

TAGUI_DIR = config.BASE_DIR / "tagui"
RUTA_IMAGEN_ACTUAL = TAGUI_DIR / "ticket_actual.png"
RUTA_RESULTADO_OCR = TAGUI_DIR / "ocr_resultado.txt"
RUTA_ERROR_OCR = TAGUI_DIR / "ocr_error.txt"
RUTA_LOG_SIKULI = TAGUI_DIR / "ocr_sikuli.log"
RUTA_SCRIPT_TAG = TAGUI_DIR / "ocr_ticket.tag"
RUTA_SIKULI_DIR = TAGUI_DIR / "ocr_ticket.sikuli"
RUTA_SIKULI_PY = RUTA_SIKULI_DIR / "ocr_ticket.py"

RUTA_TAGUI = config.RUTA_TAGUI
RUTA_SIKULIX_JAR = RUTA_TAGUI / "sikulix" / "sikulix.jar"
RUTA_JYTHON_JAR = RUTA_TAGUI / "sikulix" / "jython-standalone-2.7.1.jar"


def _generar_scripts_ocr(ruta_imagen: Path, ruta_salida: Path, ruta_error: Path) -> None:
    """Genera tanto el script .tag de TagUI como el paquete .sikuli que ejecuta SikuliX."""
    img_posix = ruta_imagen.resolve().as_posix()
    out_posix = ruta_salida.resolve().as_posix()
    err_posix = ruta_error.resolve().as_posix()

    codigo_jython = (
        "# -*- coding: utf-8 -*-\n"
        "from sikuli import *\n"
        "import codecs\n"
        "import java.io.File\n"
        "import java.lang.Throwable\n"
        "import javax.imageio.ImageIO\n\n"
        "Settings.OcrTextRead = True\n"
        "Settings.OcrTextSearch = True\n\n"
        'texto_limpio = u""\n'
        "errores = []\n"
        f'ruta_img = "{img_posix}"\n'
        "try:\n"
        "    img_file = java.io.File(ruta_img)\n"
        "    bimg = javax.imageio.ImageIO.read(img_file)\n"
        "    if bimg is None:\n"
        '        errores.append("ImageIO.read devolvio None para la imagen")\n'
        "    else:\n"
        "        texto_ocr = None\n"
        "        try:\n"
        "            from org.sikuli.script import Image\n"
        "            img_obj = Image.create(ruta_img)\n"
        "            if img_obj is not None:\n"
        "                texto_ocr = img_obj.text()\n"
        "        except java.lang.Throwable, e1:\n"
        '            errores.append("Image.text: " + str(e1))\n'
        "        except Exception, e1:\n"
        '            errores.append("Image.text: " + str(e1))\n\n'
        "        if not texto_ocr:\n"
        "            try:\n"
        "                from org.sikuli.script import TextRecognizer\n"
        "                tr = TextRecognizer.getInstance()\n"
        "                if tr is not None:\n"
        '                    if hasattr(tr, "doOCR"):\n'
        "                        texto_ocr = tr.doOCR(bimg)\n"
        '                    elif hasattr(tr, "recognize"):\n'
        "                        texto_ocr = tr.recognize(bimg)\n"
        "                else:\n"
        '                    errores.append("TextRecognizer.getInstance() devolvio None")\n'
        "            except java.lang.Throwable, e2:\n"
        '                errores.append("TextRecognizer: " + str(e2))\n'
        "            except Exception, e2:\n"
        '                errores.append("TextRecognizer: " + str(e2))\n\n'
        "        if not texto_ocr:\n"
        "            try:\n"
        "                from org.sikuli.script import OCR\n"
        "                texto_ocr = OCR.readText(bimg)\n"
        "            except java.lang.Throwable, e3:\n"
        '                errores.append("OCR.readText: " + str(e3))\n'
        "            except Exception, e3:\n"
        '                errores.append("OCR.readText: " + str(e3))\n\n'
        "        if texto_ocr is not None:\n"
        '            if isinstance(texto_ocr, str):\n'
        '                texto_ocr = texto_ocr.decode("utf-8", "replace")\n'
        "            texto_limpio = texto_ocr.strip()\n"
        "except java.lang.Throwable, e:\n"
        '    errores.append("Java Error: " + str(e))\n'
        "except Exception, e:\n"
        '    errores.append("Python Error: " + str(e))\n\n'
        f'f_out = codecs.open("{out_posix}", "w", encoding="utf-8")\n'
        "f_out.write(texto_limpio)\n"
        "f_out.close()\n"
        "if not texto_limpio and errores:\n"
        f'    f_err = codecs.open("{err_posix}", "w", encoding="utf-8")\n'
        '    f_err.write("; ".join(errores))\n'
        "    f_err.close()\n"
    )

    RUTA_SIKULI_DIR.mkdir(parents=True, exist_ok=True)
    RUTA_SIKULI_PY.write_text(codigo_jython, encoding="utf-8")

    if not RUTA_SCRIPT_TAG.exists():
        contenido_tag = (
            "// Extrae el texto de un ticket o factura usando OCR (SikuliX de TagUI)\n"
            "vision begin\n"
            + codigo_jython
            + "vision finish\n"
        )
        RUTA_SCRIPT_TAG.write_text(contenido_tag, encoding="utf-8")


def _preparar_entorno() -> dict:
    """Asegura que la carpeta src de TagUI esté en el PATH al invocar el subproceso."""
    env = os.environ.copy()
    if RUTA_TAGUI.exists():
        path_actual = env.get("PATH", "")
        if str(RUTA_TAGUI).lower() not in path_actual.lower():
            env["PATH"] = f"{RUTA_TAGUI};{path_actual}"
    return env


def extraer_texto_ocr(ruta_imagen: Path = RUTA_IMAGEN_ACTUAL, timeout: int = 120) -> str:
    """
    Ejecuta el motor SikuliX OCR de TagUI sobre la imagen indicada y devuelve el texto extraído.
    Lanza RuntimeError si TagUI/SikuliX falla, o ValueError si no se detecta texto.
    """
    TAGUI_DIR.mkdir(parents=True, exist_ok=True)
    if not ruta_imagen.exists():
        raise FileNotFoundError(f"No se encontró la imagen para OCR: {ruta_imagen}")

    for archivo_previo in (RUTA_RESULTADO_OCR, RUTA_ERROR_OCR):
        if archivo_previo.exists():
            try:
                archivo_previo.unlink()
            except OSError:
                pass

    _generar_scripts_ocr(ruta_imagen, RUTA_RESULTADO_OCR, RUTA_ERROR_OCR)

    if not RUTA_SIKULIX_JAR.exists():
        raise RuntimeError(
            f"No se encontró el motor SikuliX de TagUI en {RUTA_SIKULIX_JAR}."
        )

    env = _preparar_entorno()

    # Primera ejecución: integra jython-standalone en SikuliX tal como hace tagui.cmd (línea 994)
    if RUTA_JYTHON_JAR.exists():
        logger.info("Inicializando Jython en SikuliX de TagUI por primera vez...")
        try:
            subprocess.run(
                ["java", "-jar", str(RUTA_SIKULIX_JAR), "-h"],
                cwd=str(RUTA_TAGUI),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception as e:
            logger.warning("Aviso durante la inicialización de Jython en SikuliX: %s", e)

    try:
        proc = subprocess.run(
            ["java", "-jar", str(RUTA_SIKULIX_JAR), "-r", str(RUTA_SIKULI_DIR), "-d", "3"],
            cwd=str(RUTA_TAGUI),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            "El proceso de OCR con TagUI (SikuliX) excedió el tiempo de espera."
        ) from e
    except Exception as e:
        raise RuntimeError(f"No se pudo ejecutar Java/SikuliX para el OCR: {e}") from e

    salida_consola = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    try:
        RUTA_LOG_SIKULI.write_text(salida_consola, encoding="utf-8", errors="replace")
    except OSError:
        pass

    if RUTA_ERROR_OCR.exists():
        detalle_sikuli = RUTA_ERROR_OCR.read_text(encoding="utf-8", errors="replace").strip()
        logger.error("Error interno de SikuliX OCR: %s", detalle_sikuli)
        raise RuntimeError(f"Error en SikuliX OCR: {detalle_sikuli}")

    if not RUTA_RESULTADO_OCR.exists():
        logger.error("SikuliX no generó ocr_resultado.txt (rc=%s). Log:\n%s", proc.returncode, salida_consola)
        raise RuntimeError(
            "TagUI/SikuliX finalizó pero no generó el archivo de resultado del OCR. "
            "Revisá tagui/ocr_sikuli.log para más detalles."
        )

    texto = RUTA_RESULTADO_OCR.read_text(encoding="utf-8", errors="replace").strip()
    if not texto:
        raise ValueError(
            "No se pudo detectar texto legible en la imagen. "
            "Intentá con una foto más nítida y bien iluminada."
        )

    logger.info("Texto extraído por TagUI OCR (%d caracteres):\n%s", len(texto), texto)
    return texto

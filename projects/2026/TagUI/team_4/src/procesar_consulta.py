import base64
import copy
import difflib
import json
import os
import re
from datetime import datetime, timedelta

import preinscripcion
from cursos import armar_menu, cargar_cursos, detectar_curso, formatear_curso
from texto import normalizar, palabras

# Rutas absolutas calculadas respecto a este archivo (src/)
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SRC_DIR, ".."))

LOG_FILE = os.path.join(ROOT_DIR, "bot.log")
CSV_PATH = os.path.join(ROOT_DIR, "data", "cursos.csv")
SESIONES_PATH = os.path.join(ROOT_DIR, "data", "sesiones.json")
PATH_ENTRADA = os.path.join(ROOT_DIR, "entrada.json")
PATH_SALIDA = os.path.join(ROOT_DIR, "salida.json")

DURACION_SESION = timedelta(minutes=30)

PALABRAS_SALUDO = ["hola", "buen dia", "buenas", "buenas tardes", "buenas noches", "inicio", "start",
                   "ayuda", "menu", "cursos"]
PALABRAS_DESPEDIDA = ["adios", "chau", "chao", "chaooo", "bye", "nos vemos", "nos vemos pronto",
                      "hasta luego", "hasta pronto", "gracias", "muchas gracias"]

CONTENIDO_NO_SOPORTADO = re.compile(r"^\d{1,2}:\d{2}$|this message is not supported|^null$", re.IGNORECASE)

MENSAJE_DESPEDIDA = "👋 ¡Gracias por tu consulta! Nos vemos pronto."
MENSAJE_NO_RECONOCIDO = (
    "No logré identificar el curso solicitado.\n\n"
    "Escribí 'MENU' para revisar los cursos disponibles o verificá la palabra ingresada."
)


def registrar_log(tipo, chat_id, entrada, salida):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, mode="a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{tipo}] CHAT: '{chat_id}' | IN: '{entrada}' | "
                    f"OUT: '{salida.replace(chr(10), ' ')}'\n")
    except Exception:
        pass


def _contiene_frase(texto_normalizado, frases):
    return any(re.search(rf"\b{re.escape(frase)}\b", texto_normalizado) for frase in frases)


def _parecida(texto_normalizado, candidatas, cutoff):
    mejor = 0.0
    for palabra in palabras(texto_normalizado):
        if len(palabra) < 3:
            continue
        parecidas = difflib.get_close_matches(palabra, candidatas, n=1, cutoff=cutoff)
        if parecidas:
            mejor = max(mejor, difflib.SequenceMatcher(None, palabra, parecidas[0]).ratio())
    return mejor


def es_despedida(texto_normalizado):
    return (_contiene_frase(texto_normalizado, PALABRAS_DESPEDIDA)
            or _parecida(texto_normalizado, ["adios", "chau", "chao", "bye", "gracias"], 0.65) >= 0.7)


def es_saludo(texto_normalizado):
    return (_contiene_frase(texto_normalizado, PALABRAS_SALUDO)
            or _parecida(texto_normalizado, ["menu", "cursos", "ayuda"], 0.6) >= 0.7
            or _parecida(texto_normalizado, PALABRAS_SALUDO, 0.65) >= 0.7)


def _resultado(respuesta, tipo):
    return {"accion": "", "respuesta": respuesta, "tipo": tipo}


def responder_consulta(sesion, texto_normalizado, cursos, inscriptos):
    if preinscripcion.es_pedido_de_inscripcion(texto_normalizado):
        return preinscripcion.iniciar(sesion, texto_normalizado, cursos, inscriptos)

    deteccion = detectar_curso(texto_normalizado, cursos)
    if deteccion and deteccion["tipo"] in ("directo", "inferido"):
        if inscriptos is None:
            return preinscripcion.NECESITA_PLANILLA
        curso = deteccion["curso"]
        sesion["ultimo_curso"] = curso["codigo"]
        inferido = deteccion["tipo"] == "inferido"
        tipo = f"EXITO_FUZZY_{deteccion['similitud']:.2f}" if inferido else "EXITO_DIRECTO"
        return _resultado(formatear_curso(curso, inscriptos, inferido), tipo)

    if es_despedida(texto_normalizado):
        return _resultado(MENSAJE_DESPEDIDA, "INFO_DESPEDIDA")
    if es_saludo(texto_normalizado):
        return _resultado(armar_menu(cursos), "INFO_MENU")
    if deteccion:
        nombre = deteccion["curso"].get("curso", "")
        return _resultado(f"¿Quisiste consultar por '{nombre}'? Escribilo para confirmar.",
                          f"SUGERENCIA_{deteccion['similitud']:.2f}")
    return _resultado(MENSAJE_NO_RECONOCIDO, "NO_RECONOCIDO")


def procesar(entrada, sesion, cursos, ahora):
    sesion = copy.deepcopy(sesion or {})
    actualizado = sesion.get("actualizado")
    if actualizado and ahora - datetime.fromisoformat(actualizado) > DURACION_SESION:
        sesion = {}

    evento = entrada.get("evento") or "mensaje"
    inscriptos = entrada.get("inscriptos")

    if evento in ("registro_ok", "registro_fallido"):
        resultado = preinscripcion.resultado_registro(sesion, evento == "registro_ok", entrada.get("numero"), cursos)
    else:
        texto = (entrada.get("mensaje") or "").strip()
        texto_normalizado = normalizar(texto)
        ultima = sesion.get("ultima_respuesta")
        if texto_normalizado and ultima and texto_normalizado == normalizar(ultima):
            resultado = _resultado("", "IGNORADO_PROPIO")
        elif not texto_normalizado:
            resultado = _resultado("No detecté texto en tu mensaje. Escribí 'MENU' o el nombre de un curso.", "WARN_VACIO")
        elif CONTENIDO_NO_SOPORTADO.search(texto):
            respuesta = "Por ahora solo puedo leer mensajes de texto 🙂"
            pregunta = preinscripcion.pregunta_actual(sesion)
            respuesta += f"\n\n{pregunta}" if pregunta else "\n\nEscribí 'MENU' para ver los cursos."
            resultado = _resultado(respuesta, "CONTENIDO_NO_SOPORTADO")
        elif preinscripcion.en_curso(sesion):
            resultado = preinscripcion.continuar(sesion, texto, texto_normalizado, cursos, inscriptos)
        else:
            resultado = responder_consulta(sesion, texto_normalizado, cursos, inscriptos)

    salida = dict(resultado)
    if salida["accion"] != "leer_planilla":
        sesion["actualizado"] = ahora.isoformat(timespec="seconds")
        if salida["respuesta"]:
            sesion["ultima_respuesta"] = salida["respuesta"]
    return salida, sesion


def _leer_json(ruta, por_defecto):
    try:
        with open(ruta, mode="r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return por_defecto


def _escribir_json(ruta, datos):
    temporal = ruta + ".tmp"
    with open(temporal, mode="w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=True)
    os.replace(temporal, ruta)


def main():
    entrada = _leer_json(PATH_ENTRADA, {})
    chat_id = str(entrada.get("chat_id") or "")
    ahora = datetime.now()

    try:
        cursos = cargar_cursos(CSV_PATH)
    except FileNotFoundError:
        cursos = None
        salida = _resultado("Error interno: La base de datos de cursos no se encuentra disponible.", "ERROR_CSV_FALTA")
    except Exception as e:
        cursos = None
        salida = _resultado(f"Error al leer la base de datos: {e}", "ERROR_CSV_LECTURA")

    if cursos is not None:
        sesiones = _leer_json(SESIONES_PATH, {})
        sesiones = {cid: s for cid, s in sesiones.items()
                    if ahora - datetime.fromisoformat(s.get("actualizado", ahora.isoformat())) <= DURACION_SESION}
        salida, sesion = procesar(entrada, sesiones.get(chat_id), cursos, ahora)
        if salida["accion"] != "leer_planilla" and chat_id:
            sesiones[chat_id] = sesion
            _escribir_json(SESIONES_PATH, sesiones)

    if salida["accion"] != "leer_planilla":
        registrar_log(salida["tipo"], chat_id, entrada.get("mensaje") or entrada.get("evento", ""), salida["respuesta"])

    salida["respuesta_b64"] = base64.b64encode(salida["respuesta"].encode("utf-8")).decode("ascii")
    _escribir_json(PATH_SALIDA, salida)


if __name__ == "__main__":
    main()

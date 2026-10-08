import sys
import csv
import os
import difflib
from datetime import datetime

# Rutas absolutas calculadas respecto a este archivo (src/)
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SRC_DIR, ".."))

LOG_FILE = os.path.join(ROOT_DIR, "bot.log")
CSV_PATH = os.path.join(ROOT_DIR, "data", "cursos.csv")
PATH_IN = os.path.join(ROOT_DIR, "in.txt")
PATH_OUT = os.path.join(ROOT_DIR, "out.txt")

def registrar_log(tipo, entrada, salida):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, mode="a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{tipo}] IN: '{entrada}' | OUT: '{salida.replace(chr(10), ' ')}'\n")
    except Exception:
        pass

def obtener_menu_bienvenida():
    return (
        "👋 ¡Hola! Bienvenido/a al Asistente de Cursos.\n\n"
        "Estoy acá para ayudarte a consultar nuestra oferta de cursos de forma rápida y sencilla.\n\n"
        "📚 Estos son los cursos disponibles:\n\n"
        "• Peluquería y Estilismo\n"
        "• Programación\n"
        "• Maquillaje Profesional\n"
        "• Barbería Clásica\n"
        "• Cocina Profesional\n"
        "• Repostería Creativa\n"
        "• Inglés Conversacional\n"
        "• Fotografía Digital\n"
        "• Yoga y Relajación\n"
        "• Carpintería de Muebles\n"
        "• Electrónica Básica\n"
        "• Robótica para Niños\n"
        "• Guitarra y Música\n"
        "• Dibujo y Pintura\n"
        "• Marketing Digital\n"
        "• Diseño Gráfico\n"
        "• Mecánica de Motos\n"
        "• Huerta y Jardinería\n\n"
        "Escribí el nombre del curso que te interesa y te paso los detalles."
    )

def formatear_curso(data):
    return (
        f"Curso: {data.get('curso', '')}\n"
        f"• Docente: {data.get('docente', '')}\n"
        f"• Días: {data.get('dias', '')}\n"
        f"• Horario: {data.get('horario', '')} hs\n"
        f"• Arancel: {data.get('precio', '')}\n"
        f"• Detalle: {data.get('descripcion', '')}"
    )

def procesar_consulta(texto_crudo):
    consulta = texto_crudo.strip().lower()

    if not consulta:
        res = "No detecté texto en tu mensaje. Escribí 'menu' o el nombre de un curso."
        registrar_log("WARN_VACIO", texto_crudo, res)
        return res

    palabras_saludo = ["hola", "buen dia", "buenas", "buenas tardes", "buenas noches", "inicio", "/start", "ayuda", "menu", "menú", "cursos"]
    # Despedidas
    palabras_despedida = ["adios", "adiós", "chau", "chao", "chaooo", "bye", "nos vemos", "nos vemos pronto", "hasta luego", "hasta pronto", "gracias", "muchas gracias"]
    # Coincidencia directa o por substring (despedidas primero)
    if any(s in consulta for s in palabras_despedida):
        res = "👋 ¡Gracias por tu consulta! Nos vemos pronto."
        registrar_log("INFO_DESPEDIDA", texto_crudo, res)
        return res
    # Coincidencia directa o por substring (saludos/menu)
    if any(s in consulta for s in palabras_saludo):
        res = obtener_menu_bienvenida()
        registrar_log("INFO_MENU", texto_crudo, res)
        return res
    # Fuzzy para capturar variantes con errores tipográficos (mnu, meni, meny, menuu, mnú, etc.)
    tokens_menu = consulta.split()
    candidatos_menu = ["menu", "menú", "cursos", "ayuda"]
    for t in tokens_menu:
        if len(t) < 2:
            continue
        matches_m = difflib.get_close_matches(t, candidatos_menu, n=1, cutoff=0.6)
        if matches_m:
            ratio_m = difflib.SequenceMatcher(None, t, matches_m[0]).ratio()
            if ratio_m >= 0.7:  # umbral razonable para 3-4 letras
                res = obtener_menu_bienvenida()
                registrar_log(f"INFO_MENU_FUZZY_{ratio_m:.2f}", texto_crudo, res)
                return res
    # También intentar contra la lista completa de saludos con cutoff suave
    for t in tokens_menu:
        matches_m2 = difflib.get_close_matches(t, palabras_saludo, n=1, cutoff=0.65)
        if matches_m2:
            ratio_m2 = difflib.SequenceMatcher(None, t, matches_m2[0]).ratio()
            if ratio_m2 >= 0.7:
                res = obtener_menu_bienvenida()
                registrar_log(f"INFO_MENU_FUZZY2_{ratio_m2:.2f}", texto_crudo, res)
                return res
    # Fuzzy para despedidas
    for t in tokens_menu:
        matches_d = difflib.get_close_matches(t, ["adios", "adiós", "chau", "chao", "bye", "gracias"], n=1, cutoff=0.65)
        if matches_d:
            ratio_d = difflib.SequenceMatcher(None, t, matches_d[0]).ratio()
            if ratio_d >= 0.7:
                res = "👋 ¡Gracias por tu consulta! Nos vemos pronto."
                registrar_log(f"INFO_DESPEDIDA_FUZZY_{ratio_d:.2f}", texto_crudo, res)
                return res
    # Despedidas con frases completas
    if "nos vemos" in consulta or "hasta luego" in consulta or "hasta pronto" in consulta:
        res = "👋 ¡Gracias por tu consulta! Nos vemos pronto."
        registrar_log("INFO_DESPEDIDA_FR", texto_crudo, res)
        return res

    if not os.path.exists(CSV_PATH):
        res = "Error interno: La base de datos de cursos no se encuentra disponible."
        registrar_log("ERROR_CSV_FALTA", texto_crudo, res)
        return res

    cursos = {}
    try:
        with open(CSV_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("keyword"):
                    cursos[row["keyword"].strip().lower()] = row
    except Exception as e:
        res = f"Error al leer la base de datos: {str(e)}"
        registrar_log("ERROR_CSV_LECTURA", texto_crudo, res)
        return res

    # 1. Coincidencia directa
    for kw, datos in cursos.items():
        if kw in consulta:
            res = formatear_curso(datos)
            registrar_log("EXITO_DIRECTO", texto_crudo, res)
            return res

    # 2. Fuzzy Matching
    tokens = consulta.split()
    claves = list(cursos.keys())
    mejor_match = None
    mejor_ratio = 0.0

    for t in tokens:
        matches = difflib.get_close_matches(t, claves, n=1, cutoff=0.6)
        if matches:
            candidato = matches[0]
            ratio = difflib.SequenceMatcher(None, t, candidato).ratio()
            if ratio > mejor_ratio:
                mejor_ratio = ratio
                mejor_match = candidato

    if mejor_match:
        if mejor_ratio >= 0.75:
            res = f"*(Inferí que consultaste por '{mejor_match.capitalize()}')*\n\n" + formatear_curso(cursos[mejor_match])
            registrar_log(f"EXITO_FUZZY_{mejor_ratio:.2f}", texto_crudo, res)
            return res
        else:
            res = f"¿Quisiste consultar por '{mejor_match.capitalize()}'? Escribilo para confirmar."
            registrar_log(f"SUGERENCIA_{mejor_ratio:.2f}", texto_crudo, res)
            return res

    # 3. No reconocido
    res = (
        "No logré identificar el curso solicitado.\n\n"
        "Escribí 'menu' para revisar los cursos disponibles o verificá la palabra ingresada."
    )
    registrar_log("NO_RECONOCIDO", texto_crudo, res)
    return res

if __name__ == "__main__":
    texto_recibido = ""

    # Lectura obligatoria con codificación UTF-8 (prioriza la raíz; fallback en src/)
    for ruta_in in (PATH_IN, os.path.join(SRC_DIR, "in.txt")):
        if os.path.exists(ruta_in):
            try:
                with open(ruta_in, mode="r", encoding="utf-8") as f_in:
                    texto_recibido = f_in.read()
            except Exception:
                texto_recibido = ""
            break

    salida = procesar_consulta(texto_recibido)

    # Escritura asegurada en out.txt en UTF-8
    with open(PATH_OUT, mode="w", encoding="utf-8") as f_out:
        f_out.write(salida)
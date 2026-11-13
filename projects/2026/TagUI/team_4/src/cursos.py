import csv
import difflib
import re

from texto import normalizar, palabras

UMBRAL_SIMILITUD = 0.65
UMBRAL_INFERENCIA = 0.75

PALABRAS_IGNORADAS = {
    "quiero", "quisiera", "queria", "info", "informacion", "sobre", "curso", "cursos", "clase",
    "clases", "taller", "talleres", "para", "como", "cuando", "donde", "tiene", "tienen", "tenes",
    "hola", "buenas", "buenos", "dias", "tardes", "noches", "gracias", "precio", "precios",
    "costo", "horario", "horarios", "saber", "consultar", "consulta", "necesito", "puede",
    "pueden", "podes", "menu", "ayuda", "esta", "este", "esto", "estos", "tambien", "favor",
    "porfa", "algo", "bien", "dale", "inscribirme", "inscribir", "inscripcion", "preinscripcion",
    "preinscribirme", "anotarme",
    "basica", "clasica", "creativa", "profesional", "digital",
}


def cargar_cursos(ruta_csv):
    cursos = []
    with open(ruta_csv, mode="r", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            codigo = (fila.get("keyword") or "").strip().lower()
            if not codigo:
                continue
            try:
                cupo = int((fila.get("cupo") or "").strip())
            except ValueError:
                raise ValueError(f"el curso '{codigo}' no tiene un cupo numérico válido")
            curso = dict(fila)
            curso["codigo"] = codigo
            curso["cupo"] = cupo
            cursos.append(curso)
    _calcular_alias(cursos)
    return cursos


def _calcular_alias(cursos):
    palabras_por_curso = [
        {p for p in palabras(normalizar(curso.get("curso", ""))) if len(p) >= 5 and p not in PALABRAS_IGNORADAS}
        for curso in cursos
    ]
    for curso, propias in zip(cursos, palabras_por_curso):
        otras = set().union(*(p for p in palabras_por_curso if p is not propias))
        curso["alias"] = {normalizar(curso["codigo"])} | (propias - otras)


def buscar_por_codigo(cursos, codigo):
    for curso in cursos:
        if curso["codigo"] == codigo:
            return curso
    return None


def detectar_curso(texto_normalizado, cursos):
    mejor_posicion = None
    for curso in cursos:
        for alias in curso["alias"]:
            encontrado = re.search(rf"\b{re.escape(alias)}(?:s|es)?\b", texto_normalizado)
            if encontrado and (mejor_posicion is None or encontrado.start() < mejor_posicion[0]):
                mejor_posicion = (encontrado.start(), curso)
    if mejor_posicion:
        return {"curso": mejor_posicion[1], "tipo": "directo", "similitud": 1.0}

    alias_a_curso = {alias: curso for curso in cursos for alias in curso["alias"]}
    mejor_alias, mejor_similitud = None, 0.0
    for palabra in palabras(texto_normalizado):
        if len(palabra) < 4 or palabra in PALABRAS_IGNORADAS:
            continue
        parecidas = difflib.get_close_matches(palabra, alias_a_curso.keys(), n=1, cutoff=UMBRAL_SIMILITUD)
        if parecidas:
            similitud = difflib.SequenceMatcher(None, palabra, parecidas[0]).ratio()
            if similitud > mejor_similitud:
                mejor_alias, mejor_similitud = parecidas[0], similitud
    if mejor_alias is None:
        return None
    tipo = "inferido" if mejor_similitud >= UMBRAL_INFERENCIA else "sugerido"
    return {"curso": alias_a_curso[mejor_alias], "tipo": tipo, "similitud": mejor_similitud}


def cantidad_inscriptos(curso, inscriptos):
    return sum(1 for inscripto in inscriptos if inscripto.get("codigo") == curso["codigo"])


def cupos_disponibles(curso, inscriptos):
    return max(0, curso["cupo"] - cantidad_inscriptos(curso, inscriptos))


def dni_ya_inscripto(curso, dni, inscriptos):
    return any(i.get("codigo") == curso["codigo"] and i.get("dni") == dni for i in inscriptos)


def armar_menu(cursos):
    lista = "\n".join(f"• {curso.get('curso', '')}" for curso in cursos)
    return (
        "Hola! Bienvenido/a al Asistente de Cursos.\n\n"
        "Estoy acá para ayudarte a consultar nuestra oferta de cursos de forma rápida y sencilla.\n\n"
        f"📚 Estos son los cursos disponibles:\n\n{lista}\n\n"
        "Escribí el nombre del curso que te interesa y te paso los detalles. "
        "Desde ahí también podés realizar la inscripción al mismo."
    )


def formatear_curso(curso, inscriptos, inferido=False):
    disponibles = cupos_disponibles(curso, inscriptos)
    lineas = []
    if inferido:
        lineas += [f"(Inferí que consultaste por '{curso.get('curso', '')}')", ""]
    lineas += [
        f"Curso: {curso.get('curso', '')}",
        f"• Docente: {curso.get('docente', '')}",
        f"• Días: {curso.get('dias', '')}",
        f"• Horario: {curso.get('horario', '')} hs",
        f"• Arancel: {curso.get('precio', '')}",
        f"• Detalle: {curso.get('descripcion', '')}",
        f"• Cupos disponibles: {disponibles} de {curso['cupo']}",
        "",
    ]
    if disponibles > 0:
        lineas.append('📝 Si querés inscribirte, escribí "INSCRIBIRME".')
    else:
        lineas.append("⛔ Este curso no tiene cupos disponibles por el momento.")
    return "\n".join(lineas)

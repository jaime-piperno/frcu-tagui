import re

from cursos import buscar_por_codigo, cupos_disponibles, detectar_curso, dni_ya_inscripto
from texto import limpiar_dato, palabras

PASO_CURSO = "curso"
PASO_NOMBRE = "nombre"
PASO_DNI = "dni"
PASO_EMAIL = "email"
PASO_TELEFONO = "telefono"
PASO_CONFIRMACION = "confirmacion"
PASO_REGISTRANDO = "registrando"

NECESITA_PLANILLA = {"accion": "leer_planilla", "respuesta": "", "tipo": "LEER_PLANILLA"}

PEDIDO_INSCRIPCION = re.compile(r"\b(pre)?(inscrib|inscripc|anot|matricul)")
PALABRAS_CANCELAR = {"cancelar", "cancela", "cancelo", "salir"}
RESPUESTAS_SI = {"si", "s", "dale", "ok", "okey", "confirmo", "confirmar", "correcto", "correctos", "claro", "perfecto", "yes"}
RESPUESTAS_NO = {"no", "n", "nop", "corregir", "incorrecto", "incorrectos", "modificar", "cambiar", "mal"}

NOMBRE_VALIDO = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)+$")
EMAIL_VALIDO = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9\-]+(?:\.[a-z0-9\-]+)*\.[a-z]{2,}$")

PREGUNTAS = {
    PASO_CURSO: '¿A qué curso te querés inscribir? Escribí su nombre (o "CANCELAR" para salir).',
    PASO_NOMBRE: "¿Cuál es tu nombre y apellido?",
    PASO_DNI: "¿Cuál es tu DNI? (solo números, sin puntos)",
    PASO_EMAIL: "¿Cuál es tu email?",
    PASO_TELEFONO: "¿Cuál es tu número de teléfono?",
    PASO_CONFIRMACION: 'Respondé "SÍ" para confirmar la inscripción o "NO" para volver a cargar los datos.',
    PASO_REGISTRANDO: 'Respondé "SÍ" para confirmar la inscripción o "NO" para volver a cargar los datos.',
}


def _resultado(respuesta, tipo, accion="", registro=None):
    resultado = {"accion": accion, "respuesta": respuesta, "tipo": tipo}
    if registro:
        resultado["registro"] = registro
    return resultado


def es_pedido_de_inscripcion(texto_normalizado):
    return bool(PEDIDO_INSCRIPCION.search(texto_normalizado))


def en_curso(sesion):
    return bool(sesion.get("paso"))


def pregunta_actual(sesion):
    return PREGUNTAS.get(sesion.get("paso"), "")


def terminar(sesion):
    for clave in ("paso", "curso", "datos"):
        sesion.pop(clave, None)


def validar_nombre(texto):
    nombre = limpiar_dato(texto)
    if not (5 <= len(nombre) <= 60) or not NOMBRE_VALIDO.match(nombre):
        return None
    if nombre == nombre.lower() or nombre == nombre.upper():
        nombre = nombre.title()
    return nombre


def validar_dni(texto):
    dni = re.sub(r"[\s.\-]", "", limpiar_dato(texto))
    if re.fullmatch(r"[1-9]\d{6,7}", dni):
        return dni
    return None


def validar_email(texto):
    email = limpiar_dato(texto).lower()
    if len(email) <= 80 and ".." not in email and EMAIL_VALIDO.match(email):
        return email
    return None


def validar_telefono(texto):
    telefono = limpiar_dato(texto)
    if not telefono or re.search(r"[^\d\s+().\-]", telefono):
        return None
    numeros = re.sub(r"\D", "", telefono)
    if not 8 <= len(numeros) <= 15:
        return None
    return ("+" if telefono.startswith("+") else "") + numeros


VALIDACIONES = {
    PASO_NOMBRE: (validar_nombre, "nombre", PASO_DNI,
                  "⚠️ Necesito tu nombre y apellido (al menos dos palabras, solo letras). Por ejemplo: Juan Pérez."),
    PASO_DNI: (validar_dni, "dni", PASO_EMAIL,
               "⚠️ El DNI debe tener 7 u 8 números, sin puntos. Por ejemplo: 40123456."),
    PASO_EMAIL: (validar_email, "email", PASO_TELEFONO,
                 "⚠️ Ese email no parece válido. Escribilo de nuevo, por ejemplo: nombre@gmail.com."),
    PASO_TELEFONO: (validar_telefono, "telefono", PASO_CONFIRMACION,
                    "⚠️ El teléfono debe tener entre 8 y 15 números. Por ejemplo: 3442 123456."),
}


def _mensaje_sin_cupo(curso):
    return (f"⛔ Lo siento, {curso['curso']} no tiene cupos disponibles por el momento.\n\n"
            'Escribí "MENU" para ver los otros cursos.')


def _mensaje_duplicado(curso, dni):
    return (f"⚠️ Ya hay una inscripción con el DNI {dni} en {curso['curso']}, "
            "así que no hace falta que te anotes de nuevo.\n\n"
            'Escribí "MENU" si querés consultar otro curso.')


def _resumen(curso, datos):
    return (
        "📋 Revisá tus datos:\n\n"
        f"• Curso: {curso['curso']}\n"
        f"• Nombre y apellido: {datos['nombre']}\n"
        f"• DNI: {datos['dni']}\n"
        f"• Email: {datos['email']}\n"
        f"• Teléfono: {datos['telefono']}\n\n"
        '¿Son correctos? Respondé "SÍ" para confirmar o "NO" para volver a cargarlos.'
    )


def iniciar(sesion, texto_normalizado, cursos, inscriptos):
    deteccion = detectar_curso(texto_normalizado, cursos)
    curso = None
    if deteccion and deteccion["tipo"] in ("directo", "inferido"):
        curso = deteccion["curso"]
    elif sesion.get("ultimo_curso"):
        curso = buscar_por_codigo(cursos, sesion["ultimo_curso"])
    if curso is None:
        sesion["paso"] = PASO_CURSO
        return _resultado(PREGUNTAS[PASO_CURSO], "PREINSCRIPCION_PIDE_CURSO")
    return _ofrecer_formulario(sesion, curso, inscriptos)


def _ofrecer_formulario(sesion, curso, inscriptos):
    if inscriptos is None:
        return NECESITA_PLANILLA
    sesion["ultimo_curso"] = curso["codigo"]
    if cupos_disponibles(curso, inscriptos) == 0:
        terminar(sesion)
        return _resultado(_mensaje_sin_cupo(curso), "PREINSCRIPCION_SIN_CUPO")
    sesion.update({"paso": PASO_NOMBRE, "curso": curso["codigo"], "datos": {}})
    return _resultado(
        f"¡Genial! Vamos a inscribirte en {curso['curso']}.\n"
        'Te voy a pedir 4 datos. Podés escribir "CANCELAR" en cualquier momento para salir.\n\n'
        + PREGUNTAS[PASO_NOMBRE],
        "PREINSCRIPCION_INICIO",
    )


def continuar(sesion, texto, texto_normalizado, cursos, inscriptos):
    if PALABRAS_CANCELAR & set(palabras(texto_normalizado)):
        terminar(sesion)
        return _resultado('Listo, cancelé la inscripción. Escribí "MENU" para ver los cursos.',
                          "PREINSCRIPCION_CANCELADA")

    paso = sesion["paso"]
    if paso == PASO_CURSO:
        return _elegir_curso(sesion, texto_normalizado, cursos, inscriptos)

    curso = buscar_por_codigo(cursos, sesion.get("curso"))
    if curso is None:
        terminar(sesion)
        return _resultado('Ese curso ya no está disponible. Escribí "MENU" para ver la oferta actual.',
                          "PREINSCRIPCION_CURSO_INEXISTENTE")

    if paso in (PASO_CONFIRMACION, PASO_REGISTRANDO):
        return _confirmar(sesion, texto_normalizado, curso, inscriptos)
    return _guardar_dato(sesion, paso, texto, curso, inscriptos)


def _elegir_curso(sesion, texto_normalizado, cursos, inscriptos):
    deteccion = detectar_curso(texto_normalizado, cursos)
    if deteccion and deteccion["tipo"] in ("directo", "inferido"):
        return _ofrecer_formulario(sesion, deteccion["curso"], inscriptos)
    if deteccion:
        return _resultado(f"¿Quisiste decir '{deteccion['curso']['curso']}'? Escribí el nombre del curso "
                          'para confirmar (o "CANCELAR" para salir).', "PREINSCRIPCION_SUGERENCIA")
    lista = ", ".join(curso["curso"] for curso in cursos)
    return _resultado(f"No reconocí ese curso. Los cursos disponibles son: {lista}.\n\n"
                      + PREGUNTAS[PASO_CURSO], "PREINSCRIPCION_CURSO_NO_RECONOCIDO")


def _guardar_dato(sesion, paso, texto, curso, inscriptos):
    validar, campo, siguiente, mensaje_error = VALIDACIONES[paso]
    valor = validar(texto)
    if valor is None:
        return _resultado(mensaje_error, f"PREINSCRIPCION_DATO_INVALIDO_{campo.upper()}")

    if paso == PASO_DNI:
        if inscriptos is None:
            return NECESITA_PLANILLA
        if dni_ya_inscripto(curso, valor, inscriptos):
            terminar(sesion)
            return _resultado(_mensaje_duplicado(curso, valor), "PREINSCRIPCION_DUPLICADA")

    sesion["datos"][campo] = valor
    sesion["paso"] = siguiente
    if siguiente == PASO_CONFIRMACION:
        return _resultado(_resumen(curso, sesion["datos"]), "PREINSCRIPCION_RESUMEN")
    if paso == PASO_NOMBRE:
        return _resultado(f"Gracias, {valor.split()[0]}. " + PREGUNTAS[siguiente], "PREINSCRIPCION_DATO")
    return _resultado(PREGUNTAS[siguiente], "PREINSCRIPCION_DATO")


def _confirmar(sesion, texto_normalizado, curso, inscriptos):
    primera = (palabras(texto_normalizado) or [""])[0]
    if primera in RESPUESTAS_NO:
        sesion.update({"paso": PASO_NOMBRE, "datos": {}})
        return _resultado("De acuerdo, carguemos los datos de nuevo.\n\n" + PREGUNTAS[PASO_NOMBRE],
                          "PREINSCRIPCION_RECARGA")
    if primera not in RESPUESTAS_SI:
        return _resultado(PREGUNTAS[PASO_CONFIRMACION], "PREINSCRIPCION_CONFIRMACION_PENDIENTE")

    if inscriptos is None:
        return NECESITA_PLANILLA
    datos = sesion["datos"]
    if cupos_disponibles(curso, inscriptos) == 0:
        terminar(sesion)
        return _resultado(f"⛔ Lo siento, mientras completabas los datos se ocuparon los cupos de {curso['curso']}. "
                          "Tu inscripción no se registró.", "PREINSCRIPCION_SIN_CUPO")
    if dni_ya_inscripto(curso, datos["dni"], inscriptos):
        terminar(sesion)
        return _resultado(_mensaje_duplicado(curso, datos["dni"]), "PREINSCRIPCION_DUPLICADA")

    sesion["paso"] = PASO_REGISTRANDO
    registro = {"codigo": curso["codigo"], "curso": curso["curso"], **datos}
    return _resultado("", "PREINSCRIPCION_REGISTRANDO", accion="registrar", registro=registro)


def resultado_registro(sesion, ok, numero, cursos):
    curso = buscar_por_codigo(cursos, sesion.get("curso")) or {"curso": "el curso"}
    if ok:
        terminar(sesion)
        return _resultado(f"¡Listo! Tu inscripción N° {numero} a {curso['curso']} quedó registrada.\n\n"
                          'Escribí "MENU" si querés consultar otro curso.', "PREINSCRIPCION_REGISTRADA")
    sesion["paso"] = PASO_CONFIRMACION
    return _resultado("⚠️ No pude guardar tu inscripción por un problema técnico. "
                      'Escribí "SÍ" en unos minutos para volver a intentarlo, o "CANCELAR" para salir.',
                      "PREINSCRIPCION_ERROR_PLANILLA")

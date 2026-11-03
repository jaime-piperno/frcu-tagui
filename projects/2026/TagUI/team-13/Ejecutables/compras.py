# compras.py
# El cálculo de la lista de compras: qué ingredientes llevan las comidas
# elegidas, cuánto hay ya en la alacena y cuánto falta comprar.
#
# Es la misma lógica que se lleva en bot.py, pero separada en un módulo aparte para poder testearla sin tener que levantar el bot.
# Los CSV se leen como texto con el módulo csv de Python: no hace falta tener
# Excel ni ningún otro programa instalado, y anda igual en Windows y Linux.

import csv
import math
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_DATOS = RAIZ / "data"

# ==================================================================
# EXCEPCIONES
class ErrorDeDatos(Exception):
    """Un CSV tiene algo que no se puede interpretar (ej: una cantidad con letras)."""

# ==================================================================
# FUNCIONES DE LECTURA Y ESCRITURA DE CSV
#esta funcion lee un archivo csv y devuelve una lista de listas, donde cada sublista es una fila del archivo. 
# Se saltea la fila de encabezados y las filas vacías. Además, se eliminan los espacios en blanco al principio 
# y al final de cada campo.
def _leer_csv(nombre):
    ruta = CARPETA_DATOS / nombre
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        # se saltea la fila de encabezados y las filas vacías
        filas = list(csv.reader(archivo))[1:]
    return [[campo.strip() for campo in fila] for fila in filas if any(fila)]

#esta funcion convierte un texto en un número flotante. Si el texto no se puede convertir, 
# lanza una excepción ErrorDeDatos con un mensaje de error que indica el archivo y la fila 
# donde ocurrió el error.
def _a_numero(texto, archivo, numero_fila):
    try:
        return float(texto)
    except ValueError:
        # PERTURBACION EXOGENA: un error de formato en un CSV. Viene de los
        # datos de entrada, no de un fallo del bot.
        raise ErrorDeDatos(
            f"{archivo}, fila {numero_fila + 1}: la cantidad '{texto}' no es un número "
            "(usá punto para los decimales, ej: 0.5)"
        )

#esta funcion devuelve una lista de comidas distintas que hay en la base de recetas, en el orden del CSV.
def comidas_disponibles():
    """Las comidas distintas que hay en la base de recetas, en el orden del CSV."""
    comidas = []
    for fila in _leer_csv("BaseDatos.csv"):
        if fila[0] not in comidas:
            comidas.append(fila[0])
    return comidas


def comidas_del_menu():
    """Las comidas del menú semanal (Menu.csv), una por día."""
    return [fila[1] for fila in _leer_csv("Menu.csv")]


def menu_semanal():
    """El menú de la semana como lista de (dia, comida)."""
    return [(fila[0], fila[1]) for fila in _leer_csv("Menu.csv")]


def guardar_menu(dias_y_comidas):
    _escribir_csv("Menu.csv", ["Dia", "Comida"], dias_y_comidas)


def ingredientes_de(comida):
    """Los ingredientes de una comida como lista de (ingrediente, cantidad, unidad)."""
    return [(fila[1], fila[2], fila[3] if len(fila) > 3 else "unidad")
            for fila in _leer_csv("BaseDatos.csv") if fila[0] == comida]


# ==================================================================
# CARGA DE RECETAS NUEVAS (desde el bot)
# ==================================================================
UNIDADES = ("kg", "lt", "unidad")


def _escribir_csv(nombre, encabezados, filas):
    # se reescribe el archivo entero: así queda prolijo aunque el original no
    # termine en salto de línea
    with open(CARPETA_DATOS / nombre, "w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo, lineterminator="\n")
        escritor.writerow(encabezados)
        escritor.writerows(filas)


def normalizar(texto):
    """
    Para comparar nombres sin que importen mayúsculas, tildes ni espacios de
    más: "Milanesas con Puré " y "milanesas con pure" dan lo mismo.
    """
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(letra for letra in sin_tildes if not unicodedata.combining(letra))
    return " ".join(sin_tildes.lower().split())


def comida_existente(nombre):
    """Si ya hay una comida con ese nombre (comparando normalizado), la devuelve tal como está escrita."""
    for comida in comidas_disponibles():
        if normalizar(comida) == normalizar(nombre):
            return comida
    return None


def ingredientes_conocidos():
    """
    {nombre normalizado: (nombre como está escrito, unidad)} de todos los
    ingredientes que ya aparecen en las recetas o en el stock. Sirve para que
    una receta nueva use el mismo nombre y la misma unidad: si no, el stock no
    se descontaría ("papa" no es "Papa", y 1 lt no se puede restar de 1 kg).
    """
    conocidos = {}
    for fila in _leer_csv("StockActual.csv"):
        conocidos[normalizar(fila[0])] = (fila[0], fila[2] if len(fila) > 2 else "unidad")
    for fila in _leer_csv("BaseDatos.csv"):
        conocidos[normalizar(fila[1])] = (fila[1], fila[3] if len(fila) > 3 else "unidad")
    return conocidos


def interpretar_ingrediente(renglon, permitir_cero=False):
    """
    Convierte "Papa, 1, kg" en ("Papa", 1.0, "kg"). Acepta también la coma
    decimal ("Papa, 0,5, kg"). Si el renglón no se entiende, levanta
    ErrorDeDatos con una explicación para mostrarle al usuario.
    Con permitir_cero, acepta cantidad 0 (en la alacena: "ya no tengo").
    """
    partes = [parte.strip() for parte in renglon.split(",")]
    if len(partes) == 4:
        # "Papa, 0,5, kg": la coma del medio era la de los decimales
        partes = [partes[0], f"{partes[1]}.{partes[2]}", partes[3]]
    if len(partes) != 3 or not all(partes):
        raise ErrorDeDatos(f"«{renglon}»: tiene que ser Ingrediente, cantidad, unidad")

    nombre, texto_cantidad, unidad = partes
    unidad = unidad.lower()
    try:
        cantidad = float(texto_cantidad)
    except ValueError:
        raise ErrorDeDatos(f"«{renglon}»: la cantidad «{texto_cantidad}» no es un número")
    if cantidad < 0 or (cantidad == 0 and not permitir_cero):
        raise ErrorDeDatos(f"«{renglon}»: la cantidad tiene que ser mayor que cero")
    if unidad not in UNIDADES:
        raise ErrorDeDatos(f"«{renglon}»: la unidad tiene que ser {', '.join(UNIDADES)}")

    conocido = ingredientes_conocidos().get(normalizar(nombre))
    if conocido:
        nombre, unidad_conocida = conocido
        if unidad_conocida != unidad:
            raise ErrorDeDatos(f"«{renglon}»: {nombre} ya se usa en {unidad_conocida}, cargalo en {unidad_conocida}")
    return nombre, cantidad, unidad


def interpretar_respuesta_factura(respuesta):
    """Valida renglones devueltos por la IA y separa los que no se pudieron cargar."""
    ingredientes = []
    rechazados = []
    for renglon in respuesta.splitlines():
        texto = renglon.strip()
        if not texto or texto.startswith("```"):
            continue
        texto = texto.lstrip("-*• \t").strip()
        if not texto:
            continue
        texto = re.sub(
            r"^gemini\s+(?:ha\s+dicho|dijo)\s*[:,.-]?\s*",
            "",
            texto,
            flags=re.IGNORECASE,
        )
        try:
            ingredientes.append(interpretar_ingrediente(texto))
            continue
        except ErrorDeDatos:
            pass

        cantidad_primero = re.match(
            r"^(\d+(?:[.,]\d+)?)\s+(kg|lt|unidad(?:es)?)\s+(.+)$",
            texto,
            flags=re.IGNORECASE,
        )
        if cantidad_primero:
            cantidad, unidad, nombre = cantidad_primero.groups()
            unidad = "unidad" if unidad.lower().startswith("unidad") else unidad.lower()
            normalizado = f"{nombre.strip()}, {cantidad.replace(',', '.')}, {unidad}"
            try:
                ingredientes.append(interpretar_ingrediente(normalizado))
                continue
            except ErrorDeDatos:
                pass
        rechazados.append(renglon.strip())
    return ingredientes, rechazados


def agregar_receta(comida, ingredientes):
    """Suma la comida nueva al final de BaseDatos.csv. `ingredientes`: lista de (nombre, cantidad, unidad)."""
    if comida_existente(comida):
        raise ErrorDeDatos(f"ya existe una comida llamada «{comida_existente(comida)}»")
    filas = _leer_csv("BaseDatos.csv")
    for nombre, cantidad, unidad in ingredientes:
        filas.append([comida, nombre, formatear_cantidad(cantidad), unidad])
    _escribir_csv("BaseDatos.csv", ["Comida", "Ingrediente", "Cantidad", "Unidad"], filas)


# ==================================================================
# LA ALACENA (StockActual.csv, la actualiza la persona desde el bot)
# ==================================================================
def stock_actual():
    """Lo que hay en la alacena, como lista de (ingrediente, cantidad, unidad)."""
    return [(fila[0], fila[1], fila[2] if len(fila) > 2 else "unidad")
            for fila in _leer_csv("StockActual.csv")]


def faltantes_para_receta(comida):
    """Devuelve ingredientes y cantidades que faltan para preparar una receta."""
    receta = ingredientes_de(comida)
    if not receta:
        raise ErrorDeDatos(f"No hay ingredientes cargados para «{comida}».")

    necesarios = {}
    for numero_fila, (nombre, cantidad, unidad) in enumerate(receta, start=1):
        clave = normalizar(nombre)
        cantidad = _a_numero(cantidad, "BaseDatos.csv", numero_fila)
        if clave in necesarios and necesarios[clave][2] != unidad:
            raise ErrorDeDatos(f"{nombre} aparece con unidades incompatibles en la receta.")
        if clave in necesarios:
            necesarios[clave][1] += cantidad
        else:
            necesarios[clave] = [nombre, cantidad, unidad]

    disponibles = {}
    for numero_fila, (nombre, cantidad, unidad) in enumerate(stock_actual(), start=1):
        clave = normalizar(nombre)
        cantidad = _a_numero(cantidad, "StockActual.csv", numero_fila)
        if clave in disponibles:
            if disponibles[clave][1] != unidad:
                raise ErrorDeDatos(f"{nombre} aparece con unidades incompatibles en la alacena.")
            disponibles[clave][0] += cantidad
        else:
            disponibles[clave] = [cantidad, unidad]

    faltantes = []
    for clave, (nombre, cantidad, unidad) in necesarios.items():
        cantidad_disponible, unidad_disponible = disponibles.get(clave, (0, unidad))
        if unidad_disponible != unidad:
            raise ErrorDeDatos(
                f"{nombre} se receta en {unidad}, pero la alacena lo tiene en {unidad_disponible}."
            )
        faltante = round(cantidad - cantidad_disponible, 6)
        if faltante <= 0:
            continue
        if unidad == "unidad":
            faltante = math.ceil(faltante)
        else:
            faltante = round(faltante, 2)
        faltantes.append((nombre, faltante, unidad))
    return faltantes


def se_usa_en_recetas(ingrediente):
    return any(normalizar(fila[1]) == normalizar(ingrediente) for fila in _leer_csv("BaseDatos.csv"))


def actualizar_stock(cambios):
    """
    `cambios`: lista de (ingrediente, cantidad, unidad). La cantidad pasa a
    ser la que hay (no se suma). Con cantidad 0, el ingrediente se saca.
    """
    stock = {normalizar(nombre): [nombre, cantidad, unidad] for nombre, cantidad, unidad in stock_actual()}
    for nombre, cantidad, unidad in cambios:
        if cantidad == 0:
            stock.pop(normalizar(nombre), None)
        else:
            stock[normalizar(nombre)] = [nombre, formatear_cantidad(cantidad), unidad]
    _escribir_csv("StockActual.csv", ["Ingrediente", "CantidadDisponible", "Unidad"], stock.values())


def stock_despues_de_sumar(compras_recibidas):
    """Calcula el stock resultante de una compra sin modificar el CSV."""
    stock = {
        normalizar(nombre): [nombre, float(cantidad), unidad]
        for nombre, cantidad, unidad in stock_actual()
    }
    for nombre, cantidad, unidad in compras_recibidas:
        nombre, cantidad, unidad = interpretar_ingrediente(
            f"{nombre}, {cantidad}, {unidad}"
        )
        clave = normalizar(nombre)
        if clave in stock:
            existente = stock[clave]
            if existente[2] != unidad:
                raise ErrorDeDatos(
                    f"{nombre} ya está en {existente[2]}, no se puede sumar en {unidad}"
                )
            existente[1] = round(existente[1] + float(cantidad), 6)
        else:
            stock[clave] = [nombre, round(float(cantidad), 6), unidad]

    return [
        (nombre, round(cantidad, 6), unidad)
        for nombre, cantidad, unidad in stock.values()
    ]


def stock_proyectado_de_compra(compras_recibidas):
    """Devuelve solo los productos comprados, con su cantidad final proyectada."""
    afectados = {normalizar(nombre) for nombre, _, _ in compras_recibidas}
    return [
        ingrediente
        for ingrediente in stock_despues_de_sumar(compras_recibidas)
        if normalizar(ingrediente[0]) in afectados
    ]


def sumar_al_stock(compras_recibidas):
    """Suma productos confirmados de una factura al stock existente."""
    filas = [
        [nombre, formatear_cantidad(cantidad), unidad]
        for nombre, cantidad, unidad in stock_despues_de_sumar(compras_recibidas)
    ]
    _escribir_csv("StockActual.csv", ["Ingrediente", "CantidadDisponible", "Unidad"], filas)


def calcular_lista(seleccionadas):
    """
    Devuelve (faltantes, advertencias):
      faltantes    lista de (ingrediente, cantidad, unidad) que hay que comprar
      advertencias comidas elegidas que no tienen receta cargada

    Si una comida está repetida en `seleccionadas`, sus ingredientes se suman
    dos veces (igual que cuando una comida aparece dos días en el menú).
    """
    recetas = _leer_csv("BaseDatos.csv")
    stock = _leer_csv("StockActual.csv")

    necesario = {}
    unidad_de = {}
    for fila in recetas:
        ingrediente = fila[1]
        necesario.setdefault(ingrediente, 0)
        unidad_de[ingrediente] = fila[3] if len(fila) > 3 and fila[3] else "unidad"

    # sumar lo que hace falta según las comidas elegidas
    advertencias = []
    for comida in seleccionadas:
        encontrada = False
        for numero_fila, fila in enumerate(recetas, start=1):
            if fila[0] == comida:
                encontrada = True
                necesario[fila[1]] += _a_numero(fila[2], "BaseDatos.csv", numero_fila)
        # PERTURBACION EXOGENA: el menú pide una comida que no está cargada en
        # la base de recetas. El error viene de los datos de entrada, no del bot.
        if not encontrada and comida not in advertencias:
            advertencias.append(comida)

    # descontar lo que ya hay en la alacena
    # (RETROALIMENTACION NEGATIVA: el bot mide el estado actual del sistema
    #  antes de decidir la salida)
    disponible = {}
    for numero_fila, fila in enumerate(stock, start=1):
        disponible[fila[0]] = _a_numero(fila[1], "StockActual.csv", numero_fila)

    faltantes = []
    for ingrediente, cantidad in necesario.items():
        # se redondea a 6 decimales antes de comparar para que la suma de
        # números con coma no deje restos tipo 0.30000000000000004
        falta = round(cantidad - disponible.get(ingrediente, 0), 6)
        if falta <= 0:
            continue
        unidad = unidad_de[ingrediente]
        if unidad == "unidad":
            # lo que se cuenta de a uno (huevos, lechugas) se redondea PARA
            # ARRIBA: no tiene sentido ir al súper a comprar "media lechuga"
            falta = math.ceil(falta)
        else:
            falta = round(falta, 2)
        faltantes.append((ingrediente, falta, unidad))

    return faltantes, advertencias


def formatear_cantidad(cantidad):
    # 1.0 -> "1", 0.5 -> "0.5"
    return str(int(cantidad)) if cantidad == int(cantidad) else str(cantidad)


def armar_mensaje(faltantes):
    lineas = ["Lista de compras:"]
    for ingrediente, cantidad, unidad in faltantes:
        lineas.append(f"- {ingrediente}: {formatear_cantidad(cantidad)} {unidad}")
    return "\n".join(lineas)


def guardar_evidencia(mensaje):
    """Deja la última lista en mensaje.txt, como evidencia local de la corrida."""
    (RAIZ / "mensaje.txt").write_text(mensaje + "\n", encoding="utf-8")

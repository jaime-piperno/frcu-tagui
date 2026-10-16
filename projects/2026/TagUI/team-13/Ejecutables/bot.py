# QUÉ HACE
#   El bot de Telegram es el DISPARADOR del proceso. Queda escuchando en la PC;
#   cuando alguien le escribe /start aparecen botones para elegir qué cocinar
#   (una comida, varias, o el menú semanal entero). Con eso:
#     1. calcula qué falta comprar, leyendo las recetas y la alacena de los
#        CSV (compras.py)
#     2. el robot abre Telegram Web en Chrome, busca el grupo y le escribe la
#        lista, como lo haría una persona (robot_telegram_web.py)
#     3. el bot responde cómo salió, con una captura de pantalla
#
# CÓMO SE EJECUTA
#   Windows:  Ejecutables\iniciar_bot.cmd    (o: py bot.py)
#   Linux:    ./Ejecutables/iniciar_bot.sh   (o: python3 bot.py)
#   Mientras esté corriendo, el bot atiende. Se corta con Ctrl+C.
#
# CÓMO ESCUCHA
#   Le pregunta a la Bot API de Telegram si hay mensajes nuevos (getUpdates)
#   una y otra vez ("long polling"). Así no hace falta un servidor publicado en
#   internet: alcanza con que la PC tenga conexión.

import random
import subprocess
import sys
import time
from pathlib import Path

import requests

#Traemos los modulos de compras y robot_telegram_web para poder usar sus funciones
import compras
import robot_telegram_web
from configuracion import leer_config

#leemos la configuracion del archivo config.txt para obtener el token del bot, el chat_id permitido y el nombre del grupo de telegram
CONFIG = leer_config()
API = f"https://api.telegram.org/bot{CONFIG['TELEGRAM_TOKEN']}/"
CHAT_PERMITIDO = int(CONFIG["TELEGRAM_CHAT_ID"])
GRUPO = CONFIG["GRUPO_TELEGRAM"]

ROBOT = Path(__file__).resolve().parent / "robot_telegram_web.py"
# Si el robot tarda más que esto, se da por colgado (una corrida normal
# tarda menos de un minuto)
MINUTOS_MAXIMOS_ROBOT = 3

# Estado de cada menú de botones abierto, por (chat_id, message_id):
#   {"modo": "principal" | "una" | "varias", "elegidas": [...]}
menus = {}


# LLAMADAS A LA BOT API
#Esta función llama a la API de Telegram para enviar mensajes, fotos, editar mensajes, etc.
def llamar(metodo, archivos=None, **datos):
    if archivos:
        respuesta = requests.post(API + metodo, data=datos, files=archivos, timeout=60)
    else:
        respuesta = requests.post(API + metodo, json=datos, timeout=60)
    resultado = respuesta.json()
    if not resultado.get("ok"):
        print(f"Telegram rechazó {metodo}: {resultado.get('description')}")
    return resultado

#Esta función responde a un chat con un mensaje de texto y opcionalmente con botones
def responder(chat_id, texto, botones=None):
    datos = {"chat_id": chat_id, "text": texto}
    if botones:
        datos["reply_markup"] = {"inline_keyboard": botones}
    return llamar("sendMessage", **datos)

#Esta función edita un mensaje existente en un chat, cambiando su texto y opcionalmente sus botones
def editar(chat_id, message_id, texto, botones=None):
    datos = {"chat_id": chat_id, "message_id": message_id, "text": texto}
    datos["reply_markup"] = {"inline_keyboard": botones or []}
    llamar("editMessageText", **datos)

#Esta función envía una foto a un chat con un texto opcional
def mandar_foto(chat_id, ruta, texto):
    with open(ruta, "rb") as foto:
        llamar("sendPhoto", archivos={"photo": foto}, chat_id=chat_id, caption=texto)


# LOS MENÚS DE BOTONES
#Esta función devuelve los botones principales del bot, que permiten elegir entre una comida, varias comidas, 
# el menú de la semana, ver recetas, cargar receta o ver la alacena
def botones_principales():
    return [
        [{"text": "🍽 Una comida", "callback_data": "modo:una"},
         {"text": "🛒 Varias comidas", "callback_data": "modo:varias"}],
        [{"text": "📅 Menú de la semana", "callback_data": "semana"}],
        [{"text": "📖 Ver recetas", "callback_data": "recetas"},
         {"text": "➕ Cargar receta", "callback_data": "cargar"}],
        [{"text": "🥫 Mi alacena", "callback_data": "alacena"}],
    ]

#Esta función devuelve los botones para elegir comidas según el modo (una, varias, recetas o día) y la lista de comidas disponibles
def botones_de_comidas(modo, comidas):
    prefijo = {"una": "una", "varias": "sumar", "recetas": "ver", "dia": "poner"}[modo]
    botones = [[{"text": comida, "callback_data": f"{prefijo}:{i}"}]
               for i, comida in enumerate(comidas)]
    if modo == "varias":
        botones.append([{"text": "✅ Listo", "callback_data": "listo"},
                        {"text": "🗑 Borrar", "callback_data": "borrar"}])
    volver = "semana" if modo == "dia" else "volver"
    botones.append([{"text": "⬅ Volver", "callback_data": volver}])
    return botones

#Esta función devuelve un resumen de las comidas elegidas, indicando cuántas veces se repite cada una
def resumen(elegidas):
    # ["Asado", "Asado", "Fideos"] -> "Asado x2, Fideos"
    partes = []
    for comida in dict.fromkeys(elegidas):
        veces = elegidas.count(comida)
        partes.append(comida if veces == 1 else f"{comida} x{veces}")
    return ", ".join(partes)

#Esta función devuelve un texto que indica las comidas elegidas hasta el momento, o un mensaje indicando que no se ha elegido ninguna
def texto_varias(elegidas):
    elegido = resumen(elegidas) if elegidas else "(ninguna todavía)"
    return ("Tocá las comidas que quieras (se pueden repetir) y después ✅ Listo.\n\n"
            f"Elegidas: {elegido}")

#esta función devuelve un texto que indica el menú de la semana, con un aviso opcional al principio
def texto_semana(aviso=""):
    comidas = compras.comidas_disponibles()
    renglones = []
    for dia, comida in compras.menu_semanal():
        # PERTURBACION EXOGENA: el menú (si se edita a mano) puede nombrar una
        # comida que no está en la base de recetas; se marca para que se vea
        marca = "" if comida in comidas else "  ⚠ sin receta"
        renglones.append(f"{dia}: {comida}{marca}")
    return (aviso + "\n\n" if aviso else "") + "📅 Menú de la semana:\n\n" + "\n".join(renglones)

#Esta función devuelve los botones para el menú de la semana, permitiendo comprar para la semana, cambiar un día, sortear otro menú o volver al menú principal
def botones_semana():
    return [
        [{"text": "🛒 Comprar para la semana", "callback_data": "semana:comprar"}],
        [{"text": "✏ Cambiar un día", "callback_data": "semana:cambiar"},
         {"text": "🎲 Sortear otro", "callback_data": "semana:sortear"}],
        [{"text": "⬅ Volver", "callback_data": "volver"}],
    ]

#esta función devuelve un texto con los ingredientes de una comida, indicando la cantidad y unidad de cada uno
def texto_receta(comida):
    renglones = [f"- {nombre}: {cantidad} {unidad}"
                 for nombre, cantidad, unidad in compras.ingredientes_de(comida)]
    return f"📖 {comida}\n\n" + "\n".join(renglones)

#esta función abre el menú principal para un chat, enviando un mensaje con los botones principales y guardando el estado del menú en la variable global menus
def abrir_menu(chat_id):
    enviado = responder(chat_id, "¿Qué querés hacer?", botones_principales())
    if enviado.get("ok"):
        menus[(chat_id, enviado["result"]["message_id"])] = {"modo": "principal", "elegidas": []}

#esta función atiende los botones que se tocan en el menú, actualizando el estado del menú y respondiendo según la acción elegida
def atender_boton(consulta):
    chat_id = consulta["message"]["chat"]["id"]
    message_id = consulta["message"]["message_id"]
    dato = consulta["data"]
    llamar("answerCallbackQuery", callback_query_id=consulta["id"])

    if dato.startswith("carga:"):
        atender_boton_de_carga(chat_id, message_id, dato)
        return
    if dato == "alacena:listo":
        terminar_edicion_alacena(chat_id, message_id)
        return

    menu = menus.get((chat_id, message_id))
    if menu is None:
        # un menú viejo (ya usado, o de antes de reiniciar el bot)
        editar(chat_id, message_id, "Este menú ya no está activo. Mandá /start para abrir uno nuevo.")
        return

    comidas = compras.comidas_disponibles()

    if dato == "volver":
        menu.update(modo="principal", elegidas=[])
        editar(chat_id, message_id, "¿Qué querés hacer?", botones_principales())
    elif dato == "modo:una":
        menu["modo"] = "una"
        editar(chat_id, message_id, "¿Qué comida?", botones_de_comidas("una", comidas))
    elif dato == "modo:varias":
        menu.update(modo="varias", elegidas=[])
        editar(chat_id, message_id, texto_varias([]), botones_de_comidas("varias", comidas))
    elif dato.startswith("sumar:"):
        menu["elegidas"].append(comidas[int(dato.split(":")[1])])
        editar(chat_id, message_id, texto_varias(menu["elegidas"]), botones_de_comidas("varias", comidas))
    elif dato == "borrar":
        menu["elegidas"] = []
        editar(chat_id, message_id, texto_varias([]), botones_de_comidas("varias", comidas))
    elif dato.startswith("una:"):
        cerrar_menu_y_procesar(chat_id, message_id, [comidas[int(dato.split(":")[1])]])
    elif dato == "listo":
        if menu["elegidas"]:
            cerrar_menu_y_procesar(chat_id, message_id, menu["elegidas"])

    # --- el menú de la semana: verlo, cambiarlo o comprar para él ---
    elif dato == "semana":
        menu["modo"] = "semana"
        editar(chat_id, message_id, texto_semana(), botones_semana())
    elif dato == "semana:comprar":
        cerrar_menu_y_procesar(chat_id, message_id, compras.comidas_del_menu(), "el menú de la semana")
    elif dato == "semana:cambiar":
        dias = [dia for dia, _ in compras.menu_semanal()]
        botones = [[{"text": dia, "callback_data": f"dia:{i}"}] for i, dia in enumerate(dias)]
        botones.append([{"text": "⬅ Volver", "callback_data": "semana"}])
        editar(chat_id, message_id, "¿Qué día querés cambiar?", botones)
    elif dato.startswith("dia:"):
        menu["dia"] = int(dato.split(":")[1])
        dia = compras.menu_semanal()[menu["dia"]][0]
        editar(chat_id, message_id, f"¿Qué se come el {dia}?", botones_de_comidas("dia", comidas))
    elif dato.startswith("poner:"):
        semana = compras.menu_semanal()
        dia = semana[menu["dia"]][0]
        semana[menu["dia"]] = (dia, comidas[int(dato.split(":")[1])])
        compras.guardar_menu(semana)
        editar(chat_id, message_id, texto_semana(f"✅ Cambié el {dia}."), botones_semana())
    elif dato == "semana:sortear":
        dias = [dia for dia, _ in compras.menu_semanal()]
        # sin repetir comidas, mientras alcancen para todos los días
        if len(comidas) >= len(dias):
            sorteadas = random.sample(comidas, len(dias))
        else:
            sorteadas = random.choices(comidas, k=len(dias))
        compras.guardar_menu(list(zip(dias, sorteadas)))
        editar(chat_id, message_id, texto_semana("🎲 Sorteé un menú nuevo."), botones_semana())

    # --- ver las recetas cargadas ---
    elif dato == "recetas":
        menu["modo"] = "recetas"
        editar(chat_id, message_id,
               f"Hay {len(comidas)} recetas cargadas. Tocá una para ver sus ingredientes.",
               botones_de_comidas("recetas", comidas))
    elif dato.startswith("ver:"):
        comida = comidas[int(dato.split(":")[1])]
        editar(chat_id, message_id, texto_receta(comida),
               [[{"text": "⬅ Volver al listado", "callback_data": "recetas"}]])

    # --- cargar una receta nueva ---
    elif dato == "cargar":
        del menus[(chat_id, message_id)]
        empezar_carga(chat_id, message_id)

    # --- la alacena: verla y actualizarla ---
    elif dato == "alacena":
        editar(chat_id, message_id, texto_alacena(),
               [[{"text": "✏ Actualizar", "callback_data": "alacena:actualizar"},
                 {"text": "⬅ Volver", "callback_data": "volver"}]])
    elif dato == "alacena:actualizar":
        del menus[(chat_id, message_id)]
        empezar_edicion_alacena(chat_id, message_id)


# ==================================================================
# CARGAR UNA RECETA NUEVA
# Es una charla de dos pasos: primero el nombre de la comida, después los
# ingredientes (en uno o varios mensajes). Recién al tocar ✅ Guardar se
# escribe en BaseDatos.csv.
#
# Estado de cada carga en curso, por chat_id:
#   {"nombre": None | "Comida", "ingredientes": [(nombre, cantidad, unidad)],
#    "resumen": message_id del último resumen con botones}
cargas = {}

INSTRUCCIONES_INGREDIENTES = (
    "Ahora mandame los ingredientes, uno por renglón, así:\n\n"
    "Ingrediente, cantidad, unidad\n\n"
    "Por ejemplo:\n"
    "Papa, 1, kg\n"
    "Huevo, 2, unidad\n"
    "Leche, 0.5, lt\n\n"
    f"Las unidades pueden ser: {', '.join(compras.UNIDADES)}. "
    "Podés mandarlos todos juntos o en varios mensajes."
)

#esta función devuelve los botones para la carga de una receta, que permiten guardar o cancelar la carga
def botones_carga():
    return [[{"text": "✅ Guardar", "callback_data": "carga:guardar"},
             {"text": "❌ Cancelar", "callback_data": "carga:cancelar"}]]

#esta función inicia el proceso de carga de una receta, eliminando cualquier otra carga en curso y creando un nuevo estado de carga para el chat
def empezar_carga(chat_id, message_id):
    alacenas_en_edicion.pop(chat_id, None)  # una cosa a la vez
    cargas[chat_id] = {"nombre": None, "ingredientes": [], "resumen": None}
    editar(chat_id, message_id,
           "➕ Cargar receta\n\n¿Cómo se llama la comida? Escribila en un mensaje.\n"
           "(Para cancelar, mandá /cancelar)")

#esta función atiende los mensajes de texto que llegan durante el proceso de carga de una receta, interpretando el nombre de la comida y los ingredientes, y actualizando el estado de la carga en curso
def atender_texto_de_carga(chat_id, texto):
    carga = cargas[chat_id]

    if carga["nombre"] is None:
        nombre = " ".join(texto.split())
        # no se puede cargar dos veces la misma comida (sin importar
        # mayúsculas, tildes ni espacios de más)
        existente = compras.comida_existente(nombre)
        if existente:
            responder(chat_id, f"⚠ Ya existe «{existente}». Podés ver sus ingredientes en "
                      "📖 Ver recetas.\n\nMandame otro nombre, o /cancelar.")
            return
        carga["nombre"] = nombre
        responder(chat_id, f"Comida: {nombre}\n\n{INSTRUCCIONES_INGREDIENTES}")
        return

    ya_cargados = {compras.normalizar(nombre) for nombre, _, _ in carga["ingredientes"]}
    problemas = []
    for renglon in texto.splitlines():
        if not renglon.strip():
            continue
        try:
            ingrediente = compras.interpretar_ingrediente(renglon)
        except compras.ErrorDeDatos as error:
            problemas.append(str(error))
            continue
        if compras.normalizar(ingrediente[0]) in ya_cargados:
            problemas.append(f"«{renglon.strip()}»: {ingrediente[0]} ya está en la receta")
            continue
        ya_cargados.add(compras.normalizar(ingrediente[0]))
        carga["ingredientes"].append(ingrediente)

    # el resumen anterior pierde sus botones: solo sirve el último
    if carga["resumen"]:
        llamar("editMessageReplyMarkup", chat_id=chat_id, message_id=carga["resumen"],
               reply_markup={"inline_keyboard": []})

    texto_respuesta = ""
    if problemas:
        texto_respuesta += "⚠ Estos renglones no los cargué:\n" + "\n".join(problemas) + "\n\n"
    lista = "\n".join(f"- {nombre}: {compras.formatear_cantidad(cantidad)} {unidad}"
                      for nombre, cantidad, unidad in carga["ingredientes"])
    texto_respuesta += f"«{carga['nombre']}» por ahora lleva:\n{lista or '(nada todavía)'}"
    texto_respuesta += "\n\nMandá más ingredientes, o tocá ✅ Guardar."
    enviado = responder(chat_id, texto_respuesta, botones_carga())
    carga["resumen"] = enviado.get("result", {}).get("message_id")

#esta función atiende los botones que se tocan durante el proceso de carga de una receta, guardando o cancelando la carga según corresponda
def atender_boton_de_carga(chat_id, message_id, dato):
    carga = cargas.get(chat_id)
    if carga is None or carga["resumen"] != message_id:
        editar(chat_id, message_id, "Esta carga ya no está activa. Mandá /start para empezar de nuevo.")
        return

    if dato == "carga:cancelar":
        del cargas[chat_id]
        editar(chat_id, message_id, "❌ Carga cancelada, no guardé nada.")
        return

    if not carga["ingredientes"]:
        responder(chat_id, "Todavía no cargaste ningún ingrediente.")
        return
    try:
        compras.agregar_receta(carga["nombre"], carga["ingredientes"])
    except compras.ErrorDeDatos as error:
        editar(chat_id, message_id, f"⚠ No la guardé: {error}")
    else:
        editar(chat_id, message_id,
               f"✅ Guardé «{carga['nombre']}» con {len(carga['ingredientes'])} ingredientes. "
               "Ya aparece en los botones: mandá /start para usarla.")
    del cargas[chat_id]


# ==================================================================
# MI ALACENA: el stock lo actualiza la persona
# StockActual.csv es lo que hay en la casa de quien usa el bot. Como el bot no
# puede saber qué se compró o qué se usó, lo corrige la persona: manda
# "Papa, 3, kg" y esa pasa a ser la cantidad que hay. Cada mensaje se guarda
# en el momento.
#
# Chats que están editando la alacena: {chat_id: message_id del último resumen}
alacenas_en_edicion = {}

#esta función devuelve un texto que indica el contenido de la alacena, con los ingredientes y sus cantidades y unidades, o un mensaje indicando que la alacena está vacía
def texto_alacena():
    stock = compras.stock_actual()
    if not stock:
        return "🥫 La alacena está vacía."
    renglones = [f"- {nombre}: {cantidad} {unidad}" for nombre, cantidad, unidad in stock]
    return "🥫 En la alacena hay:\n\n" + "\n".join(renglones)

#esta función inicia el proceso de edición de la alacena, eliminando cualquier otra carga en curso y creando un nuevo estado de edición para el chat
def empezar_edicion_alacena(chat_id, message_id):
    cargas.pop(chat_id, None)  # una cosa a la vez
    alacenas_en_edicion[chat_id] = None
    editar(chat_id, message_id,
           texto_alacena() + "\n\n✏ Mandame lo que tenés ahora, uno por renglón:\n\n"
           "Ingrediente, cantidad, unidad\n\n"
           "Por ejemplo:\nPapa, 3, kg\nHuevo, 12, unidad\nLeche, 0, lt\n\n"
           "La cantidad que pongas pasa a ser la que hay (no se suma). "
           "Con 0, el ingrediente se saca de la alacena.")

#esta función atiende los mensajes de texto que llegan durante el proceso de edición de la alacena, interpretando los ingredientes y sus cantidades y unidades, y actualizando el stock actual
def atender_texto_de_alacena(chat_id, texto):
    cambios, problemas, avisos = [], [], []
    for renglon in texto.splitlines():
        if not renglon.strip():
            continue
        try:
            ingrediente = compras.interpretar_ingrediente(renglon, permitir_cero=True)
        except compras.ErrorDeDatos as error:
            problemas.append(str(error))
            continue
        cambios.append(ingrediente)
        # puede ser un error de tipeo ("Papas" en vez de "Papa"): se guarda
        # igual, pero se avisa, porque así no se descontaría de ninguna receta
        if ingrediente[1] > 0 and not compras.se_usa_en_recetas(ingrediente[0]):
            avisos.append(ingrediente[0])
    compras.actualizar_stock(cambios)

    # el resumen anterior pierde su botón: solo sirve el último
    if alacenas_en_edicion[chat_id]:
        llamar("editMessageReplyMarkup", chat_id=chat_id, message_id=alacenas_en_edicion[chat_id],
               reply_markup={"inline_keyboard": []})

    texto_respuesta = ""
    if cambios:
        texto_respuesta += f"✅ Actualicé {len(cambios)} ingrediente(s).\n\n"
    if problemas:
        texto_respuesta += "⚠ Estos renglones no los cargué:\n" + "\n".join(problemas) + "\n\n"
    if avisos:
        texto_respuesta += ("ℹ Ninguna receta usa: " + ", ".join(avisos)
                            + ". Si es un error de tipeo, mandalo con 0 para sacarlo.\n\n")
    texto_respuesta += texto_alacena() + "\n\nMandá más cambios, o tocá ✅ Listo."
    enviado = responder(chat_id, texto_respuesta,
                        [[{"text": "✅ Listo", "callback_data": "alacena:listo"}]])
    alacenas_en_edicion[chat_id] = enviado.get("result", {}).get("message_id")

#esta función termina el proceso de edición de la alacena, guardando los cambios y eliminando el estado de edición para el chat
def terminar_edicion_alacena(chat_id, message_id):
    if alacenas_en_edicion.get(chat_id) != message_id:
        editar(chat_id, message_id, "Esta edición ya terminó. Mandá /start para abrir el menú.")
        return
    del alacenas_en_edicion[chat_id]
    editar(chat_id, message_id, "✅ Alacena guardada.\n\n" + texto_alacena())


# ==================================================================
# EL PROCESO: calcular la lista y que el robot la mande
#esta función ejecuta el robot en un proceso aparte, con un tiempo máximo de espera, para evitar que se quede colgado si Chrome o TagUI se cuelgan
def ejecutar_robot(mensaje):
    """
    Corre el robot en un proceso aparte, con tiempo máximo. Así, si Chrome o
    TagUI se cuelgan (por ejemplo, con la PC bloqueada), el bot no se queda
    esperando para siempre: corta el robot y sigue atendiendo.
    """
    robot_telegram_web.CAPTURA.unlink(missing_ok=True)  # que no quede la captura de una corrida anterior
    try:
        proceso = subprocess.run(
            [sys.executable, str(ROBOT), "--enviar", GRUPO],
            input=mensaje.encode("utf-8"), capture_output=True,
            timeout=MINUTOS_MAXIMOS_ROBOT * 60, cwd=ROBOT.parent,
        )
    except subprocess.TimeoutExpired:
        robot_telegram_web.terminar_procesos_tagui()
        raise robot_telegram_web.ErrorDelRobot(
            f"tardó más de {MINUTOS_MAXIMOS_ROBOT} minutos y lo corté. ¿La PC está "
            "bloqueada? Con la sesión bloqueada Chrome no dibuja las páginas"
        )
    if proceso.returncode != 0:
        errores = proceso.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise robot_telegram_web.ErrorDelRobot(errores[-1] if errores else "falló sin dar detalles")
    return robot_telegram_web.CAPTURA

#esta función cierra el menú de botones y procesa las comidas seleccionadas, calculando la lista de compras, guardando la evidencia y ejecutando el robot para enviar la lista al grupo de Telegram
def cerrar_menu_y_procesar(chat_id, message_id, seleccionadas, descripcion=None):
    del menus[(chat_id, message_id)]
    editar(chat_id, message_id, f"Pedido: {descripcion or resumen(seleccionadas)}")

    try:
        faltantes, advertencias = compras.calcular_lista(seleccionadas)
    except compras.ErrorDeDatos as error:
        responder(chat_id, f"⚠ No pude leer los datos: {error}")
        return

    # PERTURBACION EXOGENA: comidas del pedido que no tienen receta cargada
    if advertencias:
        responder(chat_id, "⚠ No tienen receta cargada en BaseDatos.csv (no se cuentan): "
                  + ", ".join(advertencias))

    if not faltantes:
        responder(chat_id, "No hay nada para comprar: el stock actual alcanza para lo elegido.")
        return

    mensaje = compras.armar_mensaje(faltantes)
    compras.guardar_evidencia(mensaje)
    responder(chat_id, f"🤖 Abro Telegram Web y le escribo la lista al grupo «{GRUPO}»...")

    try:
        captura = ejecutar_robot(mensaje)
    except robot_telegram_web.ErrorDelRobot as error:
        # ERROR EN ESTADO ESTABLE: el cálculo salió bien pero el sistema no
        # llega al resultado esperado (no hay sesión en Telegram Web, no
        # encuentra el grupo, se cortó la conexión). Para que la lista no se
        # pierda, el bot la manda él mismo por la Bot API.
        responder(chat_id, f"⚠ El robot no pudo mandarla por Telegram Web: {error}\n\n"
                  f"Te la mando yo:\n\n{mensaje}")
        return

    confirmacion = f"✅ Lista enviada al grupo «{GRUPO}»"
    if captura.exists():
        mandar_foto(chat_id, captura, confirmacion)
    else:
        responder(chat_id, confirmacion)


# ==================================================================
# EL BUCLE PRINCIPAL
#esta función descarta los pedidos pendientes que llegaron mientras el bot estaba apagado, para que no se disparen solos al prenderlo
def descartar_pendientes():
    # Los pedidos que llegaron mientras el bot estaba apagado se descartan,
    # para que no se disparen solos al prenderlo.
    pendientes = llamar("getUpdates", offset=-1, timeout=0).get("result", [])
    return pendientes[-1]["update_id"] + 1 if pendientes else 0

#esta función verifica si la actualización recibida proviene del chat permitido, para evitar que cualquier persona pueda usar el bot y controlar la PC de otro
def es_del_chat_permitido(actualizacion):
    mensaje = actualizacion.get("message") or actualizacion.get("callback_query", {}).get("message")
    return mensaje is not None and mensaje["chat"]["id"] == CHAT_PERMITIDO

#esta función atiende una actualización recibida del bot, verificando si es un mensaje de texto o un botón presionado, y llamando a la función correspondiente para procesarlo
def atender(actualizacion):
    # Solo se aceptan pedidos del chat de config.txt: si cualquiera que
    # encuentre el bot pudiera usarlo, estaría manejando la PC de otro.
    if not es_del_chat_permitido(actualizacion):
        return
    if "callback_query" in actualizacion:
        atender_boton(actualizacion["callback_query"])
        return
    chat_id = actualizacion["message"]["chat"]["id"]
    texto = actualizacion["message"].get("text", "")
    # en grupos el comando puede llegar como /start@nombre_del_bot
    comando = texto.split()[0].split("@")[0] if texto else ""
    if comando in ("/start", "/menu", "/cancelar"):
        # un comando corta cualquier carga o edición que haya quedado a medias
        if cargas.pop(chat_id, None) is not None:
            responder(chat_id, "❌ Carga de receta cancelada, no guardé nada.")
        if chat_id in alacenas_en_edicion:
            del alacenas_en_edicion[chat_id]
            responder(chat_id, "Dejé de editar la alacena (lo que ya mandaste quedó guardado).")
        if comando != "/cancelar":
            abrir_menu(chat_id)
    elif texto and chat_id in cargas:
        atender_texto_de_carga(chat_id, texto)
    elif texto and chat_id in alacenas_en_edicion:
        atender_texto_de_alacena(chat_id, texto)

#esta función es el punto de entrada del programa, que verifica el token del bot, descarta los pedidos pendientes y entra en un bucle para recibir actualizaciones de Telegram y atenderlas
def main():
    bot = llamar("getMe")
    if not bot.get("ok"):
        raise SystemExit("El token de config.txt no es válido.")
    print(f"Bot @{bot['result']['username']} escuchando. Escribile /start en Telegram. (Ctrl+C para cortar)")

    siguiente = descartar_pendientes()
    while True:
        try:
            respuesta = requests.get(API + "getUpdates",
                                     params={"offset": siguiente, "timeout": 30}, timeout=40)
            actualizaciones = respuesta.json().get("result", [])
        except requests.RequestException:
            print("Sin conexión con Telegram, reintento en 5 segundos...")
            time.sleep(5)
            continue

        for actualizacion in actualizaciones:
            siguiente = actualizacion["update_id"] + 1
            try:
                atender(actualizacion)
            except Exception as error:
                # un pedido que falla no tiene que tirar abajo el bot entero
                print(f"Error atendiendo un pedido: {error!r}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Bot detenido.")

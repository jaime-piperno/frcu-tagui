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
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path

import requests

#Traemos los modulos de compras y robot_telegram_web para poder usar sus funciones
import compras
import procesamiento
import procesador_factura
from configuracion import leer_config

# La configuración se carga en main(), no al importar el módulo, para poder
# probar la interfaz sin credenciales ni conexiones a Telegram.
API = None
API_ARCHIVOS = None
CHAT_PERMITIDO = None
GRUPO = ""
CARPETA_EVIDENCIA_FACTURAS = (
    Path(__file__).resolve().parent.parent / "docs" / "evidencia" / "facturas"
)

# Estado de cada menú de botones abierto, por (chat_id, message_id):
#   {"modo": "principal" | "una" | "varias", "elegidas": [...]}
menus = {}
esperando_foto_factura = set()
fotos_factura = {}
confirmaciones_factura = {}


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
        [{"text": "🧾 Cargar factura", "callback_data": "factura:nueva"}],
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

    if dato.startswith("factura:"):
        atender_boton_de_factura(chat_id, message_id, dato)
        return
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

    if dato in ("volver", "inicio"):
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
        botones_recetas = botones_de_comidas("recetas", comidas)
        # Insertar botón de resumen antes del "Volver"
        botones_recetas.insert(-1, [{"text": "📋 Resumen de todas", "callback_data": "recetas:resumen"}])
        editar(chat_id, message_id,
               f"Hay {len(comidas)} recetas cargadas. Tocá una para ver sus ingredientes.",
               botones_recetas)
    elif dato == "recetas:resumen":
        mostrar_resumen_recetas(chat_id, message_id, comidas)
    elif dato.startswith("ver:"):
        comida = comidas[int(dato.split(":")[1])]
        menu["comida_actual"] = comida
        editar(
            chat_id, message_id, texto_receta(comida),
            [[{"text": "🥘 ¿Tengo todo?", "callback_data": "receta:disponibilidad"}],
             [{"text": "⬅ Volver al listado", "callback_data": "recetas"},
              {"text": "🏠 Menú", "callback_data": "inicio"}]],
        )
    elif dato == "receta:disponibilidad":
        comida = menu.get("comida_actual")
        if not comida:
            editar(chat_id, message_id, "Elegí una receta para revisar sus ingredientes.",
                   botones_de_comidas("recetas", comidas))
            return
        try:
            faltantes = compras.faltantes_para_receta(comida)
        except compras.ErrorDeDatos as error:
            editar(chat_id, message_id, f"⚠ No pude revisar la receta: {error}")
            return
        if faltantes:
            renglones = [
                f"- {nombre}: {compras.formatear_cantidad(cantidad)} {unidad}"
                for nombre, cantidad, unidad in faltantes
            ]
            texto = f"Para {comida} te falta:\n\n" + "\n".join(renglones)
        else:
            texto = f"✅ Tenés todos los ingredientes para {comida}."
        indice = comidas.index(comida)
        editar(
            chat_id, message_id, texto,
            [[{"text": "⬅ Ver receta", "callback_data": f"ver:{indice}"}],
             [{"text": "📖 Otra receta", "callback_data": "recetas"},
              {"text": "🏠 Menú", "callback_data": "inicio"}]],
        )

    # --- cargar una receta nueva ---
    elif dato == "cargar":
        del menus[(chat_id, message_id)]
        empezar_carga(chat_id, message_id)

    # --- la alacena: verla y actualizarla ---
    elif dato == "alacena":
        editar(chat_id, message_id, texto_alacena(),
               [[{"text": "✏ Actualizar", "callback_data": "alacena:actualizar"}],
                [{"text": "📖 Ver recetas", "callback_data": "recetas"},
                 {"text": "⬅ Volver", "callback_data": "volver"}]])
    elif dato == "alacena:actualizar":
        del menus[(chat_id, message_id)]
        empezar_edicion_alacena(chat_id, message_id)


def mostrar_resumen_recetas(chat_id, message_id, comidas):
    """Muestra un resumen de todas las recetas: cuáles se pueden hacer y cuáles no."""
    completas = []
    incompletas = []
    for comida in comidas:
        try:
            faltantes = compras.faltantes_para_receta(comida)
        except compras.ErrorDeDatos:
            incompletas.append(f"⚠ {comida}: no se pudo revisar")
            continue
        if not faltantes:
            completas.append(f"✅ {comida}")
        else:
            detalles = ", ".join(
                f"{compras.formatear_cantidad(cant)} {unid} de {nombre}"
                for nombre, cant, unid in faltantes
            )
            incompletas.append(f"❌ {comida}: te falta {detalles}")
    partes = []
    if completas:
        partes.append("🟢 Podés hacer:\n" + "\n".join(completas))
    if incompletas:
        partes.append("🔴 Te falta algo para:\n" + "\n".join(incompletas))
    if not completas and not incompletas:
        partes.append("No hay recetas cargadas.")
    texto = "\n\n".join(partes)
    editar(
        chat_id, message_id, texto,
        [[{"text": "📖 Ver recetas", "callback_data": "recetas"},
          {"text": "🏠 Menú", "callback_data": "inicio"}]],
    )


def descargar_foto_telegram(file_id):
    """Descarga una foto de Telegram a un archivo temporal y devuelve su ruta."""
    archivo = llamar("getFile", file_id=file_id)
    if not archivo.get("ok"):
        raise RuntimeError(archivo.get("description", "Telegram no encontró la foto"))

    ruta_remota = archivo["result"]["file_path"]
    respuesta = requests.get(API_ARCHIVOS + ruta_remota, timeout=60)
    respuesta.raise_for_status()
    sufijo = Path(ruta_remota).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(prefix="factura_", suffix=sufijo, delete=False) as temporal:
        temporal.write(respuesta.content)
    return Path(temporal.name)


def _limpiar_foto_factura(chat_id):
    ruta = fotos_factura.pop(chat_id, None)
    if ruta:
        ruta.unlink(missing_ok=True)


def archivar_foto_factura(ruta_temporal):
    CARPETA_EVIDENCIA_FACTURAS.mkdir(parents=True, exist_ok=True)
    nombre = datetime.now().strftime("ticket_%Y%m%d_%H%M%S_%f") + Path(ruta_temporal).suffix
    ruta_evidencia = CARPETA_EVIDENCIA_FACTURAS / nombre
    shutil.copy2(ruta_temporal, ruta_evidencia)
    return ruta_evidencia





def botones_plan_b_factura():
    return [
        [{"text": "🥫 Cargar manualmente", "callback_data": "factura:manual"}],
        [{"text": "🏠 Volver al menú", "callback_data": "factura:menu"}],
    ]


def pedir_foto_factura(chat_id, message_id):
    _limpiar_foto_factura(chat_id)
    confirmaciones_factura.pop(chat_id, None)
    esperando_foto_factura.add(chat_id)
    editar(chat_id, message_id,
           "🧾 Enviame una foto clara de la factura o ticket. "
           "La imagen se enviará a Gemini para leer los productos; evitá incluir datos personales.",
           [[{"text": "❌ Cancelar", "callback_data": "factura:cancelar"}]])


def atender_foto_factura(chat_id, fotos):
    if chat_id not in esperando_foto_factura:
        return
    foto = max(fotos, key=lambda item: item.get("file_size", 0))
    try:
        ruta = descargar_foto_telegram(foto["file_id"])
    except (requests.RequestException, RuntimeError, KeyError) as error:
        responder(
            chat_id,
            f"⚠ No pude descargar la foto: {error}",
            botones_plan_b_factura(),
        )
        return
    _limpiar_foto_factura(chat_id)
    fotos_factura[chat_id] = ruta
    esperando_foto_factura.discard(chat_id)
    try:
        evidencia = archivar_foto_factura(ruta)
        print(f"Evidencia de factura guardada en: {evidencia}")
    except OSError as error:
        print(f"No se pudo guardar la evidencia de la factura: {error}")
        responder(
            chat_id,
            "⚠ No pude guardar la foto de evidencia. No inicié la lectura; "
            "podés cargar la compra manualmente.",
            botones_plan_b_factura(),
        )
        return
    responder(chat_id, "⏳ Foto recibida. Estoy leyendo el ticket con Gemini...")
    try:
        respuesta = procesador_factura.procesar_factura(
            ruta, compras.ingredientes_conocidos()
        )
        ingredientes, rechazados = compras.interpretar_respuesta_factura(respuesta)
        if not ingredientes:
            responder(
                chat_id,
                "⚠ No pude leer productos del ticket. La alacena no cambió.",
                botones_plan_b_factura(),
            )
            return
        solicitar_confirmacion_factura(chat_id, ingredientes)
    except Exception as error:
        print(f"No se pudo procesar la factura de {chat_id}: {error}")
        responder(
            chat_id,
            "⚠ No pude leer el ticket. No modifiqué la alacena. "
            "Podés cargar la compra manualmente.",
            botones_plan_b_factura(),
        )


def solicitar_confirmacion_factura(chat_id, ingredientes):
    """Muestra el resultado del lector externo y espera confirmación explícita."""
    stock_proyectado = compras.stock_proyectado_de_compra(ingredientes)
    lineas = [f"{nombre}, {compras.formatear_cantidad(cantidad)}, {unidad}"
              for nombre, cantidad, unidad in stock_proyectado]
    texto = "\n".join(lineas)
    texto += "\n\nConfirmá para guardar estos totales en la alacena."
    enviado = responder(
        chat_id,
        texto,
        [[{"text": "✅ Confirmar", "callback_data": "factura:confirmar"},
          {"text": "❌ Cancelar", "callback_data": "factura:cancelar"}]],
    )
    if enviado.get("ok"):
        confirmaciones_factura[chat_id] = {
            "message_id": enviado["result"]["message_id"],
            "ingredientes": ingredientes,
            "stock_proyectado": stock_proyectado,
        }


def atender_boton_de_factura(chat_id, message_id, dato):
    if dato == "factura:manual":
        esperando_foto_factura.discard(chat_id)
        confirmaciones_factura.pop(chat_id, None)
        _limpiar_foto_factura(chat_id)
        empezar_edicion_alacena(chat_id, message_id)
        return
    if dato == "factura:menu":
        esperando_foto_factura.discard(chat_id)
        confirmaciones_factura.pop(chat_id, None)
        _limpiar_foto_factura(chat_id)
        abrir_menu(chat_id)
        return
    if dato == "factura:nueva":
        menu = menus.pop((chat_id, message_id), None)
        if menu is not None:
            pedir_foto_factura(chat_id, message_id)
        return

    confirmacion = confirmaciones_factura.get(chat_id)
    if dato == "factura:confirmar":
        if confirmacion is None or confirmacion["message_id"] != message_id:
            editar(chat_id, message_id, "Esta confirmación ya no está activa. Mandá /start para empezar de nuevo.")
            return
        try:
            compras.sumar_al_stock(confirmacion["ingredientes"])
        except compras.ErrorDeDatos as error:
            editar(chat_id, message_id, f"⚠ No actualicé la alacena: {error}")
            return
        del confirmaciones_factura[chat_id]
        _limpiar_foto_factura(chat_id)
        editar(
            chat_id, message_id, "✅ Compra confirmada.\n\n" + texto_alacena(),
            [[{"text": "🏠 Volver al menú", "callback_data": "factura:menu"}]],
        )
    elif dato == "factura:cancelar":
        esperando_foto_factura.discard(chat_id)
        confirmaciones_factura.pop(chat_id, None)
        _limpiar_foto_factura(chat_id)
        editar(
            chat_id, message_id, "❌ Carga de factura cancelada. No actualicé la alacena.",
            [[{"text": "🏠 Volver al menú", "callback_data": "factura:menu"}]],
        )


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
    editar(chat_id, message_id, "✅ Alacena guardada.\n\n" + texto_alacena(),
           [[{"text": "📖 Ver recetas", "callback_data": "recetas"},
             {"text": "🏠 Volver al menú", "callback_data": "factura:menu"}]])


# ==================================================================
# EL PROCESO: calcular la lista y que el robot la mande
#esta función cierra el menú de botones y procesa las comidas seleccionadas, calculando la lista de compras, guardando la evidencia y ejecutando el robot para enviar la lista al grupo de Telegram
def cerrar_menu_y_procesar(chat_id, message_id, seleccionadas, descripcion=None):
    del menus[(chat_id, message_id)]
    editar(chat_id, message_id, f"Pedido: {descripcion or resumen(seleccionadas)}")

    try:
        resultado = procesamiento.procesar_pedido(seleccionadas, GRUPO)
    except compras.ErrorDeDatos as error:
        responder(chat_id, f"⚠ No pude leer los datos: {error}")
        return

    # PERTURBACION EXOGENA: comidas del pedido que no tienen receta cargada
    if resultado.advertencias:
        responder(chat_id, "⚠ No tienen receta cargada en BaseDatos.csv (no se cuentan): "
                  + ", ".join(resultado.advertencias))

    if not resultado.faltantes:
        responder(chat_id, "No hay nada para comprar: el stock actual alcanza para lo elegido.")
        return

    responder(chat_id, f"🤖 Abro Telegram Web y le escribo la lista al grupo «{GRUPO}»...")

    if resultado.error_robot:
        # ERROR EN ESTADO ESTABLE: el cálculo salió bien pero el sistema no
        # llega al resultado esperado (no hay sesión en Telegram Web, no
        # encuentra el grupo, se cortó la conexión). Para que la lista no se
        # pierda, el bot la manda él mismo por la Bot API.
        responder(chat_id, f"⚠ El robot no pudo mandarla por Telegram Web: {resultado.error_robot}\n\n"
                  f"Te la mando yo:\n\n{resultado.mensaje}")
        return

    confirmacion = f"✅ Lista enviada al grupo «{GRUPO}»"
    if resultado.captura and resultado.captura.exists():
        mandar_foto(chat_id, resultado.captura, confirmacion)
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
    mensaje = actualizacion["message"]
    chat_id = mensaje["chat"]["id"]
    texto = mensaje.get("text", "")
    # en grupos el comando puede llegar como /start@nombre_del_bot
    comando = texto.split()[0].split("@")[0] if texto else ""
    if comando in ("/start", "/menu", "/cancelar"):
        esperando_foto_factura.discard(chat_id)
        confirmaciones_factura.pop(chat_id, None)
        _limpiar_foto_factura(chat_id)
        # un comando corta cualquier carga o edición que haya quedado a medias
        if cargas.pop(chat_id, None) is not None:
            responder(chat_id, "❌ Carga de receta cancelada, no guardé nada.")
        if chat_id in alacenas_en_edicion:
            del alacenas_en_edicion[chat_id]
            responder(chat_id, "Dejé de editar la alacena (lo que ya mandaste quedó guardado).")
        if comando != "/cancelar":
            abrir_menu(chat_id)
    elif mensaje.get("photo"):
        atender_foto_factura(chat_id, mensaje["photo"])
    elif texto and chat_id in cargas:
        atender_texto_de_carga(chat_id, texto)
    elif texto and chat_id in alacenas_en_edicion:
        atender_texto_de_alacena(chat_id, texto)

#esta función es el punto de entrada del programa, que verifica el token del bot, descarta los pedidos pendientes y entra en un bucle para recibir actualizaciones de Telegram y atenderlas
def main():
    global API, API_ARCHIVOS, CHAT_PERMITIDO, GRUPO
    config = leer_config()
    API = f"https://api.telegram.org/bot{config['TELEGRAM_TOKEN']}/"
    API_ARCHIVOS = f"https://api.telegram.org/file/bot{config['TELEGRAM_TOKEN']}/"
    CHAT_PERMITIDO = int(config["TELEGRAM_CHAT_ID"])
    GRUPO = config["GRUPO_TELEGRAM"]

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

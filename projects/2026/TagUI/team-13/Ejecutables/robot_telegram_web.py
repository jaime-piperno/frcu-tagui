# robot_telegram_web.py
# LA PARTE RPA: el robot hace lo que haría una persona. Abre Chrome, entra a
# Telegram Web, busca el grupo por su nombre, pega la lista y la envía.
#
# Usa la librería `rpa` (RPA for Python), que por dentro maneja TagUI. La
# primera vez que se usa descarga TagUI sola (~200 MB).
#
# El mensaje sale desde la cuenta de Telegram con la que se inició sesión en
# ese Chrome (la de la persona), NO desde el bot. El bot de Telegram solo
# recibe el pedido y avisa cómo salió (ver bot.py).
#
# PRIMERA VEZ / PROBAR A MANO
#   py robot_telegram_web.py                 (Linux: python3 robot_telegram_web.py)
#   Abre Telegram Web. Si no hay sesión, escaneás el QR con el celular
#   (Telegram > Ajustes > Dispositivos > Vincular dispositivo) y la sesión
#   queda guardada en el perfil de Chrome de TagUI para las próximas veces.
#   Si la primera vez Chrome se abre y no pasa nada, cortalo con Ctrl+C y
#   correlo de nuevo: al estrenar el perfil, Chrome a veces le cierra a TagUI
#   la pestaña que iba a manejar.
#
#   py robot_telegram_web.py "Saved Messages"
#   Además de iniciar sesión, manda un mensaje de prueba a ese chat. Conviene
#   probar con "Saved Messages" ("Mensajes guardados" si Telegram Web está en
#   castellano), que es un chat con uno mismo y no molesta a nadie.
#
# OJO: LA PC TIENE QUE ESTAR DESBLOQUEADA
#   Con la sesión de Windows bloqueada, Chrome deja de dibujar las páginas y
#   Telegram Web queda en blanco: el robot no encuentra nada. Pasa con
#   cualquier RPA que maneje la pantalla, igual que le pasaría a una persona.

import os
import platform
import sys
import urllib.parse
from pathlib import Path

import rpa as r

RAIZ = Path(__file__).resolve().parent.parent
CAPTURA = RAIZ / "captura.png"

# Todo lo que depende del diseño de la página de Telegram está acá arriba: si
# Telegram cambia su web y el robot deja de encontrar algo, se corrige acá.
URL_TELEGRAM = "https://web.telegram.org/a/"
BUSCADOR = '//input[@id="telegram-search-input"]'
ID_CAJA_DE_MENSAJE = "editable-message-text"
CAJA_DE_MENSAJE = f'//div[@id="{ID_CAJA_DE_MENSAJE}"]'
CAJA_DE_MENSAJE_ACTIVA = f'{CAJA_DE_MENSAJE}[@aria-disabled="false"]'
BOTON_ENVIAR = '//button[contains(@class,"send") and contains(@class,"main-button")]'
# la columna del chat abierto: la captura se recorta a esto para no mostrar
# la lista de chats de la persona (nombres y vistas previas de otros mensajes)
COLUMNA_DEL_CHAT = '//div[@id="MiddleColumn"]'

MAYUSCULAS = "ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÜÑ"
MINUSCULAS = "abcdefghijklmnopqrstuvwxyzáéíóúüñ"


def _resultado_de_busqueda(nombre_chat):
    # El buscador de Telegram muestra dos secciones: tus chats ("Chats and
    # Contacts") y la búsqueda global, con canales y bots públicos de
    # desconocidos que pueden llamarse igual que tu grupo. Solo se acepta un
    # resultado de una sección cuyo título NO diga "global" ("Global Search",
    # "Búsqueda global"): así el robot nunca le escribe a un extraño.
    # El nombre se compara sin importar mayúsculas ("autobot" = "Autobot").
    nombre = " ".join(nombre_chat.split()).lower()
    return (
        '//div[contains(@class,"search-section")]'
        '[h3[contains(@class,"section-heading")][not(contains(translate(.,"G","g"),"global"))]]'
        '//div[contains(@class,"search-result")]'
        '//h3[contains(@class,"fullName")]'
        f'[translate(normalize-space(.),"{MAYUSCULAS}","{MINUSCULAS}")="{nombre}"]'
    )


class ErrorDelRobot(Exception):
    """El robot no pudo completar algún paso en Telegram Web."""


def _iniciar_tagui():
    # El motor antiguo de TagUI no entiende algunas directivas OpenSSL de Ubuntu.
    if platform.system() != "Linux":
        return r.init()

    openssl_conf = os.environ.get("OPENSSL_CONF")
    os.environ["OPENSSL_CONF"] = os.devnull
    try:
        return r.init()
    finally:
        if openssl_conf is None:
            os.environ.pop("OPENSSL_CONF", None)
        else:
            os.environ["OPENSSL_CONF"] = openssl_conf


def _esperar(elemento, segundos):
    # Se fija una vez por segundo si el elemento ya está en la página. Se hace
    # a mano con present() (que mira una sola vez) porque la espera propia de
    # exist() no resultó confiable en las pruebas.
    for _ in range(int(segundos)):
        if r.present(elemento):
            return True
        r.wait(1)
    return r.present(elemento)


def _abrir_telegram(segundos_para_iniciar_sesion):
    r.url(URL_TELEGRAM)
    if _esperar(BUSCADOR, 15):
        r.wait(3)  # que Telegram termine de cargar los chats antes de buscar
        return
    print("No hay sesión iniciada en Telegram Web.")
    print("Escaneá el QR que aparece en Chrome con el celular:")
    print("Telegram > Ajustes > Dispositivos > Vincular dispositivo")
    if not _esperar(BUSCADOR, segundos_para_iniciar_sesion):
        raise ErrorDelRobot(
            "no hay sesión iniciada en Telegram Web. Corré a mano "
            "`py robot_telegram_web.py` y escaneá el QR con el celular"
        )
    r.wait(3)


def _renglones(texto):
    return [renglon.strip() for renglon in texto.splitlines() if renglon.strip()]


def _abrir_chat(nombre_chat):
    # Telegram Web a veces redibuja el panel de búsqueda mientras termina de
    # cargar y se pierde lo tipeado: por eso se reintenta la búsqueda y el click.
    resultado = _resultado_de_busqueda(nombre_chat)
    for _ in range(3):
        r.click(BUSCADOR)
        r.wait(1)
        # [clear] borra lo que hubiera escrito antes en el buscador
        r.type(BUSCADOR, "[clear]" + nombre_chat)
        if _esperar(resultado, 8):
            break
    else:
        raise ErrorDelRobot(
            f"no encontré el chat «{nombre_chat}» entre tus chats de Telegram Web. "
            "Revisá que GRUPO_TELEGRAM en config.txt tenga el nombre exacto del grupo"
        )
    for _ in range(2):
        r.wait(1)  # que termine la animación de la lista antes de hacer click
        r.click(resultado)
        if _esperar(CAJA_DE_MENSAJE_ACTIVA, 8):
            return
    raise ErrorDelRobot(
        f"abrí «{nombre_chat}» pero no encontré dónde escribir. ¿La cuenta "
        "tiene permiso para escribir en ese grupo?"
    )


def _pegar_mensaje(mensaje):
    # TagUI convierte cada salto de línea en la tecla Enter, y en Telegram
    # Enter envía: tipeada letra por letra, la lista saldría en un mensaje por
    # renglón. Por eso se PEGA entera en la caja de mensaje, como haría una
    # persona con Ctrl+V. El texto viaja codificado (%20, %0A...) para que
    # ningún carácter se rompa en el camino de Python a TagUI y a Chrome.
    texto = urllib.parse.quote(mensaje)
    pegado = r.dom(
        f'var caja = document.getElementById("{ID_CAJA_DE_MENSAJE}"); caja.focus(); '
        f'document.execCommand("insertText", false, decodeURIComponent("{texto}")); '
        "return caja.innerText"
    )
    if _renglones(pegado) != _renglones(mensaje):
        raise ErrorDelRobot("no pude pegar la lista en la caja de mensaje")


def _enviar():
    r.click(BOTON_ENVIAR)
    # cuando el mensaje sale, la caja de mensaje queda vacía
    for _ in range(10):
        r.wait(1)
        if r.dom(f'return document.getElementById("{ID_CAJA_DE_MENSAJE}").innerText.trim()') == "":
            return
    raise ErrorDelRobot("hice click en enviar pero el mensaje quedó sin salir")


def _escribir_y_enviar(mensaje):
    _pegar_mensaje(mensaje)
    _enviar()
    r.wait(2)  # para que la captura muestre el mensaje ya enviado


def _sacar_captura():
    # Si no encuentra la columna del chat no saca nada (antes que mostrar la
    # pantalla entera): el bot confirma igual, solo que sin foto.
    if r.present(COLUMNA_DEL_CHAT):
        r.snap(COLUMNA_DEL_CHAT, str(CAPTURA))


def enviar_por_telegram_web(nombre_chat, mensaje, segundos_para_iniciar_sesion=20):
    """
    Abre Telegram Web, busca `nombre_chat`, le escribe `mensaje` y lo envía.
    Deja una captura de pantalla en captura.png y devuelve su ruta.
    Si algo falla lanza ErrorDelRobot con una explicación.
    """
    if not _iniciar_tagui():
        raise ErrorDelRobot("no se pudo iniciar TagUI ni abrir Chrome")
    try:
        _abrir_telegram(segundos_para_iniciar_sesion)
        _abrir_chat(nombre_chat)
        _escribir_y_enviar(mensaje)
        _sacar_captura()
        return CAPTURA
    finally:
        r.close()


def _iniciar_sesion_y_probar(nombre_chat=None):
    if not _iniciar_tagui():
        raise SystemExit("No se pudo iniciar TagUI ni abrir Chrome.")
    try:
        _abrir_telegram(segundos_para_iniciar_sesion=180)
        print("OK - hay sesión iniciada en Telegram Web.")
        if nombre_chat:
            _abrir_chat(nombre_chat)
            _escribir_y_enviar("Prueba del robot de compras - Grupo 13\nsegunda línea\ntercera línea")
            _sacar_captura()
            print(f"OK - mensaje de prueba enviado a «{nombre_chat}». Captura: {CAPTURA}")
    except ErrorDelRobot as error:
        print(f"FALLO: {error}")
    finally:
        r.close()


def terminar_procesos_tagui():
    """Cierra TagUI y su Chrome si quedaron colgados (lo mismo que hace rpa al iniciar)."""
    carpeta = "tagui" if platform.system() == "Windows" else ".tagui"
    script = Path(r.tagui_location()) / carpeta / "src" / "end_processes"
    os.system(f'"{script}"')


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--enviar":
        # Modo que usa bot.py: el nombre del chat viene como parámetro y el
        # mensaje por la entrada estándar. Si falla, la explicación sale por
        # la salida de errores y el programa termina con código 2.
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
        try:
            enviar_por_telegram_web(sys.argv[2], sys.stdin.read())
        except ErrorDelRobot as error:
            print(error, file=sys.stderr)
            sys.exit(2)
    else:
        _iniciar_sesion_y_probar(sys.argv[1] if len(sys.argv) > 1 else None)

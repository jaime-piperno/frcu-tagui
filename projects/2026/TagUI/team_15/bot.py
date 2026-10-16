import logging
import msvcrt
import os
import subprocess
import sys
import time
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import config
from llm_parser import interpretar
from excel_manager import ExcelManager
from tagui_dashboard import generar_dashboard
from categorias import MONEDAS, CATEGORIAS
import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

excel = ExcelManager(config.GOOGLE_SHEET_ID, str(config.RUTA_CREDENCIALES))

SÍ, NO = "✅ Sí, guardar", "❌ No, cancelar"
EDITAR_MONEDA = "✏️ Editar Moneda"
EDITAR_CATEGORIA = "✏️ Editar Categoría"
EDITAR_FECHA = "📅 Editar Fecha"
EDITAR_DESCRIPCION = "📝 Editar Descripción"


TECLADO = ReplyKeyboardMarkup([[SÍ, NO], [EDITAR_MONEDA, EDITAR_CATEGORIA], [EDITAR_FECHA, EDITAR_DESCRIPCION]], resize_keyboard=True)

PENDIENTES: dict = {}
ESTADOS_EDICION: dict = {}

ESTADO_FILE = config.BASE_DIR / "estado_bot.txt"


def _leer_estado() -> bool:
    try:
        return Path(ESTADO_FILE).read_text(encoding="utf-8").strip() == "1"
    except FileNotFoundError:
        return True


def _guardar_estado(encendido: bool) -> None:
    Path(ESTADO_FILE).write_text("1" if encendido else "0", encoding="utf-8")


ENCENDIDO = _leer_estado()


def _estado_texto() -> str:
    return "🟢 ENCENDIDO" if ENCENDIDO else "🔴 APAGADO"


async def _responder(update: Update, texto: str) -> None:
    try:
        await update.message.reply_text(texto)
    except Exception as e:
        logger.error(f"Error enviando respuesta: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _responder(
        update,
        "Hola 👋 Soy tu asistente de gastos.\n\n"
        f"Estado: {_estado_texto()}\n\n"
        "Enviame el gasto como quieras, por ejemplo:\n"
        "• \"almuerzo 4500\"\n"
        "• \"$3200 uber al aeropuerto\"\n"
        "• \"netflix 1500 usd\"\n\n"
        "Comandos:\n"
        "/encender — activar el bot\n"
        "/apagar — apagar el bot\n"
        "/reporte — generar dashboard en Google Sheets\n"
        "/cancelar — cancelar gasto pendiente",
    )


async def _pedir_confirmacion(update: Update, gastos: list, titulo: str = "📋 Esto es lo que entendí:") -> None:
    resumen = _generar_texto_resumen(gastos)
    mensaje = f"{titulo}\n\n{resumen}\n\n¿Es correcto?\n*(Puedes editar la Fecha, Categoría, Descripción y Moneda)*"
    await update.message.reply_text(mensaje, reply_markup=TECLADO, parse_mode="Markdown")


def _generar_texto_resumen(gastos) -> str:
    if len(gastos) == 1:
        return gastos[0].resumen()
    return "\n".join(
        f"{i + 1}. {g.categoria} — {g.descripcion} — {g.monto:,.2f} {g.moneda} — {g.fecha}"
        for i, g in enumerate(gastos)
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not ENCENDIDO:
        await _responder(
            update,
            "🔴 Estoy apagado. Enviá /encender para activarme.",
        )
        return
    
    chat_id = update.effective_chat.id
    texto = update.message.text.strip()

    if chat_id in ESTADOS_EDICION:
        await _manejar_edicion(update, texto)
        return

    if chat_id in PENDIENTES:
        await _manejar_confirmacion(update, texto)
        return

    if texto in (SÍ, NO):
        await update.message.reply_text("No hay ningún gasto pendiente. Enviá uno nuevo.")
        return

    try:
        gastos = interpretar(texto)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return
    except RuntimeError as e:
        logger.error("Configuración de IA incompleta: %s", e)
        await update.message.reply_text(str(e))
        return
    except Exception:
        logger.exception("Gemini no pudo interpretar el mensaje")
        await update.message.reply_text(
            "⚠️ No pude interpretar tu mensaje en este momento "
            "(la IA está temporalmente no disponible). "
            "Intentá de nuevo en unos minutos."
        )
        return
    gastos = [g for g in gastos if g.monto > 0 and g.descripcion.strip()]

    vistos = set()
    unicos = []
    for g in gastos:
        clave = (g.descripcion.strip().lower(), round(g.monto, 2), g.moneda, g.categoria, g.fecha)
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(g)
    gastos = unicos

    if not gastos:
        await update.message.reply_text(
            "No pude identificar un monto válido en tu mensaje.\n"
            "Intentá de nuevo, por ejemplo: \"almuerzo 4500\"."
        )
        return

    PENDIENTES[chat_id] = gastos

    await _pedir_confirmacion(update, gastos)


async def _manejar_confirmacion(update: Update, texto: str) -> None:
    chat_id = update.effective_chat.id
    
    match texto:
        case "✅ Sí, guardar":
            gastos = PENDIENTES.pop(chat_id)
            for g in gastos:
                excel.registrar(g)
            _actualizar_dashboard_silencioso()
            
            resumen = _generar_texto_resumen(gastos)
            await update.message.reply_text(
                f"✅ {len(gastos)} gasto(s) guardado(s):\n\n{resumen}",
                reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True),
            )
            await update.message.reply_text("Enviá otro gasto o usá /reporte.")

        case "❌ No, cancelar":
            PENDIENTES.pop(chat_id, None)
            await update.message.reply_text(
                "❌ Gasto cancelado. Enviá uno nuevo o /cancelar.",
                reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True),
            )

        case "✏️ Editar Moneda":
            ESTADOS_EDICION[chat_id] = "moneda"
            botones = [[m] for m in MONEDAS] + [["⬅️ Cancelar edición"]]
            await update.message.reply_text(f"Elegí la moneda correcta: {', '.join(MONEDAS)}", reply_markup=ReplyKeyboardMarkup(botones, resize_keyboard=True))

        case "✏️ Editar Categoría":
            ESTADOS_EDICION[chat_id] = "categoria"
            botones = [[c] for c in CATEGORIAS] + [["⬅️ Cancelar edición"]]
            await update.message.reply_text(f"Elegí la categoría correcta: {', '.join(CATEGORIAS)}", reply_markup=ReplyKeyboardMarkup(botones, resize_keyboard=True))

        case "📅 Editar Fecha":
            ESTADOS_EDICION[chat_id] = "fecha"
            await update.message.reply_text("Escribí la fecha en formato AAAA-MM-DD (ej: 2024-05-15):", reply_markup=ReplyKeyboardMarkup([["⬅️ Cancelar edición"]], resize_keyboard=True))

        case "📝 Editar Descripción":
            ESTADOS_EDICION[chat_id] = "descripcion"
            await update.message.reply_text("Escribí la descripción del gasto:", reply_markup=ReplyKeyboardMarkup([["⬅️ Cancelar edición"]], resize_keyboard=True))

        case _:
            # El "case _" es el "default" del switch (si no coincide con nada de arriba)
            await update.message.reply_text(
                "Respondé usando los botones del teclado para confirmar el gasto.",
                reply_markup=TECLADO,
            )

async def _repreguntar_confirmacion(update: Update) -> None:
    chat_id = update.effective_chat.id
    gastos = PENDIENTES.get(chat_id)
    if not gastos:
        return
    await _pedir_confirmacion(update, gastos, titulo="📋 Resumen actualizado:")

async def _manejar_edicion(update: Update, texto: str) -> None:
    chat_id = update.effective_chat.id
    estado = ESTADOS_EDICION.pop(chat_id, None)
    
    if texto == "⬅️ Cancelar edición":
        await _repreguntar_confirmacion(update)
        return
        
    gastos = PENDIENTES.get(chat_id)
    if not gastos:
        return
        
    if estado == "moneda":
        texto_upper = texto.upper()
        if texto_upper in MONEDAS:
            for g in gastos:
                g.moneda = texto_upper
            await update.message.reply_text(f"✅ Moneda actualizada a {texto_upper}.")
        else:
            await update.message.reply_text("❌ Moneda no válida.")
            
    elif estado == "categoria":
        texto_lower = texto.lower()
        if texto_lower in CATEGORIAS:
            for g in gastos:
                g.categoria = texto_lower
            await update.message.reply_text(f"✅ Categoría actualizada a {texto_lower}.")
        else:
            await update.message.reply_text("❌ Categoría no válida.")
            
    elif estado == "fecha":
        try:
            # Validamos que sea una fecha real usando la librería datetime
            datetime.date.fromisoformat(texto)
            for g in gastos:
                g.fecha = texto
            await update.message.reply_text(f"✅ Fecha actualizada a {texto}.")
        except ValueError:
            await update.message.reply_text("❌ Formato incorrecto. Debía ser AAAA-MM-DD.")
            
    elif estado == "descripcion":
        for g in gastos:
            g.descripcion = texto
        await update.message.reply_text("✅ Descripción actualizada.")
            
    await _repreguntar_confirmacion(update)

async def reporte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if chat_id in PENDIENTES:
        await _responder(update, "Hay un gasto pendiente de confirmación. Confirmalo o cancelalo primero.")
        return
    try:
        _actualizar_dashboard_silencioso()
        _abrir_dashboard_tagui()
        await _responder(
            update,
            "📊 Dashboard listo y abierto en tu PC.\n"
            f"Google Sheets: {config.URL_DASHBOARD}\n\n"
            "Los reportes anteriores en este chat siguen disponibles "
            "(tocá el archivo en el historial para verlos).",
        )
    except Exception as e:
        logger.exception("Error al abrir dashboard")
        await _responder(update, f"⚠️ No se pudo abrir el dashboard: {e}")


def _actualizar_dashboard_silencioso() -> None:
    try:
        generar_dashboard(config.GOOGLE_SHEET_ID, str(config.RUTA_CREDENCIALES))
    except Exception:
        logger.exception("Error actualizando dashboard")


def _abrir_dashboard_tagui() -> None:
    try:
        tag = config.BASE_DIR / "tagui" / "abrir_dashboard.tag"
        tag.write_text(
            "// Abre el dashboard de gastos en Google Sheets (rol RPA de TagUI)\n"
            "// En esta build de TagUI la navegación se indica con la URL en su propia línea.\n\n"
            f"{config.URL_DASHBOARD}\n\n"
            "wait 5\n",
            encoding="utf-8",
        )
        subprocess.Popen(
            ["cmd", "/c", "tagui abrir_dashboard.tag"],
            cwd=str(config.BASE_DIR / "tagui"),
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except Exception:
        logger.exception("No se pudo abrir el dashboard con TagUI")


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    PENDIENTES.pop(chat_id, None)
    await _responder(update, "Sesión limpia. Enviá un gasto cuando quieras.")


async def _cambiar_estado_bot(update: Update, activar: bool, msg_ya_estaba: str, msg_exito: str) -> None:
    global ENCENDIDO
    if ENCENDIDO == activar:
        await _responder(update, msg_ya_estaba)
        return
    ENCENDIDO = activar
    _guardar_estado(activar)
    await _responder(update, msg_exito)


async def encender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _cambiar_estado_bot(
        update, True, 
        "🟢 Ya estoy encendido.", 
        "🟢 Bot encendido. Enviame tus gastos."
    )


async def apagar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _cambiar_estado_bot(
        update, False, 
        "🔴 Ya estoy apagado.", 
        "🔴 Bot apagado. Enviá /encender para reactivarme."
    )


def _intentar_bloquear(fd: int) -> bool:
    os.lseek(fd, 0, os.SEEK_SET)
    try:
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        return True
    except OSError:
        return False


def _cerrar_instancias_anteriores() -> None:
    """Mata otras instancias de bot.py (viejas o duplicadas) antes de arrancar."""
    ps = (
        "(Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'bot\\.py' } | "
        "Select-Object -ExpandProperty ProcessId) -join ' '"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        logger.exception("No se pudo listar procesos para reemplazar el bot")
        return
    for pid in [int(x) for x in (proc.stdout or "").split() if x.isdigit()]:
        if pid == os.getpid():
            continue
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True, text=True, timeout=10,
            )
            logger.info(f"Instancia anterior del bot finalizada (PID {pid}).")
        except Exception:
            logger.exception(f"No se pudo matar la instancia anterior (PID {pid})")


def _adquirir_lock_instancia() -> None:
    """Autorreemplazo: cierra la instancia vieja que esté corriendo y arranca la nueva."""
    _cerrar_instancias_anteriores()

    lock_path = config.BASE_DIR / "bot.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    try:
        for _ in range(30):
            if _intentar_bloquear(fd):
                break
            time.sleep(0.2)
        else:
            logger.error(
                "Ya hay otra instancia del bot que no se pudo cerrar. "
                "Cerrala a mano y volvé a iniciar."
            )
            os.close(fd)
            sys.exit(1)
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, str(os.getpid()).encode())
        os.lseek(fd, 0, os.SEEK_SET)
    except OSError:
        os.close(fd)
        logger.error("Error al iniciar el bot (lock).")
        sys.exit(1)


def main() -> None:
    if not config.TOKEN_TELEGRAM:
        logger.error("No se encontró TELEGRAM_TOKEN en .env")
        return

    _adquirir_lock_instancia()

    app = ApplicationBuilder().token(config.TOKEN_TELEGRAM).read_timeout(30).connect_timeout(30).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reporte", reporte))
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(CommandHandler("encender", encender))
    app.add_handler(CommandHandler("apagar", apagar))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info(f"Bot iniciado. Estado: {_estado_texto()}")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

"""
Bot de Telegram para la Conciliación Automatizada de Mercado Pago.

- Recibe el extracto 'MP YYYY-MM (M).xlsx', lo concilia a través de la API y devuelve
  las métricas de la corrida junto con el Excel conciliado (y botones para PDF/CSV).
- Envía alertas cuando quedan cargos sin conciliar o el control de cuadre detecta diferencias.
- Consulta el historial por mes, rango de meses o intervalo de fechas, y las últimas corridas.
- Autorización: administradores definidos en ALLOWED_CHAT_IDS y usuarios vinculados con /vincular CODIGO.

Configuración (variables de entorno o archivo .env):
    TELEGRAM_TOKEN      Token entregado por @BotFather.
    ALLOWED_CHAT_IDS    chat_id de los administradores, separados por coma.
    API_URL             URL de la API de conciliación (default http://localhost:8000).
    API_KEY             Clave interna compartida con la API (habilita la vinculación de usuarios).
"""
from __future__ import annotations

import html
import logging
import os
import re
import sys
import time
from collections import defaultdict, deque
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


from entorno import cargar_env

cargar_env()

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(name)s: %(message)s', level=logging.INFO)
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger('bot_conciliador')

TOKEN = os.getenv('TELEGRAM_TOKEN', '').strip()
API_URL = os.getenv('API_URL', 'http://localhost:8000').strip().rstrip('/')
API_KEY = os.getenv('API_KEY', '').strip()
ADMIN_CHAT_IDS = {
    int(x) for x in re.split(r'[,\s;]+', os.getenv('ALLOWED_CHAT_IDS', '').strip()) if x.lstrip('-').isdigit()
}
ZONA_HORARIA = os.getenv('TZ', 'America/Argentina/Buenos_Aires')

TIMEOUT_API = httpx.Timeout(180.0, connect=10.0)
MAX_TAMANIO_ARCHIVO = 20 * 1024 * 1024  # Límite de descarga de archivos de la Bot API de Telegram
MAX_PENDIENTES_ALERTA = 10
MAX_DIAS_EN_MENSAJE = 10
MAX_INTENTOS_VINCULAR = 5
VENTANA_INTENTOS_SEG = 15 * 60
PATRON_PERIODO = re.compile(r'20\d{2}-(0[1-9]|1[0-2])')
PATRON_FECHA = re.compile(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})')
MIME_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
CLAVE_ARCHIVO_PENDIENTE = 'archivo_sin_periodo'
PATRON_NOMBRE_ARCHIVO = re.compile(r'filename="?([^";]+)"?')
CONECTORES_RANGO = {'a', 'al', 'hasta', '-', 'y'}
ETIQUETAS_EXPORTACION = {
    'pdf': '📄 PDF',
    'csv': '🧾 CSV',
    'csv-pendientes': '🧾 CSV pendientes',
}

# Usuarios vinculados confirmados por la API (caché en memoria del proceso)
USUARIOS_VINCULADOS: set[int] = set()
# Intentos fallidos de /vincular por chat: timestamps
INTENTOS_FALLIDOS: dict[int, deque] = defaultdict(deque)


class ErrorAPI(Exception):
    """Error devuelto por la API de conciliación o de comunicación con ella."""

    def __init__(self, mensaje: str, status: int | None = None):
        super().__init__(mensaje)
        self.status = status


def hoy() -> date:
    try:
        return datetime.now(ZoneInfo(ZONA_HORARIA)).date()
    except ZoneInfoNotFoundError:
        return date.today()


# ---------------------------------------------------------------------------
# Formato
# ---------------------------------------------------------------------------

def pesos(valor) -> str:
    """Formatea un importe al estilo argentino: $ 1.234.567,89 (con signo si es negativo)."""
    numero = float(valor or 0)
    texto = f'{abs(numero):,.2f}'.replace(',', '#').replace('.', ',').replace('#', '.')
    return f'-$ {texto}' if numero < 0 else f'$ {texto}'


def entero(valor) -> str:
    return f'{int(valor or 0):,}'.replace(',', '.')


def porcentaje(valor) -> str:
    return f'{float(valor or 0):.2f}'.replace('.', ',') + ' %'


def esc(texto) -> str:
    return html.escape(str(texto), quote=False)


def fecha_corta(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime('%d/%m/%Y %H:%M')
    except (TypeError, ValueError):
        return str(iso)


def fecha_dia(iso: str) -> str:
    try:
        return datetime.strptime(iso, '%Y-%m-%d').strftime('%d/%m/%Y')
    except (TypeError, ValueError):
        return str(iso)


def texto_ayuda(chat_id: int | None = None, es_admin: bool = False) -> str:
    lineas = [
        '<b>🤖 Conciliador RPA – Mercado Pago</b>',
        '',
        '<b>Conciliar un mes</b>',
        'Enviame el extracto descargado de Mercado Pago (<code>MP YYYY-MM (M).xlsx</code>) como archivo.',
        'Si el nombre no tiene el período, escribilo en el comentario del archivo (ej. <code>2025-10</code>) o te lo pregunto.',
        '',
        '<b>Resúmenes</b>',
        '/resumen <code>2025-10</code> – un mes',
        '/resumen <code>2025-09 2025-12</code> – un rango de meses',
        '/resumen <code>01-11-2025 a 15-11-2025</code> – un intervalo de fechas',
        '/resumen <code>01-11-2025</code> – un día',
        '/resumen <code>actual</code> · /resumen <code>anterior</code> – mes en curso o mes anterior',
        '/historial <code>[n]</code> – últimas corridas registradas (por defecto 10)',
        '',
        '<b>Exportar</b>',
        'Debajo del Excel conciliado y de cada /resumen aparecen botones para descargar en PDF o CSV.',
        'Los archivos de una conciliación quedan disponibles durante 1 hora.',
        '',
        '<b>Cuenta</b>',
        '/vincular <code>CODIGO</code> – vincular esta cuenta con el código de acceso',
        '/desvincular – quitar el acceso de esta cuenta',
        '/cancelar – descarta un archivo que quedó esperando el período',
        '/ayuda – este mensaje',
    ]
    if es_admin:
        lineas += [
            '',
            '<b>Administración</b>',
            '/usuarios – usuarios vinculados',
            '/revocar <code>CHAT_ID</code> – quitar el acceso a un usuario',
        ]
    if chat_id is not None:
        lineas += ['', f'Tu chat_id: <code>{chat_id}</code>' + (' (administrador)' if es_admin else '')]
    return '\n'.join(lineas)


def formatear_resultado(r: dict) -> str:
    m = r['metricas']
    cuadre = m['cuadre']
    ret = m['totales_retenciones']
    estado = '✅' if cuadre['ok'] and m['cargos_pendientes'] == 0 else '⚠️'
    lineas = [
        f"{estado} <b>Conciliación {esc(r['periodo'])}</b>",
        f"📄 {esc(r['nombre_archivo'])}",
        '',
        f"Movimientos: <b>{entero(m['movimientos_totales'])}</b>",
        f"Cargos asociados: <b>{entero(m['cargos_asociados'])}</b> de {entero(m['cargos_totales'])} ({porcentaje(m['porcentaje_asociado'])})",
        f"No conciliado: <b>{pesos(m['monto_pendiente'])}</b> ({entero(m['cargos_pendientes'])} cargos)",
        '',
        f"Ingresos: {pesos(m['ingresos'])}",
        f"Egresos: {pesos(m['egresos'])}",
        f"Balance: <b>{pesos(m['balance'])}</b>",
        '',
        '<b>Retenciones y gastos del extracto</b>',
        f"SIRCUPA {pesos(ret['sircupa'])} · SIRTAC {pesos(ret['sirtac'])}",
        f"IDC {pesos(ret['idc'])} · Gastos {pesos(ret['gastos'])}",
        '',
        (
            f"Cuadre: {'✔ OK' if cuadre['ok'] else '✖ CON DIFERENCIAS'} "
            f"(diferencia {pesos(cuadre['diferencia'])}; "
            f"{entero(cuadre['filas_validadas'])} filas validadas, {entero(cuadre['filas_con_error'])} con error)"
        ),
    ]
    if not r.get('historial_guardado', True):
        lineas += ['', '⚠️ La corrida no pudo guardarse en el historial.']
    return '\n'.join(lineas)


def describir_autor(corrida: dict | None) -> str:
    """Texto 'por Usuario (canal)' para una corrida o corrida anterior."""
    if not corrida:
        return ''
    usuario = corrida.get('usuario')
    canal = corrida.get('canal') or ''
    return f'por {usuario} · {canal}' if usuario else f'desde {canal}'


def totales_coinciden(anterior: dict, r: dict) -> bool:
    """Compara los totales principales de la corrida anterior con los de la actual."""
    m = r['metricas']
    return (
        int(anterior['movimientos']) == int(m['movimientos_totales'])
        and round(float(anterior['balance']), 2) == round(float(m['balance']), 2)
        and round(float(anterior['monto_pendiente']), 2) == round(float(m['monto_pendiente']), 2)
    )


def formatear_comparacion(r: dict) -> str | None:
    """Aviso para quien concilió: extracto idéntico al ya procesado o con datos que reemplazan a los anteriores."""
    comp = r.get('comparacion') or {}
    estado = comp.get('estado')
    ant = comp.get('corrida_anterior')
    if not ant or estado in (None, 'nuevo'):
        return None
    cuando = f"{fecha_corta(ant['fecha_ejecucion'])} {describir_autor(ant)}"
    if estado == 'identico':
        return (
            f"ℹ️ <b>Este extracto ya se había procesado</b> (corrida #{ant['id']}, {esc(cuando)}).\n"
            'Los datos son idénticos: los resultados y los resúmenes no cambian.'
        )
    m = r['metricas']
    if estado == 'sin_huella' and totales_coinciden(ant, r):
        return (
            f"ℹ️ <b>{esc(r['periodo'])} ya tenía una corrida</b> (#{ant['id']}, {esc(cuando)}).\n"
            'Es anterior a la detección de extractos repetidos, así que no se puede verificar si es el mismo archivo, '
            'pero los totales coinciden.'
        )
    motivo = 'con datos distintos' if estado == 'distinto' else 'que no tiene huella para comparar'
    return (
        f"⚠️ <b>Reemplaza a la corrida anterior de {esc(r['periodo'])}</b> (#{ant['id']}, {esc(cuando)}), {motivo}.\n"
        'Desde ahora los resúmenes de ese mes usan esta corrida.\n\n'
        f"Movimientos: {entero(ant['movimientos'])} → <b>{entero(m['movimientos_totales'])}</b>\n"
        f"Balance: {pesos(ant['balance'])} → <b>{pesos(m['balance'])}</b>\n"
        f"No conciliado: {pesos(ant['monto_pendiente'])} → <b>{pesos(m['monto_pendiente'])}</b>"
    )


def formatear_aviso_admin(r: dict, autor: str) -> str:
    """Notificación para los administradores cuando otro usuario concilia un mes."""
    m = r['metricas']
    cuadre = m['cuadre']
    comp = r.get('comparacion') or {}
    estado = comp.get('estado')
    ant = comp.get('corrida_anterior')
    if estado == 'identico' and ant:
        situacion = f"Mismo extracto que la corrida #{ant['id']}: los datos no cambian."
    elif estado == 'sin_huella' and ant and totales_coinciden(ant, r):
        situacion = f"Reprocesó el mes; la corrida anterior (#{ant['id']}) no tiene huella, pero los totales coinciden."
    elif estado in ('distinto', 'sin_huella') and ant:
        situacion = (
            f"⚠️ Reemplazó a la corrida #{ant['id']} ({fecha_corta(ant['fecha_ejecucion'])} {describir_autor(ant)})"
            f"{' con datos distintos' if estado == 'distinto' else ''}. "
            f"Balance {pesos(ant['balance'])} → {pesos(m['balance'])}; "
            f"no conciliado {pesos(ant['monto_pendiente'])} → {pesos(m['monto_pendiente'])}."
        )
    else:
        situacion = 'Primera corrida registrada de este mes.'
    return '\n'.join([
        f"🔔 <b>{esc(autor)}</b> concilió <b>{esc(r['periodo'])}</b>",
        f"📄 {esc(r['nombre_archivo'])}",
        '',
        f"Movimientos: {entero(m['movimientos_totales'])} · asociado {porcentaje(m['porcentaje_asociado'])}",
        f"No conciliado: {pesos(m['monto_pendiente'])} ({entero(m['cargos_pendientes'])} cargos)",
        f"Balance: {pesos(m['balance'])}",
        f"Cuadre: {'✔ OK' if cuadre['ok'] else '✖ CON DIFERENCIAS'}",
        '',
        esc(situacion),
    ])


def formatear_alerta_pendientes(r: dict) -> str | None:
    m = r['metricas']
    pendientes = r.get('pendientes') or []
    if not m['cargos_pendientes']:
        return None
    lineas = [
        f"⚠️ <b>Alerta: {entero(m['cargos_pendientes'])} cargos sin conciliar en {esc(r['periodo'])}</b>",
        f"Monto total: <b>{pesos(m['monto_pendiente'])}</b>",
        '',
    ]
    for p in pendientes[:MAX_PENDIENTES_ALERTA]:
        lineas.append(
            f"• {esc(p['hoja'])} <code>{esc(p['id'])}</code> {esc(p['fecha'])} – {pesos(p['importe'])}\n"
            f"  <i>{esc(p['motivo'])}</i>"
        )
    restantes = len(pendientes) - MAX_PENDIENTES_ALERTA
    if restantes > 0:
        lineas.append(f'… y {entero(restantes)} más.')
    lineas += ['', "El detalle completo está en la hoja <b>No Conciliados</b> del Excel."]
    return '\n'.join(lineas)


def formatear_alerta_cuadre(r: dict) -> str | None:
    cuadre = r['metricas']['cuadre']
    if cuadre['ok']:
        return None
    lineas = [f"🚨 <b>Alerta de descuadre en {esc(r['periodo'])}</b>", '']
    for d in cuadre['detalle_por_hoja']:
        if not d['ok']:
            lineas.append(
                f"• {esc(d['hoja'])}: extracto {pesos(d['origen'])}, imputado {pesos(d['imputado'])}, "
                f"no conciliado {pesos(d['pendiente'])} → diferencia <b>{pesos(d['diferencia'])}</b>"
            )
    if cuadre['filas_con_error']:
        lineas.append(f"• {entero(cuadre['filas_con_error'])} filas con MOV TOTAL inconsistente.")
    lineas += ['', "Revisá la hoja <b>Control y Cuadre</b> del Excel."]
    return '\n'.join(lineas)


def formatear_resumen(r: dict) -> str:
    t = r['totales']
    titulo = r['desde'] if r['desde'] == r['hasta'] else f"{r['desde']} a {r['hasta']}"
    lineas = [f'📊 <b>Resumen {esc(titulo)}</b>', '']

    if len(r['meses']) > 1:
        for mes in r['meses']:
            marca = '✔' if mes['cuadre_ok'] and mes['cargos_pendientes'] == 0 else '⚠️'
            lineas.append(
                f"{marca} <b>{esc(mes['periodo'])}</b> · balance {pesos(mes['balance'])} · "
                f"no conciliado {pesos(mes['monto_pendiente'])}"
            )
        lineas.append('')

    lineas += [
        f"Movimientos: <b>{entero(t['movimientos'])}</b>",
        f"Cargos asociados: {entero(t['cargos_asociados'])} de {entero(t['cargos_totales'])} ({porcentaje(t['porcentaje_asociado'])})",
        f"No conciliado: <b>{pesos(t['monto_pendiente'])}</b> ({entero(t['cargos_pendientes'])} cargos)",
        '',
        f"Ingresos: {pesos(t['ingresos'])}",
        f"Egresos: {pesos(t['egresos'])}",
        f"Balance: <b>{pesos(t['balance'])}</b>",
        '',
        f"SIRCUPA {pesos(t['total_sircupa'])} · SIRTAC {pesos(t['total_sirtac'])}",
        f"IDC {pesos(t['total_idc'])} · Gastos {pesos(t['total_gastos'])}",
    ]
    if len(r['meses']) > 1 or t['periodos_con_pendientes'] or t['periodos_descuadrados']:
        lineas += [
            '',
            f"Meses con pendientes: {t['periodos_con_pendientes']} · Meses descuadrados: {t['periodos_descuadrados']}",
        ]
    if r.get('meses_sin_datos'):
        lineas += ['', f"Sin corridas registradas: {esc(', '.join(r['meses_sin_datos']))}"]
    if len(r['meses']) == 1:
        mes = r['meses'][0]
        lineas += ['', f"Última corrida: #{mes['id']} · {fecha_corta(mes['fecha_ejecucion'])} {esc(describir_autor(mes))}"]
    return '\n'.join(lineas)


def formatear_resumen_dias(r: dict) -> str:
    t = r['totales']
    desde, hasta = fecha_dia(r['desde']), fecha_dia(r['hasta'])
    titulo = desde if desde == hasta else f'{desde} al {hasta}'
    retenciones = sum(float(t[k]) for k in ('sircupa', 'sirtac', 'idc', 'gastos'))
    lineas = [
        f'📅 <b>Resumen {esc(titulo)}</b>',
        '',
        f"Movimientos: <b>{entero(t['movimientos'])}</b> "
        f"({entero(t['dias_con_movimientos'])} {'día' if t['dias_con_movimientos'] == 1 else 'días'} con movimientos)",
        f"Ingresos: {pesos(t['ingresos'])}",
        f"Egresos: {pesos(t['egresos'])}",
        f"Balance: <b>{pesos(t['balance'])}</b>",
        f"Suma de MOV TOTAL (bruto): {pesos(t['mov_total'])}",
        '',
        f"<b>Retenciones y gastos imputados:</b> {pesos(retenciones)}",
        f"SIRCUPA {pesos(t['sircupa'])} · SIRTAC {pesos(t['sirtac'])}",
        f"IDC {pesos(t['idc'])} · Gastos {pesos(t['gastos'])}",
        '',
        f"No conciliado (cargos con fecha en el intervalo): <b>{pesos(t['monto_pendiente'])}</b> ({entero(t['cargos_pendientes'])} cargos)",
    ]
    dias = r.get('dias') or []
    if dias and len(dias) <= MAX_DIAS_EN_MENSAJE and len(dias) > 1:
        lineas += ['', '<b>Por día</b>']
        for d in dias:
            marca = ' ⚠️' if d['cargos_pendientes'] else ''
            lineas.append(
                f"{fecha_dia(d['fecha'])} · {entero(d['movimientos'])} mov. · balance {pesos(d['balance'])}{marca}"
            )
    elif len(dias) > MAX_DIAS_EN_MENSAJE:
        lineas += ['', 'El detalle por día está en el PDF y el CSV.']
    if r.get('meses_sin_datos'):
        lineas += ['', f"Sin corridas registradas: {esc(', '.join(r['meses_sin_datos']))}"]
    if r.get('meses_sin_detalle'):
        lineas += ['', f"Sin detalle diario (volvé a procesar el extracto): {esc(', '.join(r['meses_sin_detalle']))}"]
    return '\n'.join(lineas)


def formatear_historial(r: dict) -> str:
    corridas = r.get('corridas') or []
    if not corridas:
        return 'Todavía no hay corridas registradas.'
    lineas = ['🗂 <b>Últimas corridas</b>', '']
    notas = {
        'identico': ' · ↺ mismo extracto',
        'distinto': ' · ⚠️ reemplazó datos',
        'sin_huella': ' · reproceso',
    }
    for c in corridas:
        marca = '✔' if c['cuadre_ok'] and c['cargos_pendientes'] == 0 else '⚠️'
        lineas.append(
            f"{marca} #{c['id']} <b>{esc(c['periodo'])}</b> · {fecha_corta(c['fecha_ejecucion'])} · {esc(describir_autor(c))}\n"
            f"   {entero(c['movimientos'])} mov. · no conciliado {pesos(c['monto_pendiente'])}"
            f"{notas.get(c.get('comparacion'), '')}"
        )
    return '\n'.join(lineas)


def formatear_usuarios(r: dict) -> str:
    usuarios = r.get('usuarios') or []
    lineas = ['👥 <b>Usuarios</b>', '', '<b>Administradores</b> (ALLOWED_CHAT_IDS)']
    lineas += [f'• <code>{i}</code>' for i in sorted(ADMIN_CHAT_IDS)] or ['• (ninguno)']
    lineas += ['', f'<b>Vinculados con código</b> ({len(usuarios)})']
    if not usuarios:
        lineas.append('• (ninguno)')
    for u in usuarios:
        lineas.append(f"• <code>{esc(u['chat_id'])}</code> {esc(u.get('nombre') or '')} · desde {fecha_corta(u['vinculado_en'])}")
    return '\n'.join(lineas)


# ---------------------------------------------------------------------------
# Interpretación de /resumen
# ---------------------------------------------------------------------------

def mes_relativo(desplazamiento: int) -> str:
    referencia = hoy().replace(day=1)
    if desplazamiento == -1:
        referencia = referencia - timedelta(days=1)
    return referencia.strftime('%Y-%m')


def parsear_fecha(texto: str) -> date | None:
    coincidencia = PATRON_FECHA.fullmatch(texto)
    if not coincidencia:
        return None
    dia, mes, anio = (int(x) for x in coincidencia.groups())
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def interpretar_resumen(args: list[str]) -> tuple[str, str, str] | None:
    """
    Devuelve ('meses', desde, hasta) o ('dias', desde_iso, hasta_iso), o None si los argumentos no son válidos.
    Acepta: YYYY-MM [YYYY-MM] · DD-MM-AAAA [a] [DD-MM-AAAA] · actual · anterior.
    """
    tokens = [a.strip().lower() for a in args if a.strip() and a.strip().lower() not in CONECTORES_RANGO]
    if len(tokens) == 1 and tokens[0] in ('actual', 'mes', 'hoy'):
        periodo = mes_relativo(0)
        return 'meses', periodo, periodo
    if len(tokens) == 1 and tokens[0] in ('anterior', 'pasado'):
        periodo = mes_relativo(-1)
        return 'meses', periodo, periodo
    if len(tokens) in (1, 2) and all(PATRON_PERIODO.fullmatch(t) for t in tokens):
        desde, hasta = tokens[0], tokens[-1]
        return ('meses', *sorted((desde, hasta)))
    if len(tokens) in (1, 2):
        fechas = [parsear_fecha(t) for t in tokens]
        if all(fechas):
            desde, hasta = sorted((fechas[0], fechas[-1]))
            return 'dias', desde.isoformat(), hasta.isoformat()
    return None


# ---------------------------------------------------------------------------
# Cliente de la API
# ---------------------------------------------------------------------------

def _encabezados() -> dict:
    return {'X-API-Key': API_KEY} if API_KEY else {}


def _detalle_error(resp: httpx.Response) -> str:
    try:
        detalle = resp.json().get('detail')
    except ValueError:
        detalle = None
    return str(detalle) if detalle else f'Error {resp.status_code} del servidor de conciliación.'


async def _pedir(metodo: str, ruta: str, **kwargs) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_API, headers=_encabezados()) as cliente:
            resp = await cliente.request(metodo, f'{API_URL}{ruta}', **kwargs)
    except httpx.TimeoutException:
        raise ErrorAPI('El servidor de conciliación tardó demasiado en responder.')
    except httpx.HTTPError:
        raise ErrorAPI('No pude conectarme con el servidor de conciliación. ¿Está levantado?')
    if resp.status_code != 200:
        raise ErrorAPI(_detalle_error(resp), resp.status_code)
    return resp


async def api_conciliar(nombre: str, contenido: bytes, periodo: str, chat_id: int, usuario: str) -> dict:
    resp = await _pedir(
        'POST', '/api/conciliar',
        files={'archivo': (nombre, contenido, MIME_XLSX)},
        data={'periodo': periodo, 'canal': 'telegram', 'chat_id': str(chat_id), 'usuario': usuario},
    )
    return resp.json()


def nombre_usuario(update: Update) -> str:
    usuario = update.effective_user
    if usuario is None:
        return str(update.effective_chat.id)
    nombre = usuario.full_name or str(update.effective_chat.id)
    return f'{nombre} (@{usuario.username})' if usuario.username else nombre


async def api_get(ruta: str, params: dict | None = None) -> dict:
    return (await _pedir('GET', ruta, params=params)).json()


async def api_post(ruta: str, data: dict) -> dict:
    return (await _pedir('POST', ruta, data=data)).json()


async def api_archivo(ruta: str, params: dict, nombre_por_defecto: str) -> tuple[str, bytes]:
    """Descarga un archivo de la API y devuelve (nombre, contenido)."""
    resp = await _pedir('GET', ruta, params=params)
    coincidencia = PATRON_NOMBRE_ARCHIVO.search(resp.headers.get('content-disposition', ''))
    return (coincidencia.group(1) if coincidencia else nombre_por_defecto), resp.content


def teclado_conciliacion(token: str, formatos: list[str]) -> InlineKeyboardMarkup | None:
    botones = [
        InlineKeyboardButton(etiqueta, callback_data=f'exp|{token}|{formato}')
        for formato, etiqueta in ETIQUETAS_EXPORTACION.items()
        if formato in formatos
    ]
    return InlineKeyboardMarkup([botones]) if botones else None


def teclado_resumen(prefijo: str, desde: str, hasta: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton('📄 PDF', callback_data=f'{prefijo}|{desde}|{hasta}|pdf'),
        InlineKeyboardButton('🧾 CSV', callback_data=f'{prefijo}|{desde}|{hasta}|csv'),
    ]])


# ---------------------------------------------------------------------------
# Autorización
# ---------------------------------------------------------------------------

def es_admin(chat_id: int) -> bool:
    return chat_id in ADMIN_CHAT_IDS


async def esta_autorizado(chat_id: int) -> bool:
    if chat_id in ADMIN_CHAT_IDS or chat_id in USUARIOS_VINCULADOS:
        return True
    if not API_KEY:
        return False
    try:
        respuesta = await api_get(f'/api/usuarios/{chat_id}')
    except ErrorAPI as e:
        logger.warning('No se pudo verificar el usuario %s: %s', chat_id, e)
        return False
    if respuesta.get('autorizado'):
        USUARIOS_VINCULADOS.add(chat_id)
        return True
    return False


async def autorizado(update: Update) -> bool:
    chat = update.effective_chat
    if chat is not None and await esta_autorizado(chat.id):
        return True
    if chat is not None and update.effective_message is not None:
        logger.warning('Acceso rechazado al chat_id %s', chat.id)
        texto = f'⛔ No estás autorizado para usar este bot.\nTu chat_id es <code>{chat.id}</code>.'
        if API_KEY:
            texto += '\nSi tenés el código de acceso, enviá /vincular <code>CODIGO</code>.'
        else:
            texto += '\nPedile al administrador que lo agregue a ALLOWED_CHAT_IDS.'
        await update.effective_message.reply_text(texto, parse_mode=ParseMode.HTML)
    return False


def _registrar_intento_fallido(chat_id: int) -> int:
    """Registra un intento fallido y devuelve cuántos intentos quedan en la ventana."""
    intentos = INTENTOS_FALLIDOS[chat_id]
    intentos.append(time.monotonic())
    return max(0, MAX_INTENTOS_VINCULAR - len(intentos))


def _bloqueado(chat_id: int) -> bool:
    intentos = INTENTOS_FALLIDOS[chat_id]
    limite = time.monotonic() - VENTANA_INTENTOS_SEG
    while intentos and intentos[0] < limite:
        intentos.popleft()
    return len(intentos) >= MAX_INTENTOS_VINCULAR


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await autorizado(update):
        return
    chat_id = update.effective_chat.id
    await update.effective_message.reply_text(
        texto_ayuda(chat_id, es_admin(chat_id)), parse_mode=ParseMode.HTML
    )


async def cmd_vincular(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensaje = update.effective_message
    chat_id = update.effective_chat.id
    args = context.args or []

    # El mensaje contiene el código: se borra del chat para que no quede visible.
    if args:
        try:
            await mensaje.delete()
        except TelegramError:
            pass

    if es_admin(chat_id):
        await context.bot.send_message(chat_id=chat_id, text='Ya tenés acceso como administrador (ALLOWED_CHAT_IDS).')
        return
    if not API_KEY:
        await context.bot.send_message(
            chat_id=chat_id,
            text='La vinculación por código no está habilitada. Pedile al administrador que agregue tu chat_id.',
        )
        return
    if len(args) != 1:
        await context.bot.send_message(
            chat_id=chat_id, text='Uso: /vincular <code>CODIGO</code>', parse_mode=ParseMode.HTML
        )
        return
    if _bloqueado(chat_id):
        await context.bot.send_message(
            chat_id=chat_id,
            text='⛔ Demasiados intentos fallidos. Esperá 15 minutos antes de volver a intentar.',
        )
        return

    try:
        respuesta = await api_post(
            '/api/usuarios/vincular',
            {'chat_id': str(chat_id), 'codigo': args[0], 'nombre': nombre_usuario(update)},
        )
    except ErrorAPI as e:
        if e.status == 403:
            restantes = _registrar_intento_fallido(chat_id)
            texto = '❌ Código incorrecto.'
            if restantes:
                texto += f" Te {'queda 1 intento' if restantes == 1 else f'quedan {restantes} intentos'}."
            else:
                texto += ' Esperá 15 minutos antes de volver a intentar.'
        else:
            texto = f'❌ {e}'
        await context.bot.send_message(chat_id=chat_id, text=texto)
        return

    INTENTOS_FALLIDOS.pop(chat_id, None)
    USUARIOS_VINCULADOS.add(chat_id)
    estado = 'Tu cuenta ya estaba vinculada.' if respuesta.get('ya_estaba_vinculado') else '✅ Cuenta vinculada.'
    await context.bot.send_message(
        chat_id=chat_id,
        text=f'{estado} Ya podés usar el bot.\n\n{texto_ayuda(chat_id)}',
        parse_mode=ParseMode.HTML,
    )


async def cmd_desvincular(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensaje = update.effective_message
    chat_id = update.effective_chat.id
    if es_admin(chat_id):
        await mensaje.reply_text('Sos administrador: tu acceso se configura en ALLOWED_CHAT_IDS del archivo .env.')
        return
    if not API_KEY:
        await mensaje.reply_text('La vinculación por código no está habilitada.')
        return
    try:
        respuesta = await api_post('/api/usuarios/desvincular', {'chat_id': str(chat_id)})
    except ErrorAPI as e:
        await mensaje.reply_text(f'❌ {e}')
        return
    USUARIOS_VINCULADOS.discard(chat_id)
    if respuesta.get('desvinculado'):
        await mensaje.reply_text('Listo, tu cuenta fue desvinculada. Para volver a usar el bot enviá /vincular CODIGO.')
    else:
        await mensaje.reply_text('Tu cuenta no estaba vinculada.')


async def cmd_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensaje = update.effective_message
    if not es_admin(update.effective_chat.id):
        await mensaje.reply_text('⛔ Este comando es solo para administradores.')
        return
    if not API_KEY:
        await mensaje.reply_text(formatear_usuarios({'usuarios': []}) + '\n\n(Vinculación por código deshabilitada.)',
                                 parse_mode=ParseMode.HTML)
        return
    try:
        respuesta = await api_get('/api/usuarios')
    except ErrorAPI as e:
        await mensaje.reply_text(f'❌ {e}')
        return
    await mensaje.reply_text(formatear_usuarios(respuesta), parse_mode=ParseMode.HTML)


async def cmd_revocar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mensaje = update.effective_message
    if not es_admin(update.effective_chat.id):
        await mensaje.reply_text('⛔ Este comando es solo para administradores.')
        return
    args = context.args or []
    if len(args) != 1 or not args[0].lstrip('-').isdigit():
        await mensaje.reply_text('Uso: /revocar <code>CHAT_ID</code> (ver /usuarios)', parse_mode=ParseMode.HTML)
        return
    objetivo = int(args[0])
    if es_admin(objetivo):
        await mensaje.reply_text('Ese chat_id es administrador: se quita editando ALLOWED_CHAT_IDS en .env.')
        return
    try:
        respuesta = await api_post('/api/usuarios/desvincular', {'chat_id': str(objetivo)})
    except ErrorAPI as e:
        await mensaje.reply_text(f'❌ {e}')
        return
    USUARIOS_VINCULADOS.discard(objetivo)
    if respuesta.get('desvinculado'):
        await mensaje.reply_text(f'Listo, se quitó el acceso a {objetivo}.')
    else:
        await mensaje.reply_text(f'{objetivo} no estaba vinculado.')


async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await autorizado(update):
        return
    if context.user_data.pop(CLAVE_ARCHIVO_PENDIENTE, None):
        await update.effective_message.reply_text('Listo, descarté el archivo pendiente.')
    else:
        await update.effective_message.reply_text('No había ningún archivo esperando el período.')


async def procesar_extracto(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str, nombre: str, periodo: str) -> None:
    mensaje = update.effective_message
    chat_id = update.effective_chat.id
    aviso = await mensaje.reply_text(f'⏳ Conciliando <b>{esc(nombre)}</b> ({esc(periodo)})…', parse_mode=ParseMode.HTML)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)

    autor = nombre_usuario(update)
    try:
        archivo_tg = await context.bot.get_file(file_id)
        contenido = bytes(await archivo_tg.download_as_bytearray())
        resultado = await api_conciliar(nombre, contenido, periodo, chat_id, autor)
        _, excel = await api_archivo(f"/api/descargar/{resultado['descarga_token']}", {}, resultado['archivo_salida'])
    except ErrorAPI as e:
        await aviso.edit_text(f'❌ {esc(e)}', parse_mode=ParseMode.HTML)
        return

    await aviso.edit_text(formatear_resultado(resultado), parse_mode=ParseMode.HTML)
    await context.bot.send_document(
        chat_id=chat_id,
        document=excel,
        filename=resultado['archivo_salida'],
        caption=f"📎 Conciliación {resultado['periodo']}\nExportar en otro formato:",
        reply_markup=teclado_conciliacion(resultado['descarga_token'], resultado.get('exportaciones', [])),
    )

    comparacion = resultado.get('comparacion') or {}
    aviso_comparacion = formatear_comparacion(resultado)
    if aviso_comparacion:
        await context.bot.send_message(chat_id=chat_id, text=aviso_comparacion, parse_mode=ParseMode.HTML)

    # Si este mismo chat ya había procesado exactamente estos datos, no se repite la alerta de pendientes.
    anterior = comparacion.get('corrida_anterior') or {}
    repetido_propio = comparacion.get('estado') == 'identico' and str(anterior.get('chat_id')) == str(chat_id)
    alerta_pendientes = None if repetido_propio else formatear_alerta_pendientes(resultado)
    for alerta in (alerta_pendientes, formatear_alerta_cuadre(resultado)):
        if alerta:
            await context.bot.send_message(chat_id=chat_id, text=alerta, parse_mode=ParseMode.HTML)

    await notificar_administradores(context, resultado, chat_id, autor)


async def notificar_administradores(context: ContextTypes.DEFAULT_TYPE, resultado: dict, chat_origen: int, autor: str) -> None:
    """Avisa a los administradores (salvo a quien concilió) que se procesó un mes."""
    destinatarios = sorted(ADMIN_CHAT_IDS - {chat_origen})
    if not destinatarios:
        return
    texto = formatear_aviso_admin(resultado, autor)
    for admin in destinatarios:
        try:
            await context.bot.send_message(chat_id=admin, text=texto, parse_mode=ParseMode.HTML)
        except TelegramError as e:
            logger.warning('No se pudo notificar al administrador %s: %s', admin, e)


async def recibir_documento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await autorizado(update):
        return
    mensaje = update.effective_message
    doc = mensaje.document
    nombre = doc.file_name or 'extracto.xlsx'

    if not nombre.lower().endswith('.xlsx'):
        await mensaje.reply_text('El archivo tiene que ser un Excel (.xlsx) descargado de Mercado Pago.')
        return
    if doc.file_size and doc.file_size > MAX_TAMANIO_ARCHIVO:
        await mensaje.reply_text('El archivo supera los 20 MB que permite Telegram para bots. Usá la web de conciliación.')
        return

    coincidencia = PATRON_PERIODO.search(mensaje.caption or '') or PATRON_PERIODO.search(nombre)
    if not coincidencia:
        context.user_data[CLAVE_ARCHIVO_PENDIENTE] = {'file_id': doc.file_id, 'nombre': nombre}
        await mensaje.reply_text(
            '¿De qué período es este extracto? Respondé con el formato <code>YYYY-MM</code> (ej. <code>2025-10</code>), '
            'o /cancelar.',
            parse_mode=ParseMode.HTML,
        )
        return

    context.user_data.pop(CLAVE_ARCHIVO_PENDIENTE, None)
    await procesar_extracto(update, context, doc.file_id, nombre, coincidencia.group(0))


async def recibir_texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await autorizado(update):
        return
    mensaje = update.effective_message
    pendiente = context.user_data.get(CLAVE_ARCHIVO_PENDIENTE)
    if pendiente:
        texto = (mensaje.text or '').strip()
        if PATRON_PERIODO.fullmatch(texto):
            context.user_data.pop(CLAVE_ARCHIVO_PENDIENTE, None)
            await procesar_extracto(update, context, pendiente['file_id'], pendiente['nombre'], texto)
        else:
            await mensaje.reply_text(
                'Necesito el período con formato <code>YYYY-MM</code> (ej. <code>2025-10</code>), o /cancelar.',
                parse_mode=ParseMode.HTML,
            )
        return
    await mensaje.reply_text(
        'Enviame el extracto de Mercado Pago (.xlsx) o usá /ayuda para ver los comandos.'
    )


async def cmd_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await autorizado(update):
        return
    mensaje = update.effective_message
    consulta = interpretar_resumen(context.args or [])
    if consulta is None:
        await mensaje.reply_text(
            'Uso:\n'
            '/resumen <code>2025-10</code> – un mes\n'
            '/resumen <code>2025-09 2025-12</code> – rango de meses\n'
            '/resumen <code>01-11-2025 a 15-11-2025</code> – intervalo de fechas\n'
            '/resumen <code>actual</code> · /resumen <code>anterior</code>',
            parse_mode=ParseMode.HTML,
        )
        return

    tipo, desde, hasta = consulta
    try:
        if tipo == 'meses':
            resultado = await api_get('/api/resumen', {'desde': desde, 'hasta': hasta})
            texto, teclado = formatear_resumen(resultado), teclado_resumen('res', resultado['desde'], resultado['hasta'])
        else:
            resultado = await api_get('/api/resumen/dias', {'desde': desde, 'hasta': hasta})
            texto, teclado = formatear_resumen_dias(resultado), teclado_resumen('dia', resultado['desde'], resultado['hasta'])
    except ErrorAPI as e:
        await mensaje.reply_text(f'ℹ️ {esc(e)}', parse_mode=ParseMode.HTML)
        return
    await mensaje.reply_text(texto, parse_mode=ParseMode.HTML, reply_markup=teclado)


async def exportar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Atiende los botones de exportación (PDF/CSV) de conciliaciones y resúmenes."""
    consulta = update.callback_query
    if not await autorizado(update):
        await consulta.answer()
        return

    chat_id = update.effective_chat.id
    partes = (consulta.data or '').split('|')
    try:
        if partes[0] == 'exp' and len(partes) == 3:
            _, token, formato = partes
            await consulta.answer(f'Generando {ETIQUETAS_EXPORTACION.get(formato, formato)}…')
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
            nombre, contenido = await api_archivo(f'/api/descargar/{token}', {'formato': formato}, f'conciliacion.{formato}')
        elif partes[0] in ('res', 'dia') and len(partes) == 4:
            prefijo, desde, hasta, formato = partes
            ruta = '/api/resumen/exportar' if prefijo == 'res' else '/api/resumen/dias/exportar'
            await consulta.answer(f'Generando resumen en {formato.upper()}…')
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_DOCUMENT)
            nombre, contenido = await api_archivo(ruta, {'desde': desde, 'hasta': hasta, 'formato': formato}, f'resumen.{formato}')
        else:
            await consulta.answer('Botón no reconocido.', show_alert=True)
            return
    except ErrorAPI as e:
        texto = str(e)
        if partes[0] == 'exp' and 'expiró' in texto:
            texto += ' Volvé a enviar el extracto para generarlo de nuevo.'
        await context.bot.send_message(chat_id=chat_id, text=f'❌ {esc(texto)}', parse_mode=ParseMode.HTML)
        return

    await context.bot.send_document(chat_id=chat_id, document=contenido, filename=nombre)


async def cmd_historial(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await autorizado(update):
        return
    mensaje = update.effective_message
    args = context.args or []
    limite = 10
    if args:
        if not args[0].isdigit() or not 1 <= int(args[0]) <= 50:
            await mensaje.reply_text('Uso: /historial [n] con n entre 1 y 50.')
            return
        limite = int(args[0])
    try:
        resultado = await api_get('/api/historial', {'limite': limite})
    except ErrorAPI as e:
        await mensaje.reply_text(f'❌ {esc(e)}', parse_mode=ParseMode.HTML)
        return
    await mensaje.reply_text(formatear_historial(resultado), parse_mode=ParseMode.HTML)


async def manejar_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error('Error no controlado procesando una actualización', exc_info=context.error)
    if isinstance(update, Update) and update.effective_message is not None:
        try:
            await update.effective_message.reply_text('❌ Ocurrió un error inesperado. Probá de nuevo en unos minutos.')
        except Exception:
            pass


def construir_aplicacion() -> Application:
    aplicacion = Application.builder().token(TOKEN).build()
    aplicacion.add_handler(CommandHandler(['start', 'ayuda', 'help'], cmd_ayuda))
    aplicacion.add_handler(CommandHandler('resumen', cmd_resumen))
    aplicacion.add_handler(CommandHandler('historial', cmd_historial))
    aplicacion.add_handler(CommandHandler('vincular', cmd_vincular))
    aplicacion.add_handler(CommandHandler('desvincular', cmd_desvincular))
    aplicacion.add_handler(CommandHandler('usuarios', cmd_usuarios))
    aplicacion.add_handler(CommandHandler('revocar', cmd_revocar))
    aplicacion.add_handler(CommandHandler('cancelar', cmd_cancelar))
    aplicacion.add_handler(CallbackQueryHandler(exportar_callback, pattern=r'^(exp|res|dia)\|'))
    aplicacion.add_handler(MessageHandler(filters.Document.ALL, recibir_documento))
    aplicacion.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_texto))
    aplicacion.add_error_handler(manejar_error)
    return aplicacion


def main() -> None:
    if not TOKEN:
        logger.warning('TELEGRAM_TOKEN no está configurado: el bot no se inicia. Completá el archivo .env.')
        sys.exit(0)
    if not ADMIN_CHAT_IDS:
        logger.warning(
            'ALLOWED_CHAT_IDS está vacío: no hay administradores. '
            'Escribile /start al bot para obtener tu chat_id y agregalo al archivo .env.'
        )
    if not API_KEY:
        logger.warning('API_KEY no está configurada: la vinculación por código (/vincular) queda deshabilitada.')
    logger.info('Bot iniciado. API: %s · administradores: %s', API_URL, sorted(ADMIN_CHAT_IDS) or 'ninguno')
    construir_aplicacion().run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == '__main__':
    main()

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from rubros import RUBROS
from opciones import TIPO_PROCESO, ESTADO_PROCESO, TIPO_OPERACION

# búsquedas predefinidas disponibles; la clave es el callback_data del botón
PERIODOS = {
    'ultimas_5': ('Últimas 5', 30),
    'semana': ('Última semana', 7),
    'mes': ('Último mes', 30),
}

# callback_data del botón que permite ingresar un rango de fechas a mano
PERIODO_PERSONALIZADO = 'personalizado'


def teclado_rubros():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(nombre, callback_data=nombre)] for nombre in RUBROS]
    )

def teclado_tipo_proceso():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(nombre, callback_data=f"tp_{nombre}")] for nombre in TIPO_PROCESO]
    )

def teclado_estado_proceso():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(nombre, callback_data=f"ep_{nombre}")] for nombre in ESTADO_PROCESO]
    )

def teclado_tipo_operacion():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(nombre, callback_data=f"to_{nombre}")] for nombre in TIPO_OPERACION]
    )


def teclado_periodos():
    botones = [
        [InlineKeyboardButton(label, callback_data=clave)] for clave, (label, _) in PERIODOS.items()
    ]
    botones.append(
        [InlineKeyboardButton('Elegir rango de fechas', callback_data=PERIODO_PERSONALIZADO)]
    )
    return InlineKeyboardMarkup(botones)


def teclado_lista_presets(nombres_presets: list):
    botones = [[InlineKeyboardButton("➕ Crear Nuevo Preset", callback_data="pr_crear")]]
    for nombre in nombres_presets:
        botones.append([InlineKeyboardButton(f"📝 {nombre}", callback_data=f"pr_ver_{nombre}")])
    return InlineKeyboardMarkup(botones)


def teclado_acciones_preset(nombre_preset: str):
    botones = [
        [InlineKeyboardButton("▶️ Ejecutar", callback_data=f"pr_exec_{nombre_preset}")],
        [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"pr_del_{nombre_preset}")],
        [InlineKeyboardButton("🔙 Volver", callback_data="pr_volver")]
    ]
    return InlineKeyboardMarkup(botones)


def teclado_lista_alertas(nombres_alertas: list):
    botones = [[InlineKeyboardButton("➕ Crear Nueva Alerta", callback_data="al_crear")]]
    for nombre in nombres_alertas:
        botones.append([InlineKeyboardButton(f"🔔 {nombre}", callback_data=f"al_ver_{nombre}")])
    return InlineKeyboardMarkup(botones)


def teclado_acciones_alerta(nombre_alerta: str):
    botones = [
        [InlineKeyboardButton("🗑️ Eliminar", callback_data=f"al_del_{nombre_alerta}")],
        [InlineKeyboardButton("🔙 Volver", callback_data="al_volver")]
    ]
    return InlineKeyboardMarkup(botones)

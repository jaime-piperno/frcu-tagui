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


def teclado_prioridad_alerta():
    botones = [
        [InlineKeyboardButton("🎯 Solo si incluye ítems de mi catálogo", callback_data="al_prio_si")],
        [InlineKeyboardButton("🌐 Notificar todas las del rubro", callback_data="al_prio_no")],
    ]
    return InlineKeyboardMarkup(botones)


def teclado_menu_catalogo():
    botones = [
        [InlineKeyboardButton("📋 Ver ítems del catálogo", callback_data="cat_ver")],
        [InlineKeyboardButton("🔍 Buscar en COMPR.AR (BuscarItemCiudadano)", callback_data="cat_buscar_web")],
        [InlineKeyboardButton("➕ Agregar ítem manualmente", callback_data="cat_agregar_manual")],
        [InlineKeyboardButton("📥 Descargar catalogo_empresa.xlsx", callback_data="cat_descargar")],
        [InlineKeyboardButton("📤 Subir/Reemplazar Excel (.xlsx)", callback_data="cat_subir_excel")],
        [InlineKeyboardButton("🗑️ Eliminar un ítem", callback_data="cat_eliminar_menu")],
    ]
    return InlineKeyboardMarkup(botones)


def teclado_resultados_items_ciudadano(items: list):
    botones = []
    for idx, item in enumerate(items):
        codigo = item.get('codigo', 'S/C')
        desc = item.get('descripcion', '')[:35]
        botones.append([
            InlineKeyboardButton(
                f"➕ Agregar {codigo} ({desc}...)",
                callback_data=f"cat_addweb_{idx}",
            )
        ])
    botones.append([InlineKeyboardButton("🔙 Volver al Catálogo", callback_data="cat_volver")])
    return InlineKeyboardMarkup(botones)


def teclado_eliminar_item_catalogo(df_catalogo):
    botones = []
    for idx, row in df_catalogo.iterrows():
        codigo = str(row.get('Codigo', '')).strip() or 'S/C'
        desc = str(row.get('Descripcion', '')).strip()[:30]
        botones.append([
            InlineKeyboardButton(
                f"🗑️ {idx + 1}. {codigo} - {desc}",
                callback_data=f"cat_delitem_{idx}",
            )
        ])
    botones.append([InlineKeyboardButton("🔙 Volver al Catálogo", callback_data="cat_volver")])
    return InlineKeyboardMarkup(botones)

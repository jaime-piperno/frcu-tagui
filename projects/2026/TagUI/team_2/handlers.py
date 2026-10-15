import asyncio
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from configuraciones import guardar_preset, obtener_presets, obtener_preset_por_nombre, eliminar_preset
from alertas import guardar_alerta, obtener_alertas, eliminar_alerta
from scraper import SinResultadosError, buscar_procesos_de_un_rubro, extraer_ultimas_licitaciones
from teclados import (
    PERIODO_PERSONALIZADO, PERIODOS, teclado_periodos, teclado_rubros, 
    teclado_tipo_proceso, teclado_estado_proceso, teclado_tipo_operacion,
    teclado_lista_presets, teclado_acciones_preset,
    teclado_lista_alertas, teclado_acciones_alerta
)

ELEGIR_RUBRO, ELEGIR_TIPO_PROCESO, ELEGIR_ESTADO_PROCESO, ELEGIR_TIPO_OPERACION, ELEGIR_PERIODO, INGRESAR_FECHA_DESDE, INGRESAR_FECHA_HASTA, GESTION_PRESETS, INGRESAR_NOMBRE_PRESET, GESTION_ALERTAS, INGRESAR_NOMBRE_ALERTA = range(11)

FORMATO_FECHA = '%d/%m/%Y'


def fecha_valida(texto: str) -> bool:
    try:
        datetime.strptime(texto, FORMATO_FECHA)
        return True
    except ValueError:
        return False


async def ejecutar_busqueda(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    rubro: str,
    periodo: str,
    fecha_desde: str,
    fecha_hasta: str,
    descripcion_periodo: str,
):

    await context.bot.send_message(
        chat_id,
        f'Buscando procesos de "{rubro}" ({descripcion_periodo})...\n'
        'Esto puede tardar unos segundos.',
    )

    try:
        loop = asyncio.get_running_loop()
        archivo = await loop.run_in_executor(
            None, 
            buscar_procesos_de_un_rubro, 
            fecha_desde, 
            fecha_hasta, 
            rubro,
            context.user_data.get('tipo_proceso'),
            context.user_data.get('estado_proceso'),
            context.user_data.get('tipo_operacion')
        )
    except SinResultadosError:
        await context.bot.send_message(
            chat_id,
            f'No se encontraron resultados para "{rubro}" ({descripcion_periodo}).',
        )
        return ConversationHandler.END
    except Exception as exc:
        await context.bot.send_message(chat_id, f'Ocurrió un error al buscar: {exc}')
        return ConversationHandler.END

    # Si se seleccionó "Últimas 5", enviamos el texto extraído
    if periodo == 'ultimas_5':
        mensaje_licitaciones = extraer_ultimas_licitaciones(archivo, 5)
        await context.bot.send_message(chat_id, text=mensaje_licitaciones, parse_mode='Markdown')

    # Enviar el archivo adjunto original siempre
    with open(archivo, 'rb') as reporte:
        await context.bot.send_document(chat_id, document=reporte)
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '¡Hola! Soy el bot de búsqueda de procesos de compra en comprar.gob.ar.\n\n'
        'Usá /buscar para una búsqueda rápida, /presets para guardar y usar búsquedas frecuentes, '
        'o /cancelar para interrumpir una búsqueda en curso.'
    )


async def menu_presets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    presets = obtener_presets(chat_id)
    nombres_presets = list(presets.keys())
    
    mensaje = "Tus presets guardados:" if nombres_presets else "No tienes presets guardados."
    if update.callback_query:
        await update.callback_query.edit_message_text(mensaje, reply_markup=teclado_lista_presets(nombres_presets))
    else:
        await update.message.reply_text(mensaje, reply_markup=teclado_lista_presets(nombres_presets))
    
    return GESTION_PRESETS


async def accion_preset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = update.effective_chat.id
    
    if data == "pr_crear":
        context.user_data['creando_preset'] = True
        await query.edit_message_text('Vamos a crear un preset.\n\nElegí un rubro:', reply_markup=teclado_rubros())
        return ELEGIR_RUBRO
        
    if data == "pr_volver":
        return await menu_presets(update, context)
        
    if data.startswith("pr_ver_"):
        nombre = data[7:]
        preset = obtener_preset_por_nombre(chat_id, nombre)
        if not preset:
            await query.edit_message_text("Preset no encontrado.")
            return ConversationHandler.END
            
        texto = f"📝 **{nombre}**\n\n"
        texto += f"Rubro: {preset['rubro']}\n"
        texto += f"Tipo Proceso: {preset['tipo_proceso']}\n"
        texto += f"Estado: {preset['estado_proceso']}\n"
        texto += f"Operación: {preset['tipo_operacion']}\n"
        
        periodo_label = PERIODOS[preset['periodo']][0] if preset['periodo'] in PERIODOS else "Personalizado"
        texto += f"Período: {periodo_label}\n"
        
        await query.edit_message_text(texto, reply_markup=teclado_acciones_preset(nombre), parse_mode="Markdown")
        return GESTION_PRESETS
        
    if data.startswith("pr_del_"):
        nombre = data[7:]
        eliminar_preset(chat_id, nombre)
        # Volvemos al menú
        return await menu_presets(update, context)
        
    if data.startswith("pr_exec_"):
        nombre = data[8:]
        preset = obtener_preset_por_nombre(chat_id, nombre)
        if not preset:
            await query.edit_message_text("Preset no encontrado.")
            return ConversationHandler.END
            
        context.user_data.update(preset) # Cargar rubro, tipo_proceso, etc.
        clave_periodo = preset['periodo']
        
        if clave_periodo == PERIODO_PERSONALIZADO:
            await query.edit_message_text(
                f'Ingresá la fecha desde en formato {FORMATO_FECHA.lower()} (ej: 01/09/2026):'
            )
            return INGRESAR_FECHA_DESDE
            
        # Período dinámico
        label, dias = PERIODOS[clave_periodo]
        hoy = datetime.now()
        fecha_desde = (hoy - timedelta(days=dias)).strftime(FORMATO_FECHA)
        fecha_hasta = hoy.strftime(FORMATO_FECHA)
        
        await query.edit_message_text(f'Ejecutando preset "{nombre}"...')
        return await ejecutar_busqueda(
            context, chat_id, preset['rubro'], clave_periodo, fecha_desde, fecha_hasta, label.lower()
        )


async def menu_alertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    alertas = obtener_alertas(chat_id)
    nombres_alertas = list(alertas.keys())
    
    mensaje = "Tus alertas automáticas guardadas:" if nombres_alertas else "No tienes alertas guardadas."
    if update.callback_query:
        await update.callback_query.edit_message_text(mensaje, reply_markup=teclado_lista_alertas(nombres_alertas))
    else:
        await update.message.reply_text(mensaje, reply_markup=teclado_lista_alertas(nombres_alertas))
    
    return GESTION_ALERTAS


async def accion_alerta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = update.effective_chat.id
    
    if data == "al_crear":
        context.user_data['creando_preset'] = False
        context.user_data['creando_alerta'] = True
        await query.edit_message_text('Vamos a configurar una nueva alerta automática.\n\nElegí un rubro:', reply_markup=teclado_rubros())
        return ELEGIR_RUBRO
        
    if data == "al_volver":
        return await menu_alertas(update, context)
        
    if data.startswith("al_ver_"):
        nombre = data[7:]
        alertas = obtener_alertas(chat_id)
        alerta = alertas.get(nombre)
        if not alerta:
            await query.edit_message_text("Alerta no encontrada.")
            return ConversationHandler.END
            
        texto = f"🔔 **{nombre}**\n\n"
        texto += f"Rubro: {alerta['rubro']}\n"
        texto += f"Tipo Proceso: {alerta['tipo_proceso']}\n"
        texto += f"Estado: {alerta['estado_proceso']}\n"
        texto += f"Operación: {alerta['tipo_operacion']}\n\n"
        texto += "Esta alerta se ejecuta automáticamente en segundo plano."
        
        await query.edit_message_text(texto, reply_markup=teclado_acciones_alerta(nombre), parse_mode="Markdown")
        return GESTION_ALERTAS
        
    if data.startswith("al_del_"):
        nombre = data[7:]
        eliminar_alerta(chat_id, nombre)
        return await menu_alertas(update, context)

async def nombre_alerta_ingresado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text.strip()
    if len(nombre) > 30:
        await update.message.reply_text('El nombre es demasiado largo. Por favor, ingresá uno más corto (máx 30 caracteres):')
        return INGRESAR_NOMBRE_ALERTA
        
    chat_id = update.effective_chat.id
    guardar_alerta(
        chat_id=chat_id,
        nombre_alerta=nombre,
        rubro=context.user_data['rubro'],
        tipo_proceso=context.user_data['tipo_proceso'],
        estado_proceso=context.user_data['estado_proceso'],
        tipo_operacion=context.user_data['tipo_operacion']
    )
    
    context.user_data['creando_alerta'] = False
    await update.message.reply_text(f'¡Alerta "{nombre}" guardada con éxito! El bot te notificará automáticamente cuando haya nuevas licitaciones que coincidan.')
    return ConversationHandler.END

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['creando_preset'] = False
    await update.message.reply_text('Elegí un rubro:', reply_markup=teclado_rubros())
    return ELEGIR_RUBRO


async def rubro_elegido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data['rubro'] = query.data
    await query.edit_message_text(
        f'Rubro elegido: {query.data}\n\nAhora elegí el Tipo de Proceso:',
        reply_markup=teclado_tipo_proceso(),
    )
    return ELEGIR_TIPO_PROCESO

async def tipo_proceso_elegido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # quitamos el prefijo 'tp_'
    seleccion = query.data[3:]
    context.user_data['tipo_proceso'] = seleccion
    await query.edit_message_text(
        f'Tipo de Proceso: {seleccion}\n\nAhora elegí el Estado del Proceso:',
        reply_markup=teclado_estado_proceso(),
    )
    return ELEGIR_ESTADO_PROCESO

async def estado_proceso_elegido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # quitamos el prefijo 'ep_'
    seleccion = query.data[3:]
    context.user_data['estado_proceso'] = seleccion
    await query.edit_message_text(
        f'Estado del Proceso: {seleccion}\n\nAhora elegí el Tipo de Operación:',
        reply_markup=teclado_tipo_operacion(),
    )
    return ELEGIR_TIPO_OPERACION

async def tipo_operacion_elegido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # quitamos el prefijo 'to_'
    seleccion = query.data[3:]
    context.user_data['tipo_operacion'] = seleccion
    
    if context.user_data.get('creando_alerta'):
        await query.edit_message_text(
            f'Tipo de Operación: {seleccion}\n\n'
            '¡Casi listo! Por favor, ingresá un nombre para esta alerta automática (máx 30 caracteres):'
        )
        return INGRESAR_NOMBRE_ALERTA

    await query.edit_message_text(
        f'Tipo de Operación: {seleccion}\n\nPor último, elegí el período:',
        reply_markup=teclado_periodos(),
    )
    return ELEGIR_PERIODO


async def periodo_elegido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    clave_periodo = query.data
    context.user_data['periodo'] = clave_periodo

    if context.user_data.get('creando_preset'):
        await query.edit_message_text(
            '¡Casi listo! Por favor, ingresá un nombre para este preset (máx 30 caracteres):'
        )
        return INGRESAR_NOMBRE_PRESET

    if clave_periodo == PERIODO_PERSONALIZADO:
        await query.edit_message_text(
            f'Ingresá la fecha desde en formato {FORMATO_FECHA.lower()} (ej: 01/09/2026):'
        )
        return INGRESAR_FECHA_DESDE

    rubro = context.user_data['rubro']
    label, dias = PERIODOS[clave_periodo]

    hoy = datetime.now()
    fecha_desde = (hoy - timedelta(days=dias)).strftime(FORMATO_FECHA)
    fecha_hasta = hoy.strftime(FORMATO_FECHA)

    await query.edit_message_text(f'Período elegido: {label}')
    return await ejecutar_busqueda(
        context, update.effective_chat.id, rubro, clave_periodo, fecha_desde, fecha_hasta, label.lower()
    )


async def nombre_preset_ingresado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text.strip()
    if len(nombre) > 30:
        await update.message.reply_text('El nombre es demasiado largo. Por favor, ingresá uno más corto (máx 30 caracteres):')
        return INGRESAR_NOMBRE_PRESET
        
    chat_id = update.effective_chat.id
    guardar_preset(
        chat_id=chat_id,
        nombre_preset=nombre,
        rubro=context.user_data['rubro'],
        tipo_proceso=context.user_data['tipo_proceso'],
        estado_proceso=context.user_data['estado_proceso'],
        tipo_operacion=context.user_data['tipo_operacion'],
        periodo=context.user_data['periodo']
    )
    
    await update.message.reply_text(f'¡Preset "{nombre}" guardado con éxito! Podés usar /presets para ejecutarlo.')
    return ConversationHandler.END


async def fecha_desde_ingresada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    if not fecha_valida(texto):
        await update.message.reply_text(
            f'Formato inválido. Ingresá la fecha desde en formato {FORMATO_FECHA.lower()} (ej: 01/09/2026):'
        )
        return INGRESAR_FECHA_DESDE

    context.user_data['fecha_desde'] = texto
    await update.message.reply_text(
        f'Ingresá la fecha hasta en formato {FORMATO_FECHA.lower()} (ej: 15/09/2026):'
    )
    return INGRESAR_FECHA_HASTA


async def fecha_hasta_ingresada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()

    if not fecha_valida(texto):
        await update.message.reply_text(
            f'Formato inválido. Ingresá la fecha hasta en formato {FORMATO_FECHA.lower()} (ej: 15/09/2026):'
        )
        return INGRESAR_FECHA_HASTA

    fecha_desde = context.user_data['fecha_desde']
    fecha_hasta = texto

    if datetime.strptime(fecha_hasta, FORMATO_FECHA) < datetime.strptime(fecha_desde, FORMATO_FECHA):
        await update.message.reply_text(
            'La fecha hasta no puede ser anterior a la fecha desde. '
            f'Ingresá la fecha hasta en formato {FORMATO_FECHA.lower()}:'
        )
        return INGRESAR_FECHA_HASTA

    rubro = context.user_data['rubro']
    descripcion = f'del {fecha_desde} al {fecha_hasta}'
    return await ejecutar_busqueda(
        context, update.effective_chat.id, rubro, PERIODO_PERSONALIZADO, fecha_desde, fecha_hasta, descripcion
    )


from alertas import extraer_ids_de_excel, obtener_ids_nuevos, marcar_como_vistos, cargar_alertas

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Búsqueda cancelada.')
    return ConversationHandler.END


async def tarea_revisar_alertas(context: ContextTypes.DEFAULT_TYPE):
    print("Revisando alertas automáticas...")
    alertas_por_chat = cargar_alertas()
    
    hoy = datetime.now()
    # Buscamos en los últimos 2 días para tener un poco de solapamiento
    fecha_desde = (hoy - timedelta(days=2)).strftime(FORMATO_FECHA)
    fecha_hasta = hoy.strftime(FORMATO_FECHA)
    
    loop = asyncio.get_running_loop()
    
    for chat_id_str, alertas in alertas_por_chat.items():
        chat_id = int(chat_id_str)
        for nombre_alerta, config in alertas.items():
            print(f"Revisando alerta '{nombre_alerta}' para {chat_id}...")
            try:
                # Ejecutamos la búsqueda silenciosamente
                archivo = await loop.run_in_executor(
                    None,
                    buscar_procesos_de_un_rubro,
                    fecha_desde,
                    fecha_hasta,
                    config['rubro'],
                    config.get('tipo_proceso'),
                    config.get('estado_proceso'),
                    config.get('tipo_operacion')
                )
                
                # Extraemos los IDs
                ids_encontrados = extraer_ids_de_excel(archivo)
                
                # Comparamos
                ids_nuevos = obtener_ids_nuevos(chat_id, nombre_alerta, ids_encontrados)
                
                if ids_nuevos:
                    print(f"¡Se encontraron {len(ids_nuevos)} resultados nuevos para '{nombre_alerta}'!")
                    
                    # Notificar al usuario
                    texto = f"🔔 **Nuevas Licitaciones Encontradas**\n"
                    texto += f"Alerta: {nombre_alerta}\n"
                    texto += f"Se encontraron {len(ids_nuevos)} nuevos resultados.\n\n"
                    texto += "Adjunto el reporte actualizado:"
                    
                    with open(archivo, 'rb') as reporte:
                        await context.bot.send_document(
                            chat_id=chat_id, 
                            document=reporte,
                            caption=texto,
                            parse_mode="Markdown"
                        )
                    
                    # Guardamos los nuevos como vistos
                    marcar_como_vistos(chat_id, nombre_alerta, ids_nuevos)
                else:
                    print(f"Sin resultados nuevos para '{nombre_alerta}'.")
                    
            except SinResultadosError:
                print(f"Sin resultados en la búsqueda para '{nombre_alerta}'.")
                pass
            except Exception as exc:
                print(f"Error revisando alerta '{nombre_alerta}': {exc}")

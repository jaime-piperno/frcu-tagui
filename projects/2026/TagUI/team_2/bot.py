from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from handlers import (
    ELEGIR_PERIODO,
    ELEGIR_RUBRO,
    ELEGIR_TIPO_PROCESO,
    ELEGIR_ESTADO_PROCESO,
    ELEGIR_TIPO_OPERACION,
    INGRESAR_FECHA_DESDE,
    INGRESAR_FECHA_HASTA,
    GESTION_PRESETS,
    INGRESAR_NOMBRE_PRESET,
    GESTION_ALERTAS,
    INGRESAR_NOMBRE_ALERTA,
    buscar,
    cancelar,
    fecha_desde_ingresada,
    fecha_hasta_ingresada,
    periodo_elegido,
    rubro_elegido,
    tipo_proceso_elegido,
    estado_proceso_elegido,
    tipo_operacion_elegido,
    start,
    menu_presets,
    accion_preset,
    nombre_preset_ingresado,
    menu_alertas,
    accion_alerta,
    nombre_alerta_ingresado,
    tarea_revisar_alertas,
)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError('Falta la variable de entorno TELEGRAM_BOT_TOKEN')

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    texto_sin_comandos = filters.TEXT & ~filters.COMMAND

    conversacion_busqueda = ConversationHandler(
        entry_points=[
            CommandHandler('buscar', buscar),
            CommandHandler('presets', menu_presets),
            CommandHandler('alertas', menu_alertas),
        ],
        states={
            GESTION_PRESETS: [CallbackQueryHandler(accion_preset, pattern='^pr_')],
            INGRESAR_NOMBRE_PRESET: [MessageHandler(texto_sin_comandos, nombre_preset_ingresado)],
            GESTION_ALERTAS: [CallbackQueryHandler(accion_alerta, pattern='^al_')],
            INGRESAR_NOMBRE_ALERTA: [MessageHandler(texto_sin_comandos, nombre_alerta_ingresado)],
            ELEGIR_RUBRO: [CallbackQueryHandler(rubro_elegido)],
            ELEGIR_TIPO_PROCESO: [CallbackQueryHandler(tipo_proceso_elegido)],
            ELEGIR_ESTADO_PROCESO: [CallbackQueryHandler(estado_proceso_elegido)],
            ELEGIR_TIPO_OPERACION: [CallbackQueryHandler(tipo_operacion_elegido)],
            ELEGIR_PERIODO: [CallbackQueryHandler(periodo_elegido)],
            INGRESAR_FECHA_DESDE: [MessageHandler(texto_sin_comandos, fecha_desde_ingresada)],
            INGRESAR_FECHA_HASTA: [MessageHandler(texto_sin_comandos, fecha_hasta_ingresada)],
        },
        fallbacks=[CommandHandler('cancelar', cancelar)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(conversacion_busqueda)
    
    # Programar la revisión de alertas cada 1 hora (3600 segundos)
    # y también ejecutamos una vez a los 10 segundos de iniciar el bot
    app.job_queue.run_repeating(tarea_revisar_alertas, interval=3600, first=10)
    
    app.run_polling()

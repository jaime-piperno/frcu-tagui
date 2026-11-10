js fila_nueva = proxima_fila(filas_planilla); numero_preinscripcion = proximo_numero(filas_planilla); datos_fila = fila_preinscripcion(numero_preinscripcion, registro, chat_id);
js mostrar_planilla = (typeof mostrar_planilla_al_registrar !== 'undefined') && mostrar_planilla_al_registrar

if mostrar_planilla
    excel_visible = true
    excel_focus = true
    vista_previa = [`carpeta_planilla`/preinscripciones.xlsx]Preinscripciones!A1
    js ventana_telegram = minimizar_chrome()
    wait 2

[`carpeta_planilla`/preinscripciones.xlsx]Preinscripciones!A`fila_nueva` = datos_fila

if mostrar_planilla
    wait 3
    js restaurar_chrome(ventana_telegram)

js excel_close()

excel_visible = false
excel_focus = false
fila_releida = [`carpeta_planilla`/preinscripciones.xlsx]Preinscripciones!A`fila_nueva`:I`fila_nueva`
js excel_close()
js registro_guardado = fila_guardada(fila_releida, registro)
if registro_guardado
    echo Inscripcion N° `numero_preinscripcion` guardada en la fila `fila_nueva` de la planilla
else
    echo ALERTA: la inscripcion no quedo guardada en la planilla

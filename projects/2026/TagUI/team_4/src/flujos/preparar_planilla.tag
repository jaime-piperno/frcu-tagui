js planilla_existe = require('fs').exists(carpeta_planilla + '/preinscripciones.xlsx')
if planilla_existe == false
    js encabezados = encabezados_planilla()
    [`carpeta_planilla`/preinscripciones.xlsx]Preinscripciones!A1 = encabezados
    js excel_close()
    echo Planilla creada: `carpeta_planilla`/preinscripciones.xlsx

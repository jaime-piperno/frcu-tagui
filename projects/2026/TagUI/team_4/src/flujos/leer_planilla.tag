tagui flujos/preparar_planilla.tag
filas_planilla = [`carpeta_planilla`/preinscripciones.xlsx]Preinscripciones!A:I
js excel_close()
js inscriptos = inscriptos_desde_filas(filas_planilla)
echo Planilla leida: `inscriptos.length` preinscripciones

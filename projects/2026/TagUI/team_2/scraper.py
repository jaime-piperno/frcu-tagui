import os
import re

import pandas as pd
import rpa as r

from config import RESULTADOS_DIR
from rubros import RUBROS
from opciones import TIPO_PROCESO, ESTADO_PROCESO, TIPO_OPERACION

# nombre con el que comprar.gob.ar siempre nombra la descarga del reporte
NOMBRE_DESCARGA = 'ReporteProcesos.xls'


class SinResultadosError(Exception):
    """No se encontraron procesos para la búsqueda realizada."""


def extraer_ultimas_licitaciones(archivo_xls: str, cantidad: int = 5) -> str:
    """
    Lee el archivo Excel descargado y extrae las últimas N licitaciones
    como un texto formateado.
    """
    try:
        # Algunos archivos XLS generados tienen problemas de formato o son HTML.
        # En comprar.gob.ar suele ser un archivo binario pero a veces tira advertencias.
        df = pd.read_excel(archivo_xls)
        
        # Tomar las primeras N (ya deberían venir ordenadas por el sitio)
        top_n = df.head(cantidad)
        
        if top_n.empty:
            return "No hay licitaciones en el archivo."
            
        # Los nombres de columnas tienen problemas de codificación a veces 
        # (ej: 'Nmero de Proceso'). Usamos los índices para ser más seguros.
        # 0: Número de Proceso, 2: Nombre proceso, 4: Fecha de apertura, 6: Unidad Ejecutora
        col_numero = df.columns[0]
        col_nombre = df.columns[2]
        col_fecha = df.columns[4]
        col_unidad = df.columns[6]
        
        mensaje = f"🏢 **Últimas {len(top_n)} Licitaciones**\n\n"
        
        for index, row in top_n.iterrows():
            numero = row[col_numero]
            nombre = row[col_nombre]
            fecha = row[col_fecha]
            unidad = row[col_unidad]
            
            mensaje += f"🔹 **{nombre}**\n"
            mensaje += f"   🏷️ **Proceso:** `{numero}`\n"
            mensaje += f"   📅 **Apertura:** {fecha}\n"
            mensaje += f"   🏛️ **Organismo:** {unidad}\n\n"
            
        return mensaje
    except Exception as e:
        return f"Error al extraer las licitaciones del Excel: {e}"


def buscar_procesos_de_un_rubro(fecha_desde: str, fecha_hasta: str, rubro: str, tipo_proceso: str = None, estado_proceso: str = None, tipo_operacion: str = None, archivo_salida: str = None):
    """
    Busca procesos de compra del rubro indicado en comprar.gob.ar
    dentro del rango de fechas de apertura indicado, ordenados por
    fecha de apertura, y descarga el reporte Excel de resultados
    dentro del repositorio.
    """
    r.init()
    if archivo_salida is None:
        rubro_nombre = re.sub(r'[^A-Za-z0-9]+', '_', rubro).strip('_').lower()
        desde_nombre = fecha_desde.replace('/', '-')
        hasta_nombre = fecha_hasta.replace('/', '-')
        archivo_salida = os.path.join(
            RESULTADOS_DIR, f'procesos_{rubro_nombre}_{desde_nombre}_{hasta_nombre}.xls'
        )

    carpeta_salida = os.path.dirname(archivo_salida)
    os.makedirs(carpeta_salida, exist_ok=True)

    # las descargas del navegador van a esta carpeta con el nombre fijo
    # que usa el sitio; si ya existe de una corrida anterior, se borra
    # para no terminar con "ReporteProcesos (1).xls"
    descarga_previa = os.path.join(carpeta_salida, NOMBRE_DESCARGA)
    if os.path.exists(descarga_previa):
        os.remove(descarga_previa)
    r.download_location(carpeta_salida)

    r.url('https://comprar.gob.ar/BuscarAvanzado.aspx')
    r.wait()  # ensure the search form is fully loaded

    r.select('#ctl00_CPH1_ddlRubro', RUBROS[rubro])
    
    if tipo_proceso and tipo_proceso != 'Cualquiera':
        r.select('#ctl00_CPH1_ddlTipoProceso', TIPO_PROCESO[tipo_proceso])
    
    if estado_proceso and estado_proceso != 'Cualquiera':
        r.select('#ctl00_CPH1_ddlEstadoProceso', ESTADO_PROCESO[estado_proceso])
        
    if tipo_operacion and tipo_operacion != 'Cualquiera':
        r.select('#ctl00_CPH1_ddlTipoOperacion', TIPO_OPERACION[tipo_operacion])

    r.type('#ctl00_CPH1_devDteEdtFechaAperturaDesde_I', '[clear]' + fecha_desde)
    r.type('#ctl00_CPH1_devDteEdtFechaAperturaHasta_I', '[clear]' + fecha_hasta)
    r.select('#ctl00_CPH1_ddlResultadoOrdenadoPor', 'PLI.PliegoCronograma.FechaActoApertura')

    r.click('#ctl00_CPH1_btnListarPliegoAvanzado')

    # el postback de ASP.NET es asincrono: esperar a que termine y aparezca
    # el botón de descarga. Ojo: la grilla de resultados (GridListaPliegos)
    # tiene celdas <td> incluso cuando no hay resultados (muestra un
    # mensaje de "no se encontraron registros" dentro de un <td>), así que
    # no sirve como indicador; el botón de descarga sí es un indicador
    # confiable porque el sitio sólo lo renderiza si hay filas con datos.
    #
    # cada r.count() implica un ida y vuelta real con el proceso de TagUI
    # (~1.5-2s), aparte del propio r.wait(); por eso se usan pocos intentos
    # en vez de sondear segundo a segundo, que en la práctica tardaba casi
    # un minuto para confirmar que no había resultados
    boton_descarga_presente = r.count('#ctl00_CPH1_btnDescargarReporteExcel') > 0
    intentos_restantes = 6
    while not boton_descarga_presente and intentos_restantes > 0:
        r.wait(1.5)
        boton_descarga_presente = r.count('#ctl00_CPH1_btnDescargarReporteExcel') > 0
        intentos_restantes -= 1

    # si el botón de descarga nunca apareció, el sitio no encontró
    # procesos para esos filtros: cortamos acá en lugar de clickear un
    # elemento inexistente, que dejaría a TagUI reintentando
    # indefinidamente y al bot "trabado"
    if not boton_descarga_presente:
        r.close()
        raise SinResultadosError(
            f'No se encontraron procesos de "{rubro}" entre {fecha_desde} y {fecha_hasta}'
        )

    r.click('#ctl00_CPH1_btnDescargarReporteExcel')

    # esperar a que el archivo se termine de descargar
    segundos_esperados = 0
    while not os.path.isfile(descarga_previa) and segundos_esperados < 20:
        r.wait(1)
        segundos_esperados += 1

    os.replace(descarga_previa, archivo_salida)
    r.close()
    return archivo_salida

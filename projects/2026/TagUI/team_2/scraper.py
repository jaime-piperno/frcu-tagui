import os
import re

import pandas as pd
import rpa as r

from config import RESULTADOS_DIR
from rubros import RUBROS
from opciones import TIPO_PROCESO, ESTADO_PROCESO, TIPO_OPERACION
import html
import threading
import httpx
from config import MAX_PROCESOS_INSPECCION
from catalogo import enriquecer_reporte_excel, limpiar_texto_markdown

# Lock global para asegurar que sólo una instancia de TagUI / Chrome
# interactúe con el navegador a la vez y evitar colisiones de sesión.
TAGUI_LOCK = threading.Lock()

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
            mensaje += f"   🏛️ **Organismo:** {unidad}\n"
            if 'Coincide con Catálogo' in df.columns:
                coincide = limpiar_texto_markdown(row.get('Coincide con Catálogo', '-'))
                grado = limpiar_texto_markdown(row.get('Grado de Coincidencia', '-'))
                detalle = limpiar_texto_markdown(row.get('Detalle de Coincidencias', ''))
                icono_match = "✅" if coincide == 'SÍ' else "❌"
                mensaje += f"   {icono_match} **Match Catálogo:** {coincide} ({grado})\n"
                if coincide == 'SÍ' and detalle:
                    mensaje += f"   📦 **Ítems:** {str(detalle)[:120]}\n"
            mensaje += "\n"

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
    with TAGUI_LOCK:
        r.init()
        try:
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
            try:
                items_por_proceso = recolectar_items_de_procesos_en_sesion(
                    archivo_salida, max_procesos=MAX_PROCESOS_INSPECCION
                )
                archivo_salida, _ = enriquecer_reporte_excel(archivo_salida, items_por_proceso)
            except Exception as e:
                print(f"Advertencia: no se pudieron recolectar/cruzar ítems adicionales ({e})")
            return archivo_salida
        finally:
            try:
                r.close()
            except Exception:
                pass


def separar_cantidad_y_unidad(texto_cantidad: str):
    """
    Separa cadenas del estilo '2.000,00 UNIDAD' en ('2.000,00', 'UNIDAD').
    """
    if not texto_cantidad:
        return '', ''
    partes = str(texto_cantidad).strip().split(None, 1)
    if len(partes) == 2:
        return partes[0].strip(), partes[1].strip()
    return partes[0].strip(), ''


def parsear_items_html_pliego(html_pliego: str) -> list:
    """
    Extrae los ítems de la tabla #ctl00_CPH1_UCVistaPreviaPliego_UC_DetalleProductos_gvLineaPliego
    a partir del HTML de VistaPreviaPliegoCiudadano.aspx.
    """
    items = []
    if not html_pliego or 'gvLineaPliego' not in html_pliego:
        return items

    match_tabla = re.search(
        r'<table[^>]*id="ctl00_CPH1_UCVistaPreviaPliego_UC_DetalleProductos_gvLineaPliego"[^>]*>(.*?)</table>',
        html_pliego,
        re.DOTALL | re.IGNORECASE,
    )
    if not match_tabla:
        return items

    cuerpo_tabla = match_tabla.group(1)
    filas = re.findall(r'<tr[^>]*>(.*?)</tr>', cuerpo_tabla, re.DOTALL | re.IGNORECASE)

    for fila in filas:
        celdas = re.findall(r'<td[^>]*>(.*?)</td>', fila, re.DOTALL | re.IGNORECASE)
        if len(celdas) >= 5:
            limpiar = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()
            renglon = limpiar(celdas[0])
            objeto_gasto = limpiar(celdas[1])
            codigo_item = limpiar(celdas[2])
            descripcion = limpiar(celdas[3])
            cant_raw = limpiar(celdas[4])
            cantidad, unidad = separar_cantidad_y_unidad(cant_raw)
            items.append({
                'renglon': renglon,
                'objeto_gasto': objeto_gasto,
                'codigo_item': codigo_item,
                'descripcion': descripcion,
                'cantidad': cantidad,
                'unidad_medida': unidad,
            })
    return items


def extraer_items_tabla_pliego_actual() -> list:
    """
    Lee los ítems de la tabla gvLineaPliego cuando el navegador de TagUI se encuentra
    en la página VistaPreviaPliegoCiudadano.aspx.
    """
    selector_tabla = '#ctl00_CPH1_UCVistaPreviaPliego_UC_DetalleProductos_gvLineaPliego'
    intentos = 4
    while r.count(selector_tabla) == 0 and intentos > 0:
        r.wait(1)
        intentos -= 1

    if r.count(selector_tabla) == 0:
        return []

    # 1 sola llamada IPC vía DOM para obtener el HTML completo de la tabla de ítems
    html_tabla = r.dom(
        'return document.getElementById("ctl00_CPH1_UCVistaPreviaPliego_UC_DetalleProductos_gvLineaPliego").outerHTML'
    )
    if html_tabla and '<table' in str(html_tabla).lower():
        items_parseados = parsear_items_html_pliego(str(html_tabla))
        if items_parseados:
            return items_parseados[:25]

    items = []
    xpath_filas = '//table[@id="ctl00_CPH1_UCVistaPreviaPliego_UC_DetalleProductos_gvLineaPliego"]//tr[td]'
    total_filas = r.count(xpath_filas)
    for i in range(1, min(total_filas, 10) + 1):
        renglon = r.read(f'({xpath_filas})[{i}]/td[1]').strip()
        objeto_gasto = r.read(f'({xpath_filas})[{i}]/td[2]').strip()
        codigo_item = r.read(f'({xpath_filas})[{i}]/td[3]').strip()
        descripcion = r.read(f'({xpath_filas})[{i}]/td[4]').strip()
        cant_raw = r.read(f'({xpath_filas})[{i}]/td[5]').strip()
        cantidad, unidad = separar_cantidad_y_unidad(cant_raw)
        items.append({
            'renglon': renglon,
            'objeto_gasto': objeto_gasto,
            'codigo_item': codigo_item,
            'descripcion': descripcion,
            'cantidad': cantidad,
            'unidad_medida': unidad,
        })
    return items


def obtener_items_proceso_http(num_proc: str) -> list:
    """
    Obtiene rápidamente los ítems de un proceso puntual navegando el flujo
    de BuscarAvanzado.aspx -> VistaPreviaPliegoCiudadano.aspx mediante httpx.
    """
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
    }
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            r1 = client.get('https://comprar.gob.ar/BuscarAvanzado.aspx')
            if r1.status_code != 200:
                return []

            extraer_campo = lambda html_txt, campo: (
                re.search(rf'id="{campo}"\s+value="([^"]*)"', html_txt).group(1)
                if re.search(rf'id="{campo}"\s+value="([^"]*)"', html_txt)
                else ''
            )

            data1 = {
                '__EVENTTARGET': 'ctl00$CPH1$btnListarPliegoNumero',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': extraer_campo(r1.text, '__VIEWSTATE'),
                '__VIEWSTATEGENERATOR': extraer_campo(r1.text, '__VIEWSTATEGENERATOR'),
                '__EVENTVALIDATION': extraer_campo(r1.text, '__EVENTVALIDATION'),
                'ctl00$CPH1$txtNumeroProceso': num_proc,
            }
            headers_post = headers.copy()
            headers_post['Referer'] = 'https://comprar.gob.ar/BuscarAvanzado.aspx'
            headers_post['Origin'] = 'https://comprar.gob.ar'
            r2 = client.post('https://comprar.gob.ar/BuscarAvanzado.aspx', data=data1, headers=headers_post)
            if r2.status_code != 200 or 'ctl00_CPH1_GridListaPliegos_ctl02_lnkNumeroProceso' not in r2.text:
                return []

            data2 = {
                '__EVENTTARGET': 'ctl00$CPH1$GridListaPliegos$ctl02$lnkNumeroProceso',
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': extraer_campo(r2.text, '__VIEWSTATE'),
                '__VIEWSTATEGENERATOR': extraer_campo(r2.text, '__VIEWSTATEGENERATOR'),
                '__EVENTVALIDATION': extraer_campo(r2.text, '__EVENTVALIDATION'),
            }
            headers_post2 = headers.copy()
            headers_post2['Referer'] = str(r2.url)
            headers_post2['Origin'] = 'https://comprar.gob.ar'
            r3 = client.post(str(r2.url), data=data2, headers=headers_post2)
            if r3.status_code == 200 and 'gvLineaPliego' in r3.text:
                return parsear_items_html_pliego(r3.text)[:25]
    except Exception as e:
        print(f"Aviso en obtener_items_proceso_http({num_proc}): {e}")
    return []


def recolectar_items_de_procesos_en_sesion(archivo_xls: str, max_procesos: int = None) -> dict:
    """
    Con la sesión de TagUI activa tras listar procesos en BuscarAvanzado.aspx,
    recolecta los ítems (renglón, código, descripción, cantidad y unidad) de los
    primeros `max_procesos` procesos del reporte.
    """
    if max_procesos is None:
        max_procesos = MAX_PROCESOS_INSPECCION

    items_por_proceso = {}
    try:
        df = pd.read_excel(archivo_xls)
    except Exception:
        return items_por_proceso

    if df.empty:
        return items_por_proceso

    col_numero = df.columns[0]
    numeros_proceso = [str(x).strip() for x in df[col_numero].dropna().head(max_procesos).tolist()]

    for idx, num_proc in enumerate(numeros_proceso):
        try:
            # Para el primer proceso aprovechamos la grilla ya abierta en TagUI
            if idx == 0 and r.count('#ctl00_CPH1_GridListaPliegos_ctl02_lnkNumeroProceso') > 0:
                num_en_grilla = r.read('#ctl00_CPH1_GridListaPliegos_ctl02_lnkNumeroProceso').strip()
                if num_en_grilla == num_proc:
                    r.click('#ctl00_CPH1_GridListaPliegos_ctl02_lnkNumeroProceso')
                    r.wait(1.5)
                    items_rpa = extraer_items_tabla_pliego_actual()
                    if items_rpa:
                        items_por_proceso[num_proc] = items_rpa
                        continue

            # Para los siguientes (o si no coincidió el primero), usamos consulta directa rápida
            # y caemos a RPA si fuera necesario
            items_http = obtener_items_proceso_http(num_proc)
            if items_http:
                items_por_proceso[num_proc] = items_http
                continue

            r.url('https://comprar.gob.ar/BuscarAvanzado.aspx')
            r.wait(1)
            r.type('#ctl00_CPH1_txtNumeroProceso', '[clear]' + num_proc)
            r.click('#ctl00_CPH1_btnListarPliegoNumero')

            esperas = 4
            while r.count('#ctl00_CPH1_GridListaPliegos_ctl02_lnkNumeroProceso') == 0 and esperas > 0:
                r.wait(1)
                esperas -= 1

            if r.count('#ctl00_CPH1_GridListaPliegos_ctl02_lnkNumeroProceso') > 0:
                r.click('#ctl00_CPH1_GridListaPliegos_ctl02_lnkNumeroProceso')
                r.wait(1.5)
                items_por_proceso[num_proc] = extraer_items_tabla_pliego_actual()
            else:
                items_por_proceso[num_proc] = []
        except Exception as e:
            print(f"Error al recolectar ítems del proceso {num_proc}: {e}")
            items_por_proceso[num_proc] = []

    return items_por_proceso


def parsear_grilla_items_ciudadano(html_grilla: str, max_resultados: int = 10) -> list:
    """
    Extrae la lista de ítems del HTML de #divResultados en BuscarItemCiudadano.
    """
    resultados = []
    if not html_grilla:
        return resultados
    filas = re.findall(r'<tr[^>]*>(.*?)</tr>', html_grilla, re.DOTALL | re.IGNORECASE)
    limpiar = lambda s: re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()
    for fila in filas:
        celdas = re.findall(r'<td[^>]*>(.*?)</td>', fila, re.DOTALL | re.IGNORECASE)
        if len(celdas) >= 5:
            resultados.append({
                'codigo': limpiar(celdas[0]),
                'rubro': limpiar(celdas[1]),
                'clase': limpiar(celdas[2]),
                'descripcion': limpiar(celdas[3]),
                'estado': limpiar(celdas[4]),
            })
            if len(resultados) >= max_resultados:
                break
    return resultados


def buscar_items_ciudadano(termino: str, por_codigo: bool = False, max_resultados: int = 10) -> list:
    """
    Busca ítems en el portal https://comprar.gob.ar/Item/Item/BuscarItemCiudadano
    por código de ítem o por descripción.
    Prioriza la consulta directa vía HTTP (_GrillaItems) que responde en milisegundos
    sin bloquear el navegador TagUI, y cae a RPA únicamente como respaldo.
    """
    resultados = []
    termino_limpio = str(termino or '').strip()
    if not termino_limpio:
        return resultados

    # 1. Prioridad: Consulta directa HTTP al endpoint AJAX _GrillaItems
    # Es instantánea (~200ms) y no compite por el recurso de TagUI/Chrome
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'text/html, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://comprar.gob.ar/Item/Item/BuscarItemCiudadano',
        }
        params = (
            {'CodigoItem': termino_limpio, 'esBusquedaRapida': 'true'}
            if por_codigo
            else {'Descripcion': termino_limpio, 'esBusquedaAvanzada': 'true'}
        )
        with httpx.Client(timeout=12.0, follow_redirects=True, headers=headers) as client:
            resp = client.get(
                'https://comprar.gob.ar/Item/Item/_GrillaItems',
                params=params,
            )
            if resp.status_code == 200 and 'divResultados' in resp.text:
                resultados = parsear_grilla_items_ciudadano(resp.text, max_resultados)
                if resultados:
                    return resultados
    except Exception as e:
        print(f"Aviso en consulta HTTP rápida de _GrillaItems ({e}). Reintentando por RPA...")

    # 2. Respaldo vía TagUI / RPA (protegido con Lock para evitar colisiones)
    try:
        with TAGUI_LOCK:
            r.init()
            try:
                r.url('https://comprar.gob.ar/Item/Item/BuscarItemCiudadano')
                r.wait(1.5)

                if por_codigo:
                    r.type('//input[@name="CodigoItem"]', '[clear]' + termino_limpio)
                    r.click('//button[@name="esBusquedaRapida"]')
                else:
                    r.type('//input[@name="Descripcion"]', '[clear]' + termino_limpio)
                    r.click('//button[@name="esBusquedaAvanzada" and @value="true"]')

                xpath_filas = '//div[@id="divResultados"]//table//tbody/tr[td]'
                intentos = 5
                while r.count(xpath_filas) == 0 and intentos > 0:
                    r.wait(1.5)
                    intentos -= 1

                if r.count(xpath_filas) > 0:
                    html_div = r.dom('return document.getElementById("divResultados").innerHTML')
                    resultados = parsear_grilla_items_ciudadano(str(html_div), max_resultados)
            finally:
                try:
                    r.close()
                except Exception:
                    pass
    except Exception as e:
        print(f"Error en fallback RPA BuscarItemCiudadano: {e}")

    return resultados

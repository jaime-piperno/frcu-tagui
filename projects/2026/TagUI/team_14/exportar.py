"""
Exportación de resultados a PDF y CSV.

- Conciliación de un mes: CSV de la hoja principal, CSV de cargos no conciliados y
  PDF con métricas, retenciones, control de cuadre y detalle de pendientes.
- Resumen del historial (un mes o un rango): PDF con detalle mes a mes y totales,
  y CSV con una fila por mes más la fila de totales.

Los CSV usan ';' como separador, coma decimal y UTF-8 con BOM, para abrirse
directamente en Excel configurado en español.
"""
from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import openpyxl
from fpdf import FPDF
from fpdf.fonts import FontFace

from conciliar import HEADERS, HOJAS_CARGOS, ETIQUETA_HOJA
from db import ahora

AZUL = (32, 55, 100)
GRIS_TEXTO = (89, 89, 89)
GRIS_FONDO = (242, 244, 248)
VERDE = (39, 106, 60)
ROJO = (160, 28, 36)
MAX_PENDIENTES_PDF = 1000

REEMPLAZOS_PDF = {
    '–': '-', '—': '-', '−': '-', '…': '...', '“': '"', '”': '"', '‘': "'", '’': "'",
    '✔': 'OK', '✖': 'X', '→': '->', ' ': ' ',
}


# ---------------------------------------------------------------------------
# Utilidades de formato
# ---------------------------------------------------------------------------

def _decimal(valor) -> Decimal:
    if valor is None or valor == '':
        return Decimal('0')
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


def numero_csv(valor) -> str:
    """Importe con 2 decimales y coma decimal, sin separador de miles (ej. -1234,56)."""
    return f'{_decimal(valor):.2f}'.replace('.', ',')


def pesos(valor) -> str:
    """Importe al estilo argentino para el PDF: $ 1.234.567,89"""
    numero = _decimal(valor)
    texto = f'{abs(numero):,.2f}'.replace(',', '#').replace('.', ',').replace('#', '.')
    return f'-$ {texto}' if numero < 0 else f'$ {texto}'


def entero(valor) -> str:
    return f'{int(valor or 0):,}'.replace(',', '.')


def porcentaje(valor) -> str:
    return f'{float(valor or 0):.2f}'.replace('.', ',') + ' %'


def fecha_texto(valor) -> str:
    if isinstance(valor, datetime):
        return valor.strftime('%d/%m/%Y')
    if isinstance(valor, date):
        return valor.strftime('%d/%m/%Y')
    return '' if valor is None else str(valor)


def fecha_hora(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime('%d/%m/%Y %H:%M')
    except (TypeError, ValueError):
        return str(iso)


def _t(texto) -> str:
    """Adapta el texto a la codificación de las fuentes estándar del PDF (latin-1)."""
    texto = '' if texto is None else str(texto)
    for original, reemplazo in REEMPLAZOS_PDF.items():
        texto = texto.replace(original, reemplazo)
    return texto.encode('latin-1', errors='replace').decode('latin-1')


def _escribir_csv(destino: Path, encabezado: list[str], filas) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, 'w', encoding='utf-8-sig', newline='') as f:
        escritor = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        escritor.writerow(encabezado)
        escritor.writerows(filas)
    return destino


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def csv_hoja_principal(archivo_xlsx: Path, destino: Path) -> Path:
    """Exporta la hoja principal del Excel conciliado (10 columnas oficiales) a CSV."""
    wb = openpyxl.load_workbook(archivo_xlsx, read_only=True, data_only=True)
    try:
        ws = wb.worksheets[0]
        filas = []
        for fila in ws.iter_rows(min_row=2, max_col=len(HEADERS), values_only=True):
            if not fila or all(v is None for v in fila):
                continue
            filas.append([
                fecha_texto(fila[0]),
                fila[1] or '',
                '' if fila[2] is None else str(fila[2]),
                *[numero_csv(v) if v is not None else '' for v in fila[3:10]],
            ])
    finally:
        wb.close()
    return _escribir_csv(destino, list(HEADERS), filas)


def csv_pendientes(pendientes: list[dict], destino: Path) -> Path:
    """Exporta los cargos no conciliados a CSV."""
    filas = [
        [p['hoja'], p['fila'], p['id'], p['fecha'], p['fecha_operacion'],
         numero_csv(p['base']), numero_csv(p['importe']), p['motivo']]
        for p in pendientes
    ]
    encabezado = ['HOJA ORIGEN', 'FILA ORIGEN', 'ID OPERACION', 'FECHA RETENCION',
                  'FECHA OPERACION', 'BASE IMPONIBLE', 'IMPORTE CARGO', 'MOTIVO']
    return _escribir_csv(destino, encabezado, filas)


def csv_resumen(resumen: dict, destino: Path) -> Path:
    """Exporta un resumen del historial: una fila por mes y una fila de totales."""
    encabezado = [
        'PERIODO', 'FECHA CORRIDA', 'CANAL', 'ARCHIVO', 'MOVIMIENTOS', 'CARGOS TOTALES',
        'CARGOS ASOCIADOS', 'CARGOS PENDIENTES', '% ASOCIADO', 'MONTO NO CONCILIADO',
        'INGRESOS', 'EGRESOS', 'BALANCE', 'SIRCUPA', 'SIRTAC', 'IDC', 'GASTOS',
        'CUADRE OK', 'DIFERENCIA CUADRE',
    ]
    filas = []
    for m in resumen['meses']:
        filas.append([
            m['periodo'], fecha_hora(m['fecha_ejecucion']), m['canal'], m['archivo'],
            m['movimientos'], m['cargos_totales'], m['cargos_asociados'], m['cargos_pendientes'],
            numero_csv(m['porcentaje_asociado']), numero_csv(m['monto_pendiente']),
            numero_csv(m['ingresos']), numero_csv(m['egresos']), numero_csv(m['balance']),
            numero_csv(m['total_sircupa']), numero_csv(m['total_sirtac']),
            numero_csv(m['total_idc']), numero_csv(m['total_gastos']),
            'SI' if m['cuadre_ok'] else 'NO', numero_csv(m['diferencia_cuadre']),
        ])
    t = resumen['totales']
    filas.append([
        'TOTAL', '', '', f"{t['periodos']} períodos",
        t['movimientos'], t['cargos_totales'], t['cargos_asociados'], t['cargos_pendientes'],
        numero_csv(t['porcentaje_asociado']), numero_csv(t['monto_pendiente']),
        numero_csv(t['ingresos']), numero_csv(t['egresos']), numero_csv(t['balance']),
        numero_csv(t['total_sircupa']), numero_csv(t['total_sirtac']),
        numero_csv(t['total_idc']), numero_csv(t['total_gastos']),
        'SI' if t['periodos_descuadrados'] == 0 else 'NO', '',
    ])
    return _escribir_csv(destino, encabezado, filas)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

class InformePDF(FPDF):
    def __init__(self, titulo: str, subtitulo: str):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.titulo = titulo
        self.subtitulo = subtitulo
        self.generado = ahora().strftime('%d/%m/%Y %H:%M')
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=16)
        self.set_title(_t(titulo))
        self.set_creator('Conciliador RPA Mercado Pago')
        self.add_page()

    def header(self):
        self.set_fill_color(*AZUL)
        self.rect(0, 0, self.w, 24, style='F')
        self.set_text_color(255, 255, 255)
        self.set_xy(15, 6)
        self.set_font('Helvetica', 'B', 15)
        self.cell(0, 7, _t(self.titulo))
        self.set_xy(15, 14)
        self.set_font('Helvetica', '', 9)
        self.cell(0, 5, _t(self.subtitulo))
        self.set_text_color(0, 0, 0)
        self.set_y(31)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(*GRIS_TEXTO)
        self.cell(0, 5, _t(f'Generado el {self.generado} · Conciliador RPA Mercado Pago'), align='L')
        self.set_x(15)
        self.cell(0, 5, f'Página {self.page_no()}/{{nb}}', align='R')
        self.set_text_color(0, 0, 0)

    def seccion(self, texto: str):
        if self.get_y() > self.h - 45:
            self.add_page()
        self.ln(3)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(*AZUL)
        self.cell(0, 7, _t(texto), border='B', new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def nota(self, texto: str):
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(*GRIS_TEXTO)
        self.multi_cell(0, 4, _t(texto), new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def estado(self, ok: bool, texto_ok: str, texto_error: str):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(*(VERDE if ok else ROJO))
        self.multi_cell(0, 6, _t(texto_ok if ok else texto_error), new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0, 0, 0)

    def tabla(self, encabezado, filas, anchos, alineacion, tamanio=9, ancho_total=None,
              estilos_fila=None, fila_total=None):
        """Tabla con encabezado azul. `estilos_fila` es una lista paralela a `filas` con FontFace o None por celda."""
        self.set_font('Helvetica', '', tamanio)
        estilo_encabezado = FontFace(emphasis='BOLD', color=(255, 255, 255), fill_color=AZUL)
        with self.table(
            col_widths=anchos,
            width=ancho_total or sum(anchos),
            align='LEFT',
            text_align=alineacion,
            headings_style=estilo_encabezado,
            line_height=tamanio * 0.55,
            borders_layout='HORIZONTAL_LINES',
            cell_fill_color=GRIS_FONDO,
            cell_fill_mode='ROWS',
            repeat_headings=1,
        ) as tabla:
            fila_tabla = tabla.row()
            for titulo in encabezado:
                fila_tabla.cell(_t(titulo))
            for i, fila in enumerate(filas):
                fila_tabla = tabla.row()
                estilos = (estilos_fila[i] if estilos_fila else None) or [None] * len(fila)
                for valor, estilo in zip(fila, estilos):
                    fila_tabla.cell(_t(valor), style=estilo)
            if fila_total:
                fila_tabla = tabla.row()
                for valor in fila_total:
                    fila_tabla.cell(_t(valor), style=FontFace(emphasis='BOLD', fill_color=(221, 226, 236)))
        self.ln(2)


def _estilo_estado(ok: bool) -> FontFace:
    return FontFace(emphasis='BOLD', color=VERDE if ok else ROJO)


def pdf_conciliacion(destino: Path, *, periodo: str, archivo: str, metricas: dict,
                     cuadre: dict, pendientes: list[dict]) -> Path:
    """Informe PDF de la conciliación de un mes."""
    pdf = InformePDF(f'Conciliación Mercado Pago - {periodo}', f'Extracto: {archivo}')

    pdf.seccion('Resultado de la conciliación')
    pdf.tabla(
        ['Indicador', 'Valor'],
        [
            ['Movimientos procesados', entero(metricas['movimientos_totales'])],
            ['Cargos leídos del extracto', entero(metricas['cargos_totales'])],
            ['Cargos asociados', f"{entero(metricas['cargos_asociados'])} ({porcentaje(metricas['porcentaje_asociado'])})"],
            ['Cargos no conciliados', entero(metricas['cargos_pendientes'])],
            ['Monto no conciliado', pesos(metricas['monto_pendiente'])],
            ['Ingresos', pesos(metricas['ingresos'])],
            ['Egresos', pesos(metricas['egresos'])],
            ['Balance', pesos(metricas['balance'])],
        ],
        anchos=(70, 50), alineacion=('LEFT', 'RIGHT'),
    )

    pdf.seccion('Retenciones y gastos del extracto')
    ret = metricas['totales_retenciones']
    pdf.tabla(
        ['Concepto', 'Importe'],
        [[ETIQUETA_HOJA[s], pesos(ret[s.lower()])] for s in HOJAS_CARGOS],
        anchos=(70, 50), alineacion=('LEFT', 'RIGHT'),
        fila_total=['Total', pesos(sum((_decimal(v) for v in ret.values()), Decimal('0')))],
    )

    pdf.seccion('Control de cuadre')
    t = cuadre['total']
    pdf.tabla(
        ['Concepto', 'Total extracto', 'Imputado hoja principal', 'No conciliado', 'Diferencia', 'Estado'],
        [
            [d['concepto'], pesos(d['origen']), pesos(d['imputado']), pesos(d['pendiente']),
             pesos(d['diferencia']), 'OK' if d['ok'] else 'DESCUADRADO']
            for d in cuadre['detalle']
        ],
        anchos=(38, 29, 33, 27, 25, 28),
        alineacion=('LEFT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'CENTER'),
        tamanio=8,
        estilos_fila=[[None] * 5 + [_estilo_estado(d['ok'])] for d in cuadre['detalle']],
        fila_total=['Total deducciones', pesos(t['origen']), pesos(t['imputado']), pesos(t['pendiente']),
                    pesos(t['diferencia']), 'OK' if t['ok'] else 'DESCUADRADO'],
    )
    pdf.nota('Diferencia = Total extracto - (Imputado en hoja principal + No conciliado). '
             'El imputado se suma desde las columnas SIRCUPA, SIRTAC, GASTOS e IDC de la hoja principal generada.')
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 6, _t(
        f"Validación de MOV TOTAL: {entero(cuadre['filas_validadas'])} filas validadas, "
        f"{entero(len(cuadre['filas_con_error']))} con error."
    ), new_x='LMARGIN', new_y='NEXT')
    pdf.estado(
        cuadre['ok'],
        'Resultado del control: conciliación cuadrada y MOV TOTAL válido.',
        'Resultado del control: hay diferencias de cuadre o filas con error. Revisar el Excel.',
    )

    pdf.seccion(f"Cargos no conciliados ({entero(len(pendientes))})")
    if not pendientes:
        pdf.estado(True, 'Sin cargos pendientes: el 100 % de las retenciones y gastos fue conciliado.', '')
    else:
        visibles = pendientes[:MAX_PENDIENTES_PDF]
        pdf.tabla(
            ['Hoja', 'ID operación', 'Fecha', 'Base imponible', 'Importe', 'Motivo'],
            [[p['hoja'], p['id'], p['fecha'], pesos(p['base']), pesos(p['importe']), p['motivo']] for p in visibles],
            anchos=(12, 26, 19, 24, 20, 79),
            alineacion=('LEFT', 'LEFT', 'CENTER', 'RIGHT', 'RIGHT', 'LEFT'),
            tamanio=7.5,
            fila_total=['Total', '', '', '', pesos(metricas['monto_pendiente']), f"{entero(len(pendientes))} cargos"],
        )
        if len(pendientes) > len(visibles):
            pdf.nota(f'Se muestran los primeros {entero(len(visibles))}. El detalle completo está en el Excel y en el CSV de pendientes.')

    destino.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(destino))
    return destino


def pdf_resumen(resumen: dict, destino: Path) -> Path:
    """Informe PDF de un resumen del historial (un mes o un rango de meses)."""
    desde, hasta = resumen['desde'], resumen['hasta']
    rango = desde if desde == hasta else f'{desde} a {hasta}'
    t = resumen['totales']
    pdf = InformePDF(
        f'Resumen de conciliaciones - {rango}',
        f"{t['periodos']} período(s) con datos · se usa la última corrida registrada de cada mes",
    )

    pdf.seccion('Detalle por mes')
    pdf.tabla(
        ['Período', 'Mov.', '% asoc.', 'No conciliado', 'Ingresos', 'Egresos', 'Balance', 'Cuadre'],
        [
            [m['periodo'], entero(m['movimientos']), porcentaje(m['porcentaje_asociado']),
             pesos(m['monto_pendiente']), pesos(m['ingresos']), pesos(m['egresos']),
             pesos(m['balance']), 'OK' if m['cuadre_ok'] else 'ERROR']
            for m in resumen['meses']
        ],
        anchos=(17, 14, 17, 26, 30, 30, 30, 16),
        alineacion=('LEFT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'CENTER'),
        tamanio=8,
        estilos_fila=[[None] * 7 + [_estilo_estado(m['cuadre_ok'])] for m in resumen['meses']],
        fila_total=['Total', entero(t['movimientos']), porcentaje(t['porcentaje_asociado']),
                    pesos(t['monto_pendiente']), pesos(t['ingresos']), pesos(t['egresos']),
                    pesos(t['balance']), 'OK' if t['periodos_descuadrados'] == 0 else 'ERROR'],
    )

    pdf.seccion('Totales del período')
    pdf.tabla(
        ['Indicador', 'Valor'],
        [
            ['Movimientos procesados', entero(t['movimientos'])],
            ['Cargos asociados', f"{entero(t['cargos_asociados'])} de {entero(t['cargos_totales'])} ({porcentaje(t['porcentaje_asociado'])})"],
            ['Cargos no conciliados', entero(t['cargos_pendientes'])],
            ['Monto no conciliado', pesos(t['monto_pendiente'])],
            ['Ingresos', pesos(t['ingresos'])],
            ['Egresos', pesos(t['egresos'])],
            ['Balance', pesos(t['balance'])],
            ['Meses con cargos pendientes', entero(t['periodos_con_pendientes'])],
            ['Meses con diferencias de cuadre', entero(t['periodos_descuadrados'])],
        ],
        anchos=(70, 60), alineacion=('LEFT', 'RIGHT'),
    )

    pdf.seccion('Retenciones y gastos')
    pdf.tabla(
        ['Concepto', 'Importe'],
        [
            ['Retenciones SIRCUPA', pesos(t['total_sircupa'])],
            ['Retenciones SIRTAC', pesos(t['total_sirtac'])],
            ['Retenciones IDC', pesos(t['total_idc'])],
            ['Gastos y Comisiones', pesos(t['total_gastos'])],
        ],
        anchos=(70, 60), alineacion=('LEFT', 'RIGHT'),
        fila_total=['Total', pesos(sum((_decimal(t[k]) for k in ('total_sircupa', 'total_sirtac', 'total_idc', 'total_gastos')), Decimal('0')))],
    )

    if resumen.get('meses_sin_datos'):
        pdf.nota('Meses sin corridas registradas: ' + ', '.join(resumen['meses_sin_datos']) + '.')
    pdf.nota('Ingresos: suma de importes netos positivos. Egresos: suma de importes netos negativos '
             '(incluye "Impuesto por extracción"). Balance: ingresos - egresos.')

    destino.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(destino))
    return destino


# ---------------------------------------------------------------------------
# Resumen por intervalo de fechas
# ---------------------------------------------------------------------------

def _fecha_iso_a_texto(iso: str) -> str:
    try:
        return datetime.strptime(iso, '%Y-%m-%d').strftime('%d/%m/%Y')
    except (TypeError, ValueError):
        return str(iso)


def _retenciones_dia(d: dict) -> Decimal:
    return sum((_decimal(d[k]) for k in ('sircupa', 'sirtac', 'idc', 'gastos')), Decimal('0'))


def csv_resumen_dias(resumen: dict, destino: Path) -> Path:
    """Exporta el resumen de un intervalo de fechas: una fila por día y una fila de totales."""
    encabezado = [
        'FECHA', 'MOVIMIENTOS', 'INGRESOS', 'EGRESOS', 'BALANCE', 'SIRCUPA', 'SIRTAC', 'IDC', 'GASTOS',
        'MOV TOTAL', 'CARGOS NO CONCILIADOS', 'MONTO NO CONCILIADO',
    ]
    filas = [
        [
            _fecha_iso_a_texto(d['fecha']), d['movimientos'], numero_csv(d['ingresos']), numero_csv(d['egresos']),
            numero_csv(d['balance']), numero_csv(d['sircupa']), numero_csv(d['sirtac']), numero_csv(d['idc']),
            numero_csv(d['gastos']), numero_csv(d['mov_total']), d['cargos_pendientes'], numero_csv(d['monto_pendiente']),
        ]
        for d in resumen['dias']
    ]
    t = resumen['totales']
    filas.append([
        'TOTAL', t['movimientos'], numero_csv(t['ingresos']), numero_csv(t['egresos']), numero_csv(t['balance']),
        numero_csv(t['sircupa']), numero_csv(t['sirtac']), numero_csv(t['idc']), numero_csv(t['gastos']),
        numero_csv(t['mov_total']), t['cargos_pendientes'], numero_csv(t['monto_pendiente']),
    ])
    return _escribir_csv(destino, encabezado, filas)


def pdf_resumen_dias(resumen: dict, destino: Path) -> Path:
    """Informe PDF de un intervalo de fechas con detalle diario."""
    desde = _fecha_iso_a_texto(resumen['desde'])
    hasta = _fecha_iso_a_texto(resumen['hasta'])
    rango = desde if desde == hasta else f'{desde} al {hasta}'
    t = resumen['totales']
    pdf = InformePDF(
        f'Resumen de conciliaciones - {rango}',
        'Detalle diario · se usa la última corrida registrada de cada mes',
    )

    pdf.seccion('Totales del intervalo')
    pdf.tabla(
        ['Indicador', 'Valor'],
        [
            ['Movimientos', f"{entero(t['movimientos'])} ({entero(t['dias_con_movimientos'])} "
                            f"{'día' if t['dias_con_movimientos'] == 1 else 'días'} con movimientos)"],
            ['Ingresos', pesos(t['ingresos'])],
            ['Egresos', pesos(t['egresos'])],
            ['Balance', pesos(t['balance'])],
            ['Suma de MOV TOTAL (bruto)', pesos(t['mov_total'])],
            ['Cargos no conciliados con fecha en el intervalo', f"{entero(t['cargos_pendientes'])} ({pesos(t['monto_pendiente'])})"],
        ],
        anchos=(85, 65), alineacion=('LEFT', 'RIGHT'),
    )

    pdf.seccion('Retenciones y gastos imputados')
    pdf.tabla(
        ['Concepto', 'Importe'],
        [
            ['Retenciones SIRCUPA', pesos(t['sircupa'])],
            ['Retenciones SIRTAC', pesos(t['sirtac'])],
            ['Retenciones IDC', pesos(t['idc'])],
            ['Gastos y Comisiones', pesos(t['gastos'])],
        ],
        anchos=(85, 65), alineacion=('LEFT', 'RIGHT'),
        fila_total=['Total', pesos(_retenciones_dia(t))],
    )

    pdf.seccion('Detalle por día')
    if resumen['dias']:
        pdf.tabla(
            ['Fecha', 'Mov.', 'Ingresos', 'Egresos', 'Balance', 'Retenciones', 'No conciliado'],
            [
                [_fecha_iso_a_texto(d['fecha']), entero(d['movimientos']), pesos(d['ingresos']), pesos(d['egresos']),
                 pesos(d['balance']), pesos(_retenciones_dia(d)), pesos(d['monto_pendiente'])]
                for d in resumen['dias']
            ],
            anchos=(22, 14, 31, 31, 31, 27, 24),
            alineacion=('LEFT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'),
            tamanio=8,
            fila_total=['Total', entero(t['movimientos']), pesos(t['ingresos']), pesos(t['egresos']),
                        pesos(t['balance']), pesos(_retenciones_dia(t)), pesos(t['monto_pendiente'])],
        )
    else:
        pdf.nota('No hay movimientos registrados en el intervalo.')

    if resumen.get('meses_sin_datos'):
        pdf.nota('Meses sin corridas registradas: ' + ', '.join(resumen['meses_sin_datos']) + '.')
    if resumen.get('meses_sin_detalle'):
        pdf.nota('Meses sin detalle diario (volver a procesar el extracto): ' + ', '.join(resumen['meses_sin_detalle']) + '.')
    pdf.nota('Los movimientos se agrupan por RELEASE_DATE. Las retenciones y gastos son los imputados a los '
             'movimientos del intervalo; los cargos no conciliados se agrupan por la fecha de la retención.')

    destino.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(destino))
    return destino

"""
Automatización (RPA) para la Conciliación de Movimientos de Mercado Pago.
Lee el archivo descargado de Mercado Pago y reconstruye el importe total bruto
de cada operación a partir de los reportes de retenciones y gastos.
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from collections import Counter, defaultdict
from copy import copy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from math import ceil
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent
CENT = Decimal('0.01')
ZERO = Decimal('0')

HEADERS = (
    'RELEASE_DATE', 'TRANSACTION_TYPE', 'REFERENCE_ID', 'TRANSACTION',
    'IDC COMPRAS', 'SIRCUPA', 'SIRTAC', 'GASTOS', 'IDC', 'MOV TOTAL'
)
HEADERS_PENDIENTES = (
    'HOJA ORIGEN', 'FILA ORIGEN', 'ID OPERACION', 'FECHA RETENCION',
    'FECHA OPERACION', 'BASE IMPONIBLE', 'IMPORTE CARGO', 'MOTIVO'
)
NUMBER_FORMAT = '#,##0.00;[Red]-#,##0.00'


def parse_money(value) -> Decimal:
    """Convierte importes de distintos formatos a Decimal con 2 decimales."""
    if value is None or value == '':
        return ZERO
    if isinstance(value, str):
        value = value.strip().replace('$', '').replace(' ', '')
        if ',' in value:
            value = value.replace('.', '').replace(',', '.')
    try:
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValueError(f"Importe monetario inválido: {value!r}")


def parse_id(value) -> str:
    """Conserva identificadores numéricos y alfanuméricos tal como vienen."""
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def norm(text) -> str:
    """Normaliza texto quitando tildes y pasando a minúsculas."""
    return ''.join(
        c for c in unicodedata.normalize('NFKD', str(text or ''))
        if not unicodedata.combining(c)
    ).lower().strip()


def parse_date(value) -> date:
    """Convierte fechas a objeto date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    for fmt in ('%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Fecha inválida: {value!r}")


def cargar_datos(excel_path: Path, periodo: str, hoja_tp: str = 'sheet0'):
    """Lee el Excel fuente y extrae los movimientos principales y deducciones del período."""
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    try:
        # Resolver hoja principal si no existe el nombre especificado
        if hoja_tp not in wb.sheetnames:
            for alt in ('sheet0', 'TP', 'Detallado'):
                if alt in wb.sheetnames:
                    hoja_tp = alt
                    break

        # 1. Movimientos principales
        source_rows = list(wb[hoja_tp].values)
        movimientos = []
        for rownum, row in enumerate(source_rows, 1):
            if rownum <= 4:
                continue
            if not row or not row[0]:
                break  # Fin de la tabla principal de movimientos
            if not row[1] or row[2] is None:
                continue
            try:
                d = parse_date(row[0])
            except ValueError:
                continue
            if d.strftime('%Y-%m') != periodo:
                continue

            movimientos.append({
                'row': rownum,
                'date': d,
                'type': str(row[1]),
                'id': parse_id(row[2]),
                'net': parse_money(row[3]),
                'charges': []
            })

        # 2. Cargos de deducciones (SIRCUPA, SIRTAC, IDC, Gastos)
        cargos = []
        for sheet_name in ('SIRCUPA', 'SIRTAC', 'IDC', 'Gastos'):
            if sheet_name not in wb.sheetnames:
                continue

            started = False
            for rownum, row in enumerate(wb[sheet_name].values, 1):
                if not row:
                    continue
                primera_col = norm(row[0])
                if primera_col in ('numero de operacion', 'operacion relacionada'):
                    started = True
                    continue
                if not started:
                    continue
                if not row[0]:
                    break  # Fin de la tabla oficial de Mercado Pago; se ignoran notas o controles posteriores

                # Fechas e importes según la hoja correspondiente
                try:
                    d = parse_date(row[2] if sheet_name == 'Gastos' else row[4])
                except ValueError:
                    continue

                # Filtrar fuera del período seleccionado
                if d.strftime('%Y-%m') != periodo:
                    continue

                # En Gastos, excluir los marcados con 'No' en cobrado en operación
                if sheet_name == 'Gastos' and norm(row[6]) == 'no':
                    continue

                try:
                    op_date = parse_date(row[2] if sheet_name != 'SIRCUPA' else row[1]) if sheet_name != 'Gastos' else d
                except ValueError:
                    op_date = d

                monto = parse_money(row[9] if sheet_name == 'Gastos' else row[7])
                base = parse_money(row[16] if sheet_name == 'Gastos' else row[6])

                cargos.append({
                    'sheet': sheet_name,
                    'row': rownum,
                    'id': parse_id(row[0]),
                    'date': d,
                    'op_date': op_date,
                    'amount': monto,
                    'base': base,
                    'target': None
                })

        return movimientos, cargos
    finally:
        wb.close()


def es_impuesto_extraccion(m) -> bool:
    return norm(m['type']) == 'impuesto por extraccion'


def es_anulacion(m) -> bool:
    t = norm(m['type'])
    return 'cancelada' in t or 'devolucion' in t


def total_cargos(m, sheet_name: str | None = None) -> Decimal:
    return sum((c['amount'] for c in m['charges'] if sheet_name is None or c['sheet'] == sheet_name), ZERO)


def asociar_cargos(movimientos: list[dict], cargos: list[dict], tolerancia: Decimal = CENT):
    """Asocia retenciones y comisiones a sus operaciones correspondientes en la hoja principal."""
    por_id = defaultdict(list)
    for m in movimientos:
        if not es_impuesto_extraccion(m):
            por_id[m['id']].append(m)

    # Nivel 1: Asociación directa por ID de operación
    for c in cargos:
        candidatos = [m for m in por_id[c['id']] if es_anulacion(m) == (c['amount'] < 0)]
        if len(candidatos) > 1:
            candidatos = [m for m in candidatos if m['date'] in (c['date'], c['op_date'])]
        if len(candidatos) == 1:
            c['target'] = candidatos[0]['row']
            candidatos[0]['charges'].append(c)

    # Nivel 2: IDC con identificadores alfanuméricos internos
    propuestas = []
    for c in cargos:
        if c['target'] is not None or c['sheet'] != 'IDC':
            continue

        candidatos = []
        for m in movimientos:
            if es_impuesto_extraccion(m) or any(x['sheet'] == 'IDC' for x in m['charges']):
                continue
            if m['date'] not in (c['date'], c['op_date']):
                continue
            if es_anulacion(m) != (c['amount'] < 0):
                continue

            esperado = c['base'] if m['net'] >= 0 or es_anulacion(m) else -c['base']
            if abs(m['net'] + total_cargos(m) + c['amount'] - esperado) <= tolerancia:
                if m['net'] > 0 and not any(abs(x['base'] - c['base']) <= tolerancia for x in m['charges']):
                    continue
                candidatos.append(m)

        if len(candidatos) == 1:
            propuestas.append((c, candidatos[0]))

    # Asignación de IDC únicos (evita colisiones o asignaciones ambiguas)
    conteo_movs = Counter(m['row'] for _, m in propuestas)
    for c, m in propuestas:
        if conteo_movs[m['row']] == 1:
            c['target'] = m['row']
            m['charges'].append(c)


def calcular_totales(movimientos: list[dict]):
    """Calcula el total reconstruido para cada fila de la hoja principal."""
    separados = defaultdict(list)
    for m in movimientos:
        if es_impuesto_extraccion(m):
            separados[(m['id'], m['date'])].append(m)

    filas_resultado = []
    for m in movimientos:
        sircupa = total_cargos(m, 'SIRCUPA')
        sirtac = total_cargos(m, 'SIRTAC')
        idc = total_cargos(m, 'IDC')
        gastos = total_cargos(m, 'Gastos')

        ajuste = sircupa + sirtac + idc + gastos
        filas_sep = separados[(m['id'], m['date'])] if not es_impuesto_extraccion(m) else []
        if filas_sep:
            ajuste -= idc

        reconstruido = m['net'] + ajuste

        if es_impuesto_extraccion(m):
            reconstruido = None

        filas_resultado.append({
            'fila_origen': m['row'],
            'fecha': m['date'],
            'tipo': m['type'],
            'reference_id': m['id'],
            'neto': m['net'],
            'sircupa': sircupa,
            'sirtac': sirtac,
            'idc': idc,
            'gastos': gastos,
            'total': reconstruido
        })
    return filas_resultado


# ---------------------------------------------------------------------------
# Etapa 2: control de cuadre, métricas, huella de datos y detalle de pendientes
# ---------------------------------------------------------------------------
import hashlib
import json

HOJAS_CARGOS = ('SIRCUPA', 'SIRTAC', 'IDC', 'Gastos')
CLAVE_RESULTADO = {'SIRCUPA': 'sircupa', 'SIRTAC': 'sirtac', 'IDC': 'idc', 'Gastos': 'gastos'}
# Columna (índice 0) de la hoja principal donde se imputa cada hoja de cargos (valores negativos)
COLUMNA_HOJA_PRINCIPAL = {'SIRCUPA': 5, 'SIRTAC': 6, 'Gastos': 7, 'IDC': 8}
ETIQUETA_HOJA = {
    'SIRCUPA': 'Retenciones SIRCUPA',
    'SIRTAC': 'Retenciones SIRTAC',
    'IDC': 'Retenciones IDC',
    'Gastos': 'Gastos y Comisiones',
}
PATRON_PERIODO = re.compile(r'20\d{2}-(0[1-9]|1[0-2])')
MAX_FILAS_ERROR_LISTADAS = 50


def detectar_periodo(nombre_archivo: str) -> str | None:
    """Devuelve el período YYYY-MM contenido en el nombre del archivo, o None si no lo tiene."""
    match = PATRON_PERIODO.search(nombre_archivo or '')
    return match.group(0) if match else None


def huella_datos(movimientos: list[dict], cargos: list[dict]) -> str:
    """
    Huella (SHA-256) de los datos del período leídos del extracto: movimientos y cargos.
    No depende del nombre ni de los metadatos del archivo, así que identifica el mismo extracto
    aunque se haya renombrado o vuelto a descargar, y cambia si cambia cualquier importe, fecha o ID.
    Debe calcularse con la salida de cargar_datos (antes o después de asociar: usa solo campos leídos).
    """
    filas_mov = sorted(
        (m['date'].isoformat(), m['type'], m['id'], str(m['net']))
        for m in movimientos
    )
    filas_cargos = sorted(
        (c['sheet'], c['id'], c['date'].isoformat(), c['op_date'].isoformat(), str(c['amount']), str(c['base']))
        for c in cargos
    )
    contenido = json.dumps({'movimientos': filas_mov, 'cargos': filas_cargos}, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()


def comparar_con_anterior(anterior: dict | None, huella: str) -> str:
    """Estado de una corrida respecto de la última registrada del mismo período."""
    if anterior is None:
        return 'nuevo'
    if not anterior.get('huella'):
        return 'sin_huella'
    return 'identico' if anterior['huella'] == huella else 'distinto'


def motivo_pendiente(cargo: dict, ids_movimientos: set[str]) -> str:
    """Explica por qué un cargo no pudo asociarse a ningún movimiento de la hoja principal."""
    if cargo['id'] not in ids_movimientos:
        if cargo['sheet'] == 'IDC' and any(ch.isalpha() for ch in cargo['id']):
            return 'Código interno sin operación vinculable en fecha o base imponible'
        return 'ID de operación no encontrado en los movimientos del período'
    return 'Candidato no unívoco o discrepancia en importe/anulación'


def _a_decimal(valor) -> Decimal:
    """Convierte un valor leído de una celda (float, int, Decimal, str o None) a Decimal de 2 decimales."""
    if valor is None or valor == '':
        return ZERO
    if isinstance(valor, Decimal):
        return valor.quantize(CENT, rounding=ROUND_HALF_UP)
    if isinstance(valor, (int, float)):
        return Decimal(str(valor)).quantize(CENT, rounding=ROUND_HALF_UP)
    return parse_money(valor)


def _clave_fecha(valor):
    """Normaliza la fecha de la columna RELEASE_DATE para emparejar filas por (ID, fecha)."""
    try:
        return parse_date(valor)
    except ValueError:
        return str(valor).strip()


def calcular_cuadre(cargos: list[dict], filas_hoja_principal, tolerancia: Decimal = CENT) -> dict:
    """
    Control de cuadre independiente del proceso de asociación.

    Contrasta, para cada hoja de cargos, el total leído del extracto original contra lo que quedó
    efectivamente escrito en la hoja principal del Excel generado más lo derivado a No Conciliados:
        diferencia = total extracto - (imputado en hoja principal + no conciliado)

    Además valida fila por fila la columna MOV TOTAL:
        - caso general:                                  J = D - (F + G + H + I)
        - operación con fila 'Impuesto por extracción':  J = D - (F + G + H)   (el IDC no integra el bruto)
        - fila 'Impuesto por extracción':                J = D

    `filas_hoja_principal` es un iterable de tuplas con las 10 columnas de HEADERS (sin encabezado),
    tal como quedaron escritas en la hoja (deducciones con signo negativo).
    """
    filas = [tuple(f) for f in filas_hoja_principal if f and any(v is not None for v in f)]

    # 1. Cuadre por hoja de cargos
    imputado_por_hoja = {s: ZERO for s in HOJAS_CARGOS}
    for fila in filas:
        for s, col in COLUMNA_HOJA_PRINCIPAL.items():
            imputado_por_hoja[s] -= _a_decimal(fila[col])

    detalle = []
    tot_origen = tot_imputado = tot_pendiente = ZERO
    for s in HOJAS_CARGOS:
        cargos_s = [c for c in cargos if c['sheet'] == s]
        origen = sum((c['amount'] for c in cargos_s), ZERO)
        pendiente = sum((c['amount'] for c in cargos_s if c['target'] is None), ZERO)
        imputado = imputado_por_hoja[s]
        diferencia = origen - (imputado + pendiente)
        detalle.append({
            'hoja': s,
            'concepto': ETIQUETA_HOJA[s],
            'origen': origen,
            'imputado': imputado,
            'pendiente': pendiente,
            'diferencia': diferencia,
            'ok': abs(diferencia) <= tolerancia,
        })
        tot_origen += origen
        tot_imputado += imputado
        tot_pendiente += pendiente

    tot_diferencia = tot_origen - (tot_imputado + tot_pendiente)
    total = {
        'concepto': 'TOTAL GENERAL DEDUCCIONES',
        'origen': tot_origen,
        'imputado': tot_imputado,
        'pendiente': tot_pendiente,
        'diferencia': tot_diferencia,
        'ok': abs(tot_diferencia) <= tolerancia,
    }

    # 2. Validación fila por fila de MOV TOTAL
    pares_extraccion = {
        (str(f[2]).strip(), _clave_fecha(f[0]))
        for f in filas
        if norm(f[1]) == 'impuesto por extraccion'
    }
    filas_con_error = []
    for nro_fila, fila in enumerate(filas, start=2):
        neto = _a_decimal(fila[3])
        sircupa, sirtac, gastos, idc = (_a_decimal(fila[i]) for i in (5, 6, 7, 8))
        mov_total = _a_decimal(fila[9])

        if norm(fila[1]) == 'impuesto por extraccion':
            esperado = neto
        elif (str(fila[2]).strip(), _clave_fecha(fila[0])) in pares_extraccion:
            esperado = neto - (sircupa + sirtac + gastos)
        else:
            esperado = neto - (sircupa + sirtac + gastos + idc)

        if abs(mov_total - esperado) > tolerancia:
            filas_con_error.append({
                'fila': nro_fila,
                'reference_id': str(fila[2]),
                'mov_total': mov_total,
                'esperado': esperado,
                'diferencia': mov_total - esperado,
            })

    mov_total_ok = not filas_con_error
    return {
        'ok': all(d['ok'] for d in detalle) and total['ok'] and mov_total_ok,
        'tolerancia': tolerancia,
        'detalle': detalle,
        'total': total,
        'filas_validadas': len(filas),
        'filas_con_error': filas_con_error,
        'mov_total_ok': mov_total_ok,
    }


def validar_cuadre_excel(archivo_salida: Path, cargos: list[dict], tolerancia: Decimal = CENT) -> dict:
    """Relee la hoja principal del Excel ya guardado y calcula el cuadre sobre sus valores (control de punta a punta)."""
    wb = openpyxl.load_workbook(archivo_salida, read_only=True, data_only=True)
    try:
        ws = wb.worksheets[0]
        filas = list(ws.iter_rows(min_row=2, max_col=len(HEADERS), values_only=True))
    finally:
        wb.close()
    return calcular_cuadre(cargos, filas, tolerancia)


def calcular_metricas(movimientos: list[dict], cargos: list[dict], resultados: list[dict]) -> dict:
    """Indicadores de la corrida (montos en Decimal)."""
    pendientes = [c for c in cargos if c['target'] is None]
    asociados = len(cargos) - len(pendientes)
    porcentaje = (
        (Decimal(asociados) * 100 / Decimal(len(cargos))).quantize(CENT, rounding=ROUND_HALF_UP)
        if cargos else Decimal('100.00')
    )
    ingresos = sum((r['neto'] for r in resultados if r['neto'] > 0), ZERO)
    egresos = -sum((r['neto'] for r in resultados if r['neto'] < 0), ZERO)
    return {
        'movimientos_totales': len(movimientos),
        'cargos_totales': len(cargos),
        'cargos_asociados': asociados,
        'cargos_pendientes': len(pendientes),
        'porcentaje_asociado': porcentaje,
        'monto_pendiente': sum((c['amount'] for c in pendientes), ZERO),
        'ingresos': ingresos,
        'egresos': egresos,
        'balance': ingresos - egresos,
        'totales_retenciones': {
            CLAVE_RESULTADO[s]: sum((c['amount'] for c in cargos if c['sheet'] == s), ZERO)
            for s in HOJAS_CARGOS
        },
    }


def detalle_pendientes(movimientos: list[dict], cargos: list[dict]) -> list[dict]:
    """Lista de cargos no conciliados con su motivo."""
    ids_movs = {m['id'] for m in movimientos}
    return [
        {
            'hoja': c['sheet'],
            'fila': c['row'],
            'id': c['id'],
            'fecha': c['date'].strftime('%d/%m/%Y') if hasattr(c['date'], 'strftime') else str(c['date']),
            'fecha_operacion': c['op_date'].strftime('%d/%m/%Y') if hasattr(c['op_date'], 'strftime') else str(c['op_date']),
            'base': c['base'],
            'importe': c['amount'],
            'motivo': motivo_pendiente(c, ids_movs),
        }
        for c in cargos if c['target'] is None
    ]


def crear_hoja_auditoria(wb: openpyxl.Workbook, cuadre: dict):
    """Crea la pestaña 'Control y Cuadre' a partir del resultado de calcular_cuadre()."""
    ws_aud = wb.create_sheet(title='Control y Cuadre')
    ws_aud.sheet_properties.tabColor = '203764' if cuadre['ok'] else 'C00000'
    ws_aud.sheet_view.showGridLines = True
    ws_aud.sheet_view.zoomScale = 100

    anchos = {'A': 34, 'B': 22, 'C': 26, 'D': 22, 'E': 20, 'F': 26}
    for col_let, w in anchos.items():
        ws_aud.column_dimensions[col_let].width = w

    border_thin = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    border_tbl_hdr = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='medium', color='1F4E78'),
        bottom=Side(style='medium', color='1F4E78')
    )
    border_total = Border(
        left=Side(style='thin', color='BFBFBF'),
        right=Side(style='thin', color='BFBFBF'),
        top=Side(style='thin', color='1F4E78'),
        bottom=Side(style='double', color='1F4E78')
    )

    fill_tbl_hdr = PatternFill('solid', fgColor='203764')
    fill_total = PatternFill('solid', fgColor='F2F4F8')
    fill_ok = PatternFill('solid', fgColor='E2EFDA')
    fill_err = PatternFill('solid', fgColor='F8D7DA')

    font_tbl_hdr = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
    font_bold = Font(name='Calibri', size=11, bold=True, color='000000')
    font_reg = Font(name='Calibri', size=11, color='000000')
    font_nota = Font(name='Calibri', size=10, italic=True, color='595959')
    font_ok = Font(name='Calibri', size=11, bold=True, color='276A3C')
    font_err = Font(name='Calibri', size=11, bold=True, color='721C24')

    def escribir_encabezado(fila: int, titulos: list[str]):
        for col_idx, titulo in enumerate(titulos, start=1):
            cell = ws_aud.cell(fila, col_idx, titulo)
            cell.font = font_tbl_hdr
            cell.fill = fill_tbl_hdr
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = border_tbl_hdr
        ws_aud.row_dimensions[fila].height = 30

    def escribir_estado(cell, ok: bool, texto_ok: str, texto_err: str):
        cell.value = texto_ok if ok else texto_err
        cell.font = font_ok if ok else font_err
        cell.fill = fill_ok if ok else fill_err
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # 1. Cuadre por hoja de cargos
    escribir_encabezado(1, [
        'CONCEPTO / HOJA',
        'TOTAL EXTRACTO ($)',
        'IMPUTADO EN HOJA PRINCIPAL ($)',
        'NO CONCILIADO ($)',
        'DIFERENCIA ($)',
        'ESTADO DE CUADRE',
    ])

    curr_row = 2
    for d in cuadre['detalle']:
        ws_aud.cell(curr_row, 1, d['concepto']).font = font_reg
        ws_aud.cell(curr_row, 1).alignment = Alignment(horizontal='left', vertical='center')
        for col_idx, clave in ((2, 'origen'), (3, 'imputado'), (4, 'pendiente'), (5, 'diferencia')):
            cell = ws_aud.cell(curr_row, col_idx, float(d[clave]))
            cell.number_format = NUMBER_FORMAT
            cell.font = font_reg
            cell.alignment = Alignment(horizontal='right', vertical='center')
        escribir_estado(
            ws_aud.cell(curr_row, 6), d['ok'],
            '✔ CUADRADO', f"✖ DESCUADRADO ({float(d['diferencia']):,.2f})"
        )
        for col_idx in range(1, 7):
            ws_aud.cell(curr_row, col_idx).border = border_thin
        ws_aud.row_dimensions[curr_row].height = 22
        curr_row += 1

    t = cuadre['total']
    ws_aud.cell(curr_row, 1, t['concepto']).font = font_bold
    ws_aud.cell(curr_row, 1).alignment = Alignment(horizontal='left', vertical='center')
    for col_idx, clave in ((2, 'origen'), (3, 'imputado'), (4, 'pendiente'), (5, 'diferencia')):
        cell = ws_aud.cell(curr_row, col_idx, float(t[clave]))
        cell.number_format = NUMBER_FORMAT
        cell.font = font_bold
        cell.alignment = Alignment(horizontal='right', vertical='center')
    escribir_estado(
        ws_aud.cell(curr_row, 6), t['ok'],
        '✔ CUADRADO', f"✖ DESCUADRADO ({float(t['diferencia']):,.2f})"
    )
    for col_idx in range(1, 7):
        cell = ws_aud.cell(curr_row, col_idx)
        cell.border = border_total
        if col_idx < 6:
            cell.fill = fill_total
    ws_aud.row_dimensions[curr_row].height = 26
    curr_row += 1

    nota = ws_aud.cell(
        curr_row, 1,
        'Diferencia = Total extracto − (Imputado en hoja principal + No conciliado). '
        'El imputado se suma desde las columnas SIRCUPA, SIRTAC, GASTOS e IDC de la hoja principal generada.'
    )
    nota.font = font_nota
    ws_aud.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=6)
    nota.alignment = Alignment(wrap_text=True, vertical='top')
    ws_aud.row_dimensions[curr_row].height = 30
    curr_row += 2

    # 2. Validación de MOV TOTAL
    escribir_encabezado(curr_row, [
        'VALIDACIÓN MOV TOTAL',
        'FILAS VALIDADAS',
        'FILAS CON ERROR',
        '',
        '',
        'ESTADO',
    ])
    ws_aud.merge_cells(start_row=curr_row, start_column=3, end_row=curr_row, end_column=5)
    curr_row += 1
    ws_aud.cell(curr_row, 1, 'Hoja principal').font = font_reg
    ws_aud.cell(curr_row, 2, cuadre['filas_validadas']).font = font_reg
    ws_aud.cell(curr_row, 3, len(cuadre['filas_con_error'])).font = font_reg
    for col_idx in range(1, 7):
        ws_aud.cell(curr_row, col_idx).border = border_thin
    ws_aud.merge_cells(start_row=curr_row, start_column=3, end_row=curr_row, end_column=5)
    for col_idx in (2, 3):
        ws_aud.cell(curr_row, col_idx).alignment = Alignment(horizontal='center', vertical='center')
    escribir_estado(ws_aud.cell(curr_row, 6), cuadre['mov_total_ok'], '✔ VÁLIDO', '✖ CON ERRORES')
    ws_aud.row_dimensions[curr_row].height = 22
    curr_row += 1

    nota = ws_aud.cell(
        curr_row, 1,
        'Regla: J = D − (F+G+H+I). Si la operación tiene una fila "Impuesto por extracción" con el mismo ID y fecha, '
        'J = D − (F+G+H). En las filas "Impuesto por extracción", J = D.'
    )
    nota.font = font_nota
    ws_aud.merge_cells(start_row=curr_row, start_column=1, end_row=curr_row, end_column=6)
    nota.alignment = Alignment(wrap_text=True, vertical='top')
    ws_aud.row_dimensions[curr_row].height = 30
    curr_row += 1

    if cuadre['filas_con_error']:
        curr_row += 1
        escribir_encabezado(curr_row, ['FILA (HOJA PRINCIPAL)', 'REFERENCE_ID', 'MOV TOTAL ($)', 'ESPERADO ($)', 'DIFERENCIA ($)', ''])
        curr_row += 1
        for err in cuadre['filas_con_error'][:MAX_FILAS_ERROR_LISTADAS]:
            ws_aud.cell(curr_row, 1, err['fila'])
            ws_aud.cell(curr_row, 2, err['reference_id'])
            for col_idx, clave in ((3, 'mov_total'), (4, 'esperado'), (5, 'diferencia')):
                cell = ws_aud.cell(curr_row, col_idx, float(err[clave]))
                cell.number_format = NUMBER_FORMAT
            for col_idx in range(1, 7):
                ws_aud.cell(curr_row, col_idx).font = font_reg
                ws_aud.cell(curr_row, col_idx).border = border_thin
            curr_row += 1
        restantes = len(cuadre['filas_con_error']) - MAX_FILAS_ERROR_LISTADAS
        if restantes > 0:
            ws_aud.cell(curr_row, 1, f'... y {restantes} filas más con error').font = font_nota

    # 3. Resultado global
    curr_row += 1
    ws_aud.cell(curr_row, 1, 'RESULTADO DEL CONTROL').font = font_bold
    ws_aud.merge_cells(start_row=curr_row, start_column=2, end_row=curr_row, end_column=6)
    escribir_estado(
        ws_aud.cell(curr_row, 2), cuadre['ok'],
        '✔ CONCILIACIÓN CUADRADA Y MOV TOTAL VÁLIDO',
        '✖ REVISAR: HAY DIFERENCIAS DE CUADRE O FILAS CON ERROR'
    )
    ws_aud.row_dimensions[curr_row].height = 26

    ws_aud.freeze_panes = 'A2'


def generar_excel(
    archivo_origen: Path,
    archivo_destino: Path,
    resultados: list[dict],
    hoja_tp: str = 'sheet0',
    cargos_pendientes: list[dict] | None = None,
    movimientos: list[dict] | None = None,
    todos_los_cargos: list[dict] | None = None,
    periodo: str | None = None
):
    """Genera el Excel final con formato contable profesional, las 10 columnas oficiales,
    panel de auditoría 'Control y Cuadre' y hoja de pendientes 'No Conciliados'.
    Devuelve la ruta efectivamente guardada."""
    cargos_pend = cargos_pendientes or []
    if todos_los_cargos is not None:
        cargos_todos = todos_los_cargos
    else:
        cargos_todos = [c for m in (movimientos or []) for c in m.get('charges', [])] + cargos_pend

    template = openpyxl.load_workbook(archivo_origen, data_only=True)
    wb_salida = openpyxl.Workbook()
    ws = wb_salida.active
    ws.title = hoja_tp

    try:
        if hoja_tp not in template.sheetnames:
            for alt in ('sheet0', 'TP', 'Detallado'):
                if alt in template.sheetnames:
                    hoja_tp = alt
                    break

        ws_original = template[hoja_tp]
        ws.append(HEADERS)

        # Mapeo de columnas originales para estilos:
        # RELEASE_DATE, TRANSACTION_TYPE, REFERENCE_ID, TRANSACTION, IDC COMPRAS
        cols_origen = (1, 2, 3, 4, 8, 9, 10, 11, 12, 13)

        for row_idx, res in enumerate(resultados, start=2):
            src_row = res['fila_origen']
            total = res['total']

            valores = (
                ws_original.cell(src_row, 1).value,
                res['tipo'],
                res['reference_id'],
                res['neto'],
                ws_original.cell(src_row, 8).value,  # IDC COMPRAS
                -res['sircupa'],
                -res['sirtac'],
                -res['gastos'],
                -res['idc'],
                res['neto'] if total is None else total
            )

            for col_idx, val in enumerate(valores, start=1):
                cell = ws.cell(row_idx, col_idx, float(val) if isinstance(val, Decimal) else val)
                src_cell = ws_original.cell(src_row, cols_origen[col_idx - 1])

                for attr in ('font', 'fill', 'border'):
                    setattr(cell, attr, copy(getattr(src_cell, attr)))

                cell.alignment = Alignment(
                    vertical='center',
                    horizontal='right' if col_idx >= 4 else 'left',
                    wrap_text=(col_idx == 2)
                )
                cell.number_format = NUMBER_FORMAT if col_idx >= 4 else ('@' if col_idx == 3 else src_cell.number_format)

            ws.row_dimensions[row_idx].height = max(20, 16 * ceil(len(res['tipo']) / 65))

        # Estilo del encabezado y anchos de columnas en hoja principal
        anchos = (18, 74, 21, 20, 18, 18, 18, 18, 18, 21)
        for col_idx, width in enumerate(anchos, start=1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width
            h_cell = ws.cell(1, col_idx)
            h_cell.font = Font(name='Calibri', size=11, bold=True)
            h_cell.fill = PatternFill('solid', fgColor='E7E6E6')
            h_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        ws.row_dimensions[1].height = 32
        ws.freeze_panes = 'D2'
        ws.auto_filter.ref = f"A1:J{ws.max_row}"
        ws.sheet_view.zoomScale = 85

        # -------------------------------------------------------------
        # 2. Hoja de Control y Cuadre: se calcula sobre los valores efectivamente
        #    escritos en la hoja principal, no sobre la partición de cargos.
        # -------------------------------------------------------------
        cuadre = calcular_cuadre(
            cargos_todos,
            ws.iter_rows(min_row=2, max_col=len(HEADERS), values_only=True)
        )
        crear_hoja_auditoria(wb_salida, cuadre)

        # -------------------------------------------------------------
        # 3. Hoja de Cargos No Conciliados / Pendientes
        # -------------------------------------------------------------
        ws_pend = wb_salida.create_sheet(title='No Conciliados')
        ws_pend.sheet_properties.tabColor = "FFC000" if cargos_pend else "70AD47"
        ws_pend.append(HEADERS_PENDIENTES)

        ids_movs = {m['id'] for m in (movimientos or [])}

        if cargos_pend:
            for row_idx, c in enumerate(cargos_pend, start=2):
                f_ret = c['date'].strftime('%d/%m/%Y') if hasattr(c['date'], 'strftime') else str(c['date'])
                f_op = c['op_date'].strftime('%d/%m/%Y') if hasattr(c['op_date'], 'strftime') else str(c['op_date'])

                valores_pend = (
                    c['sheet'],
                    c['row'],
                    c['id'],
                    f_ret,
                    f_op,
                    float(c['base']),
                    float(c['amount']),
                    motivo_pendiente(c, ids_movs)
                )
                for col_idx, val in enumerate(valores_pend, start=1):
                    cell = ws_pend.cell(row_idx, col_idx, val)
                    cell.font = Font(name='Calibri', size=10)
                    cell.alignment = Alignment(
                        vertical='center',
                        horizontal='right' if col_idx in (6, 7) else ('left' if col_idx == 8 else 'center')
                    )
                    if col_idx in (6, 7):
                        cell.number_format = NUMBER_FORMAT
                    elif col_idx in (2, 3):
                        cell.number_format = '@'

                ws_pend.row_dimensions[row_idx].height = 20

            # Fila totalizadora de cargos no asociados
            total_row_idx = len(cargos_pend) + 2
            total_amt = float(sum((c['amount'] for c in cargos_pend), ZERO))
            ws_pend.cell(total_row_idx, 1, 'TOTAL PENDIENTE')
            ws_pend.cell(total_row_idx, 7, total_amt)
            ws_pend.cell(total_row_idx, 8, f"{len(cargos_pend)} cargos sin asociar")

            for col_idx in range(1, 9):
                cell = ws_pend.cell(total_row_idx, col_idx)
                cell.font = Font(name='Calibri', size=11, bold=True)
                if col_idx == 7:
                    cell.number_format = NUMBER_FORMAT
                    cell.alignment = Alignment(horizontal='right', vertical='center')
                cell.fill = PatternFill('solid', fgColor='F2DCDB')
            ws_pend.row_dimensions[total_row_idx].height = 22
            ws_pend.auto_filter.ref = f"A1:H{len(cargos_pend) + 1}"
        else:
            ws_pend.cell(2, 1, "Sin cargos pendientes: el 100% de las retenciones y deducciones fue conciliado con éxito.")
            ws_pend.cell(2, 1).font = Font(name='Calibri', size=11, italic=True, color='375623')
            ws_pend.row_dimensions[2].height = 25

        # Estilo del encabezado en hoja No Conciliados
        anchos_pend = (16, 14, 24, 18, 18, 18, 18, 60)
        for col_idx, width in enumerate(anchos_pend, start=1):
            ws_pend.column_dimensions[get_column_letter(col_idx)].width = width
            h_cell = ws_pend.cell(1, col_idx)
            h_cell.font = Font(name='Calibri', size=11, bold=True)
            h_cell.fill = PatternFill('solid', fgColor='FFF2CC' if cargos_pend else 'E2EFDA')
            h_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        ws_pend.row_dimensions[1].height = 28
        ws_pend.freeze_panes = 'A2'
        ws_pend.sheet_view.zoomScale = 85

        archivo_destino.parent.mkdir(parents=True, exist_ok=True)
        destino_final = archivo_destino
        try:
            wb_salida.save(archivo_destino)
        except PermissionError:
            import time
            ts = int(time.time())
            destino_final = archivo_destino.with_name(f"{archivo_destino.stem}_{ts}.xlsx")
            wb_salida.save(destino_final)
            print(f"-> AVISO: El archivo '{archivo_destino.name}' está abierto en Excel.")
            print(f"-> Se guardó como copia alternativa en: {destino_final.name}")

        return destino_final
    finally:
        template.close()
        wb_salida.close()


def _usuario_sistema() -> str:
    try:
        import getpass
        return f'{getpass.getuser()} (consola)'
    except Exception:
        return 'consola'


def main():
    parser = argparse.ArgumentParser(description="Conciliación automatizada de Mercado Pago")
    parser.add_argument('--archivo', type=Path, default=ROOT / 'docs' / 'MP 2025-12 (M).xlsx')
    parser.add_argument('--salida', type=Path, default=ROOT / 'outputs')
    parser.add_argument('--periodo', default=None, help="Período YYYY-MM (se auto-detecta si no se especifica)")
    parser.add_argument('--hoja', default='sheet0')
    parser.add_argument('--no-registrar', action='store_true',
                        help="No guardar la corrida en el historial (data/conciliaciones.db)")
    args = parser.parse_args()

    periodo = args.periodo or detectar_periodo(args.archivo.name)
    if not periodo:
        parser.error(
            f"No se pudo detectar el período en '{args.archivo.name}'. "
            "Indicalo con --periodo YYYY-MM."
        )
    if not PATRON_PERIODO.fullmatch(periodo):
        parser.error(f"Período inválido: '{periodo}'. Formato esperado: YYYY-MM.")

    print("=" * 60)
    print(f" Iniciando Conciliación de Mercado Pago ({periodo})")
    print("=" * 60)

    movimientos, cargos = cargar_datos(args.archivo, periodo, args.hoja)
    print(f"-> Movimientos leídos de '{args.hoja}': {len(movimientos)}")
    print(f"-> Retenciones y cargos leídos: {len(cargos)}")
    if not movimientos:
        print(f"-> ERROR: no hay movimientos del período {periodo} en la hoja '{args.hoja}'.")
        raise SystemExit(1)

    asociar_cargos(movimientos, cargos)
    cargos_asociados = sum(1 for c in cargos if c['target'] is not None)
    cargos_pendientes = [c for c in cargos if c['target'] is None]

    print(f"-> Cargos asociados con éxito: {cargos_asociados}")
    if cargos_pendientes:
        print(f"-> Cargos NO conciliados: {len(cargos_pendientes)} (detallados en pestaña 'No Conciliados')")
    else:
        print("-> Cargos NO conciliados: 0 (100% conciliado con éxito)")

    resultados = calcular_totales(movimientos)

    excel_salida = args.salida / f"conciliacion_{periodo}.xlsx"
    print(f"-> Generando Excel con totales y auditoría en: {excel_salida.name}")
    guardado_en = generar_excel(
        archivo_origen=args.archivo,
        archivo_destino=excel_salida,
        resultados=resultados,
        hoja_tp=args.hoja,
        cargos_pendientes=cargos_pendientes,
        movimientos=movimientos,
        todos_los_cargos=cargos,
        periodo=periodo
    )

    cuadre = validar_cuadre_excel(guardado_en, cargos)
    metricas = calcular_metricas(movimientos, cargos, resultados)

    print("-" * 60)
    print(f" Ingresos: {metricas['ingresos']:,.2f} | Egresos: {metricas['egresos']:,.2f} | Balance: {metricas['balance']:,.2f}")
    print(f" Monto no conciliado: {metricas['monto_pendiente']:,.2f} ({metricas['porcentaje_asociado']}% asociado)")
    print(" Control y Cuadre (Total extracto - Imputado - No conciliado):")
    for d in cuadre['detalle']:
        estado = 'OK' if d['ok'] else 'DESCUADRADO'
        print(f"   {d['concepto']:<28} diferencia {d['diferencia']:>14,.2f}  {estado}")
    print(f"   {'TOTAL':<28} diferencia {cuadre['total']['diferencia']:>14,.2f}  {'OK' if cuadre['total']['ok'] else 'DESCUADRADO'}")
    print(f" Validación MOV TOTAL: {cuadre['filas_validadas']} filas, {len(cuadre['filas_con_error'])} con error")

    if not args.no_registrar:
        try:
            import db
            db.init_db()
            huella = huella_datos(movimientos, cargos)
            anterior = db.ultima_corrida(periodo)
            estado = comparar_con_anterior(anterior, huella)
            corrida_id = db.registrar_corrida(
                periodo=periodo,
                archivo=args.archivo.name,
                canal='cli',
                chat_id=None,
                usuario=_usuario_sistema(),
                huella=huella,
                metricas=metricas,
                cuadre=cuadre,
                resultados=resultados,
                pendientes=detalle_pendientes(movimientos, cargos),
            )
            print(f" Corrida registrada en el historial (id {corrida_id}): {db.DB_PATH}")
            if estado == 'identico':
                print(f" Mismo extracto que la corrida #{anterior['id']} ({anterior['fecha_ejecucion']}): los datos no cambian.")
            elif estado in ('distinto', 'sin_huella'):
                aclaracion = 'con datos distintos' if estado == 'distinto' else 'sin huella para comparar'
                print(f" AVISO: reemplaza a la corrida #{anterior['id']} de {periodo} ({aclaracion}) en los resúmenes.")
        except Exception as e:
            print(f" AVISO: no se pudo registrar la corrida en el historial: {e}")

    print("=" * 60)
    if cuadre['ok']:
        print(" Proceso finalizado correctamente!")
    else:
        print(" Proceso finalizado CON OBSERVACIONES: revisar la pestaña 'Control y Cuadre'.")
    print(f" Archivo listo en: {guardado_en.resolve()}")
    print("=" * 60)


if __name__ == '__main__':
    main()

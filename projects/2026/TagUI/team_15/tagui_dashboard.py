from collections import defaultdict
import dolar
from excel_manager import HOJA_GASTOS, abrir_hoja, asegurar_hojas

NOMBRE_DASHBOARD = "Dashboard"

COLOR_ENCABEZADO = {"red": 0.12, "green": 0.31, "blue": 0.47}

_COLUMNA_CARTEL = 4
_ULTIMA_FILA_CARTEL = 7

_CARTEL_TIPOS = [
    ("oficial", "Dólar Oficial"),
    ("blue", "Dólar Blue"),
    ("bolsa", "Dólar MEP"),
]


def _leer_gastos(sh):
    ws_gastos = sh.worksheet(HOJA_GASTOS)
    return [
        {
            "categoria": str(fila[1]),
            "monto": float(fila[3] or 0),
            "moneda": str(fila[4]),
        }
        for fila in ws_gastos.get_all_values()[1:]
        if fila and fila[0]
    ]


def _agregar_cartel_dolar(celdas, info) -> bool:
    cotizaciones = info.get("cotizaciones", {})
    if not cotizaciones:
        return False
    celdas[(3, _COLUMNA_CARTEL)] = "Dólar hoy"
    fila = 4
    for tipo, nombre in _CARTEL_TIPOS:
        c = cotizaciones.get(tipo)
        if not c:
            continue
        celdas[(fila, _COLUMNA_CARTEL)] = nombre
        celdas[(fila, _COLUMNA_CARTEL + 1)] = "Compra: " + dolar.formatear_precio(c["compra"])
        celdas[(fila, _COLUMNA_CARTEL + 2)] = "Venta: " + dolar.formatear_precio(c["venta"])
        fila += 1
    if info.get("actualizado"):
        celdas[(fila, _COLUMNA_CARTEL)] = "Actualizado: " + info["actualizado"]
    return True


def generar_dashboard(sheet_id: str, credenciales: str) -> str:
    asegurar_hojas(sheet_id, credenciales)
    sh = abrir_hoja(sheet_id, credenciales)

    datos = _leer_gastos(sh)

    for wsx in sh.worksheets():
        if wsx.title == NOMBRE_DASHBOARD:
            sh.del_worksheet(wsx)
    ws = sh.add_worksheet(title=NOMBRE_DASHBOARD, rows=200, cols=22)

    por_moneda = defaultdict(float)
    por_categoria_por_moneda = defaultdict(lambda: defaultdict(float))
    for d in datos:
        por_moneda[d["moneda"]] += d["monto"]
        por_categoria_por_moneda[d["moneda"]][d["categoria"]] += d["monto"]

    monedas = sorted(por_moneda.keys(),
                     key=lambda m: (m != "ARS", m != "USD", m))

    celdas = {}
    celdas[(1, 1)] = "Resumen de Gastos"
    celdas[(3, 1)] = "Cantidad de gastos:"
    celdas[(3, 2)] = len(datos)

    fila_resumen = 4
    for moneda in monedas:
        celdas[(fila_resumen, 1)] = f"Total {moneda}:"
        celdas[(fila_resumen, 2)] = por_moneda[moneda]
        fila_resumen += 1

    try:
        info_dolar = dolar.obtener_cotizaciones_dolar()
    except Exception:
        info_dolar = {}
    cartel_activado = _agregar_cartel_dolar(celdas, info_dolar)

    tablas = []
    columna = 1
    for moneda in monedas:
        fila = 7
        celdas[(fila, columna)] = f"Gastos en {moneda}"
        fila += 1
        inicio = fila
        celdas[(fila, columna)] = "Categoría"
        celdas[(fila, columna + 1)] = f"Monto ({moneda})"

        fila_datos = fila + 1
        totales = por_categoria_por_moneda[moneda]
        for cat, monto in sorted(totales.items(), key=lambda x: -x[1]):
            celdas[(fila_datos, columna)] = cat
            celdas[(fila_datos, columna + 1)] = monto
            fila_datos += 1

        if totales:
            tablas.append((moneda, inicio, fila_datos, columna))
        columna += 11

    max_fila = max(r for r, _ in celdas)
    max_col = max(c for _, c in celdas)
    grilla = [["" for _ in range(max_col)] for _ in range(max_fila)]
    for (r, c), valor in celdas.items():
        grilla[r - 1][c - 1] = valor

    ws.update("A1", grilla)

    requests = []
    for moneda, inicio, fila_datos, col in tablas:
        requests.append({
            "addChart": {
                "chart": {
                    "spec": {
                        "title": f"Gastos por categoría ({moneda})",
                        "pieChart": {
                            "legendPosition": "RIGHT_LEGEND",
                            "threeDimensional": False,
                            "domain": {
                                "sourceRange": {
                                    "sources": [{
                                        "sheetId": ws.id,
                                        "startRowIndex": inicio,
                                        "endRowIndex": fila_datos - 1,
                                        "startColumnIndex": col - 1,
                                        "endColumnIndex": col,
                                    }]
                                }
                            },
                            "series": {
                                "sourceRange": {
                                    "sources": [{
                                        "sheetId": ws.id,
                                        "startRowIndex": inicio,
                                        "endRowIndex": fila_datos - 1,
                                        "startColumnIndex": col,
                                        "endColumnIndex": col + 1,
                                    }]
                                }
                            },
                        },
                    },
                    "position": {
                        "overlayPosition": {
                            "anchorCell": {
                                "sheetId": ws.id,
                                "rowIndex": 6,
                                "columnIndex": col + 4,
                            }
                        }
                    },
                }
            }
        })

    requests.append({
        "repeatCell": {
            "range": {"sheetId": ws.id, "startRowIndex": 0, "endRowIndex": 1,
                      "startColumnIndex": 0, "endColumnIndex": 2},
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": COLOR_ENCABEZADO,
                    "textFormat": {"bold": True, "fontSize": 14,
                                   "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }
    })

    if cartel_activado:
        requests.append({
            "repeatCell": {
                "range": {"sheetId": ws.id, "startRowIndex": 2, "endRowIndex": 3,
                          "startColumnIndex": 3, "endColumnIndex": _COLUMNA_CARTEL + 3},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": COLOR_ENCABEZADO,
                        "textFormat": {"bold": True, "fontSize": 12,
                                       "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        })
        requests.append({
            "repeatCell": {
                "range": {"sheetId": ws.id, "startRowIndex": 3,
                          "endRowIndex": _ULTIMA_FILA_CARTEL,
                          "startColumnIndex": 3, "endColumnIndex": _COLUMNA_CARTEL + 3},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.98, "green": 0.93, "blue": 0.85},
                    }
                },
                "fields": "userEnteredFormat.backgroundColor",
            }
        })

    sh.batch_update({"requests": requests})

    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"
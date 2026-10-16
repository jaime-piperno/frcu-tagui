import gspread

ENCABEZADOS = ["Fecha", "Categoría", "Descripción", "Monto", "Moneda"]

HOJA_GASTOS = "Gastos"

_cliente = None


def _obtener_cliente(credenciales: str):
    global _cliente
    if _cliente is None:
        _cliente = gspread.service_account(filename=credenciales)
    return _cliente


def abrir_hoja(sheet_id: str, credenciales: str):
    return _obtener_cliente(credenciales).open_by_key(sheet_id)


def asegurar_hojas(sheet_id: str, credenciales: str) -> None:
    sh = abrir_hoja(sheet_id, credenciales)
    titulos = [ws.title for ws in sh.worksheets()]
    if HOJA_GASTOS not in titulos:
        ws = sh.add_worksheet(title=HOJA_GASTOS, rows=1000, cols=5)
        ws.append_row(ENCABEZADOS)


class ExcelManager:
    def __init__(self, sheet_id: str, credenciales: str):
        self.sheet_id = sheet_id
        self.credenciales = credenciales

    def _hoja_gastos(self):
        asegurar_hojas(self.sheet_id, self.credenciales)
        return abrir_hoja(self.sheet_id, self.credenciales).worksheet(HOJA_GASTOS)

    def registrar(self, gasto) -> None:
        ws = self._hoja_gastos()
        ws.append_row([
            gasto.fecha,
            gasto.categoria,
            gasto.descripcion,
            gasto.monto,
            gasto.moneda,
        ])

    def leer_todos(self):
        ws = self._hoja_gastos()
        return [
            {
                "fecha": fila[0],
                "categoria": str(fila[1]),
                "descripcion": fila[2],
                "monto": float(fila[3] or 0),
                "moneda": str(fila[4]),
            }
            for fila in ws.get_all_values()[1:]
            if fila and fila[0]
        ]
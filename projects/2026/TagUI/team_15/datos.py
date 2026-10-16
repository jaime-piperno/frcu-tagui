from dataclasses import dataclass
from datetime import datetime

_HOY = lambda: datetime.now().strftime("%Y-%m-%d")


@dataclass
class Gasto:
    descripcion: str = ""
    monto: float = 0.0
    moneda: str = "ARS"
    categoria: str = "Otros"
    fecha: str = None

    def __post_init__(self):
        if not self.fecha:
            self.fecha = _HOY()

    def resumen(self) -> str:
        return (
            f"Categoría: {self.categoria}\n"
            f"Descripción: {self.descripcion}\n"
            f"Monto: {self.monto:,.2f} {self.moneda}\n"
            f"Fecha: {self.fecha}"
        )

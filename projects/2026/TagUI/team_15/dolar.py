import re

import httpx

URL_DOLARHOY = "https://dolarhoy.com/"

TIPOS = {
    "oficial": "Dólar Oficial",
    "blue": "Dólar Blue",
    "bolsa": "Dólar MEP",
    "contadoconliqui": "Dólar CCL",
    "mayorista": "Dólar Mayorista",
}

ORDEN_TIPOS = ["oficial", "blue", "bolsa", "contadoconliqui", "mayorista"]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

_RE_PRECIO = re.compile(r'<div class="val"[^>]*>\$([\d.,]+)')
_RE_PAR = re.compile(
    r'<div class="compra">([\d.,]+)</div><div class="venta">([\d.,]+)</div>'
)
_RE_TIPO = re.compile(r'href="/cotizaciondolar([a-z0-9_-]+)"')
_RE_HORA = re.compile(r"\d{2}/\d{2}/\d{2} \d{2}:\d{2} (?:AM|PM)")


def _limpiar_precio(valor: str) -> float:
    return float(re.sub(r"[^\d,]", "", valor).replace(",", "."))


def formatear_precio(valor: float) -> str:
    entero, decimales = f"{valor:.2f}".split(".")
    grupos = []
    while len(entero) > 3:
        grupos.insert(0, entero[-3:])
        entero = entero[:-3]
    grupos.insert(0, entero)
    entero = ".".join(grupos)
    return f"${entero}" if decimales == "00" else f"${entero},{decimales}"


def _parsear(pagina: str) -> dict:
    cotizaciones = {}
    for bloque in pagina.split('class="tile is-child"')[1:]:
        m = _RE_TIPO.search(bloque)
        if not m:
            continue
        tipo = m.group(1)
        if tipo not in TIPOS or tipo in cotizaciones:
            continue
        valores = _RE_PRECIO.findall(bloque)
        if len(valores) >= 2:
            compra, venta = valores[:2]
        else:
            par = _RE_PAR.search(bloque)
            if not par:
                continue
            compra, venta = par.groups()
        cotizaciones[tipo] = {
            "compra": _limpiar_precio(compra),
            "venta": _limpiar_precio(venta),
        }

    m_hora = _RE_HORA.search(pagina)
    actualizado = m_hora.group(0) if m_hora else None
    return {
        "cotizaciones": cotizaciones,
        "actualizado": actualizado,
    }


def obtener_cotizaciones_dolar(timeout: float = 20.0) -> dict:
    resp = httpx.get(
        URL_DOLARHOY, headers=_HEADERS, timeout=timeout, follow_redirects=True
    )
    resp.raise_for_status()
    return _parsear(resp.text)
import json
import re
import time
from datetime import date

import httpx
from google import genai

import config
from categorias import CATEGORIAS, MONEDAS
from datos import Gasto

MODELO = config.LLM_MODELO
MAX_REINTENTOS = 3

HOY = date.today().isoformat()

PROMPT_SISTEMA = f"""Sos un asistente que convierte mensajes de gastos personales en datos estructurados.

El usuario escribe uno o varios gastos en lenguaje natural, en cualquier formato y moneda.
Hoy es {HOY}. La fecha de hoy en días de la semana: lunes=1, martes=2, miercoles=3, jueves=4, viernes=5, sabado=6, domingo=7.
Respondé SOLO con JSON válido (sin texto adicional, sin markdown): una LISTA de objetos, aunque sea un solo gasto.
Forma: [{{"descripcion": "...", "monto": 1234.56, "moneda": "ARS", "categoria": "comida", "fecha": "YYYY-MM-DD"}}]

Reglas:
- Contá los gastos UNO POR UNO. Cada gasto tiene su PROPIO monto/número. Si el mensaje menciona varios gastos (ej: "8000 de alcohol y 5000 de comida", "empanadas 7000 y credito 15 usd ayer"), devolvé **un objeto por cada uno**. NUNCA fusiones dos importes en un solo objeto.
- Si no se puede distinguir más de un gasto, devolvé UNA lista con un solo objeto.
- descripcion: texto corto (max 40 caracteres) que describe el gasto, sin el monto.
- monto: número positivo. Si el texto tiene varios números, elegí el que corresponde al importe de ese gasto.
- moneda: una de estas opciones: {", ".join(MONEDAS)}. Por defecto ARS si no se indica otra.
- fecha: en formato YYYY-MM-DD. Interpretá la fecha mencionada ("ayer", "mañana", "el lunes pasado", "5 de julio", "hace dos días") calculándola a partir de HOY. Si el mensaje NO menciona fecha, usá HOY.
- categoria: UNA de estas opciones: {", ".join(CATEGORIAS)}.
  - comida: comidas, supermercado, restaurantes, bares, delivery.
  - transporte: uber, taxi, colectivo, subte, nafta, viajes, peajes.
  - vivienda: alquiler, expensas, servicios (luz, agua, internet, gas), impuestos.
  - salud: farmacia, médicos, dentista, medicamentos.
  - educacion: universidad, cursos, libros, cuotas.
  - entretenimiento: cine, streaming, juegos, conciertos, salidas, joda, boliche, barras, alcohol.
  - ropa: ropa y calzado.
  - salario: sueldos o ingresos.
  - otros: si no encaja en ninguna.

Si no hay un monto claro, devolvé monto 0."""


_cliente = None


def _obtener_cliente() -> genai.Client:
    global _cliente
    if _cliente is None:
        _cliente = genai.Client(api_key=config.GEMINI_API_KEY)
    return _cliente


def _normalizar_objeto(datos: dict) -> Gasto:
    monto = float(datos.get("monto", 0) or 0)
    moneda = str(datos.get("moneda", "ARS")).upper()
    categoria = str(datos.get("categoria", "otros")).lower()
    if moneda not in MONEDAS:
        moneda = "ARS"
    if categoria not in CATEGORIAS:
        categoria = "otros"
    descripcion = str(datos.get("descripcion", "")).strip()

    fecha = str(datos.get("fecha", "")).strip()
    if not fecha:
        fecha = HOY
    else:
        try:
            date.fromisoformat(fecha)
        except ValueError:
            fecha = HOY

    return Gasto(
        descripcion=descripcion or "Sin descripcion",
        monto=monto,
        moneda=moneda,
        categoria=categoria,
        fecha=fecha,
    )


def _parsear_json(texto: str) -> list:
    """Limpia la respuesta (code fences/markdown) y la convierte a lista de dicts."""
    contenido = texto.strip()
    if contenido.startswith("```"):
        contenido = re.sub(r"^```[a-zA-Z]*\s*", "", contenido)
        contenido = re.sub(r"\s*```$", "", contenido)
    datos = json.loads(contenido)
    if isinstance(datos, dict):
        datos = [datos]
    return datos


def interpretar_llm(texto: str) -> list:
    for intento in range(1, MAX_REINTENTOS + 1):
        try:
            response = _obtener_cliente().models.generate_content(
                model=MODELO,
                contents=f"{PROMPT_SISTEMA}\n\nGasto del usuario: {texto}",
            )
            datos = _parsear_json(response.text)
            return [_normalizar_objeto(d) for d in datos]
        except Exception:
            if intento == MAX_REINTENTOS:
                raise
            time.sleep(2 * intento)


def _clave_openrouter_valida() -> bool:
    clave = (config.OPENROUTER_API_KEY or "").strip()
    return bool(clave) and "..." not in clave and len(clave) >= 32


def _clave_gemini_valida() -> bool:
    clave = (config.GEMINI_API_KEY or "").strip()
    return bool(clave) and "..." not in clave and len(clave) >= 10


def interpretar_openrouter(texto: str) -> list:
    """Interpreta con OpenRouter (API compatible con OpenAI)."""
    modelos = list(dict.fromkeys([
        config.OPENROUTER_MODELO,
        "z-ai/glm-5.2:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-31b-it:free",
        "openrouter/free",
    ]))

    for modelo in modelos:
        for intento in range(1, MAX_REINTENTOS + 1):
            try:
                resp = httpx.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": modelo,
                        "messages": [
                            {"role": "system", "content": PROMPT_SISTEMA},
                            {"role": "user", "content": texto},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0,
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                contenido = resp.json()["choices"][0]["message"]["content"]
                return [_normalizar_objeto(d) for d in _parsear_json(contenido)]
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403):
                    raise ValueError(
                        "La OPENROUTER_API_KEY no es válida (error "
                        f"{e.response.status_code}). Revisá la key en .env."
                    )
                if intento == MAX_REINTENTOS:
                    break
                time.sleep((5 if e.response.status_code == 429 else 2) * intento)
            except Exception:
                if intento == MAX_REINTENTOS:
                    break
                time.sleep(2 * intento)

    raise RuntimeError(
        "OpenRouter no respondió en ninguno de los modelos probados. "
        "Intentá de nuevo en unos minutos."
    )


def _dividir_en_fragmentos(texto: str) -> list:
    """Divide un mensaje con varios gastos en fragmentos con monto propio."""
    texto = texto.strip()
    separadores = r"\s+(?:y|e)\s+|[,;]|(?<=\d)\s+por\s+"
    fragmentos = [f.strip() for f in re.split(separadores, texto) if f.strip()]
    con_numero = [f for f in fragmentos if re.search(r"\d", f)]
    if len(con_numero) < 2:
        return [texto]
    return fragmentos


def interpretar(texto: str) -> list:
    """Interpreta el mensaje con el LLM configurado. Devuelve una lista de Gasto."""
    if not texto or not texto.strip():
        raise ValueError("El mensaje está vacío.")

    if config.OPENROUTER_API_KEY:
        if not _clave_openrouter_valida():
            raise ValueError(
                "La OPENROUTER_API_KEY en .env está incompleta o es inválida. "
                "Pegá la key completa (empieza con sk-or-v1-)."
            )
        gastos = interpretar_openrouter(texto)
    elif config.GEMINI_API_KEY:
        if not _clave_gemini_valida():
            raise ValueError(
                "La GEMINI_API_KEY en .env está incompleta. Revisala."
            )
        gastos = interpretar_llm(texto)
    else:
        raise RuntimeError(
            "No hay ninguna API key configurada. Definí OPENROUTER_API_KEY "
            "o GEMINI_API_KEY en .env"
        )

    if len(gastos) <= 1:
        fragmentos = _dividir_en_fragmentos(texto)
        if len(fragmentos) > 1:
            combinados = []
            for frag in fragmentos:
                try:
                    if config.OPENROUTER_API_KEY:
                        combinados.extend(interpretar_openrouter(frag))
                    else:
                        combinados.extend(interpretar_llm(frag))
                except Exception:
                    continue
            unicos = []
            vistos = set()
            for g in combinados:
                clave = (g.descripcion.strip().lower(), round(g.monto, 2), g.moneda, g.categoria, g.fecha)
                if clave in vistos:
                    continue
                vistos.add(clave)
                unicos.append(g)
            if len(unicos) > len(gastos):
                gastos = unicos
    return gastos
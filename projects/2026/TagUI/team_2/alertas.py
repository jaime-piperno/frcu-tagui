import json
import os
import tempfile
import threading
import pandas as pd
from typing import List, Dict

from config import ALERTAS_PATH, VISTOS_PATH

_IO_LOCK = threading.Lock()


def _guardar_json_atomico(ruta_archivo: str, datos: dict):
    """Guarda un diccionario como JSON de forma atómica y thread-safe."""
    with _IO_LOCK:
        dir_name = os.path.dirname(ruta_archivo) or '.'
        os.makedirs(dir_name, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
            json.dump(datos, tf, ensure_ascii=False, indent=2)
            temp_name = tf.name
        os.replace(temp_name, ruta_archivo)


def cargar_alertas() -> dict:
    with _IO_LOCK:
        if not os.path.isfile(ALERTAS_PATH):
            return {}
        try:
            with open(ALERTAS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}


def guardar_alertas(alertas: dict):
    _guardar_json_atomico(ALERTAS_PATH, alertas)

def obtener_alertas(chat_id: int) -> dict:
    alertas = cargar_alertas()
    return alertas.get(str(chat_id), {})

def guardar_alerta(chat_id: int, nombre_alerta: str, rubro: str, tipo_proceso: str, estado_proceso: str, tipo_operacion: str, solo_catalogo: bool = False):
    alertas = cargar_alertas()
    chat_id_str = str(chat_id)

    if chat_id_str not in alertas:
        alertas[chat_id_str] = {}

    alertas[chat_id_str][nombre_alerta] = {
        'rubro': rubro,
        'tipo_proceso': tipo_proceso,
        'estado_proceso': estado_proceso,
        'tipo_operacion': tipo_operacion,
        # Periodo is implicit (e.g. last 48 hours) for alerts
        'solo_catalogo': solo_catalogo,
    }

    guardar_alertas(alertas)

def eliminar_alerta(chat_id: int, nombre_alerta: str) -> bool:
    alertas = cargar_alertas()
    chat_id_str = str(chat_id)

    if chat_id_str in alertas and nombre_alerta in alertas[chat_id_str]:
        del alertas[chat_id_str][nombre_alerta]
        guardar_alertas(alertas)
        return True
    return False

def cargar_vistos() -> dict:
    with _IO_LOCK:
        if not os.path.isfile(VISTOS_PATH):
            return {}
        try:
            with open(VISTOS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}


def guardar_vistos(vistos: dict):
    _guardar_json_atomico(VISTOS_PATH, vistos)

def obtener_ids_nuevos(chat_id: int, nombre_alerta: str, ids_encontrados: List[str]) -> List[str]:
    vistos = cargar_vistos()
    chat_id_str = str(chat_id)

    if chat_id_str not in vistos:
        vistos[chat_id_str] = {}

    if nombre_alerta not in vistos[chat_id_str]:
        vistos[chat_id_str][nombre_alerta] = []

    ids_vistos = set(vistos[chat_id_str][nombre_alerta])
    ids_nuevos = [id_ for id_ in ids_encontrados if id_ not in ids_vistos]

    return ids_nuevos

def marcar_como_vistos(chat_id: int, nombre_alerta: str, nuevos_ids: List[str]):
    if not nuevos_ids:
        return

    vistos = cargar_vistos()
    chat_id_str = str(chat_id)

    if chat_id_str not in vistos:
        vistos[chat_id_str] = {}

    if nombre_alerta not in vistos[chat_id_str]:
        vistos[chat_id_str][nombre_alerta] = []

    vistos[chat_id_str][nombre_alerta].extend(nuevos_ids)

    # Mantener un límite para no crecer infinitamente (ej. últimos 1000)
    if len(vistos[chat_id_str][nombre_alerta]) > 1000:
        vistos[chat_id_str][nombre_alerta] = vistos[chat_id_str][nombre_alerta][-1000:]

    guardar_vistos(vistos)

def extraer_ids_de_excel(ruta_excel: str) -> List[str]:
    try:
        # Extrae la columna de IDs del excel. Suele llamarse 'Número de Proceso' o similar.
        df = pd.read_excel(ruta_excel)

        # Intentamos encontrar la columna de ID. Puede llamarse de varias formas.
        posibles_nombres = ['Número de Proceso', 'Numero de Proceso', 'Número', 'Expediente', 'N°']
        col_id = None
        for col in df.columns:
            if any(nombre.lower() in col.lower() for nombre in posibles_nombres):
                col_id = col
                break

        if col_id:
            return df[col_id].dropna().astype(str).tolist()
        else:
            # Si no encontramos columna obvia, usamos la primera columna
            return df.iloc[:, 0].dropna().astype(str).tolist()
    except Exception as e:
        print(f"Error al extraer IDs del excel: {e}")
        return []


from catalogo import limpiar_texto_markdown


def obtener_resumen_coincidencias_excel(ruta_excel: str, ids_filtrar: List[str] = None) -> dict:
    """
    Revisa el reporte Excel enriquecido y devuelve:
      - ids_con_match: lista de IDs de proceso que coinciden con el catálogo de la empresa.
      - detalles: lista de textos descriptivos con el grado de coincidencia de cada proceso.
    """
    resultado = {
        'ids_con_match': [],
        'detalles': [],
    }
    try:
        df = pd.read_excel(ruta_excel)
        if df.empty or 'Coincide con Catálogo' not in df.columns:
            return resultado

        col_id = df.columns[0]
        col_nombre = df.columns[2] if len(df.columns) > 2 else df.columns[0]
        ids_set = set(str(x).strip() for x in ids_filtrar) if ids_filtrar is not None else None

        for _, row in df.iterrows():
            proc_id = str(row[col_id]).strip()
            if ids_set is not None and proc_id not in ids_set:
                continue
            if str(row.get('Coincide con Catálogo', '')).strip() == 'SÍ':
                resultado['ids_con_match'].append(proc_id)
                nombre_proc = limpiar_texto_markdown(str(row.get(col_nombre, '')).strip())
                grado = limpiar_texto_markdown(str(row.get('Grado de Coincidencia', '')).strip())
                cant = limpiar_texto_markdown(str(row.get('Ítems Coincidentes', '')).strip())
                detalle = limpiar_texto_markdown(str(row.get('Detalle de Coincidencias', '')).strip())
                resultado['detalles'].append(
                    f"✅ `{limpiar_texto_markdown(proc_id)}` - {nombre_proc[:50]}\n"
                    f"   📊 Coincidencia: {cant} ({grado})\n"
                    f"   📦 {detalle[:120]}"
                )
    except Exception as e:
        print(f"Error al analizar coincidencias en Excel: {e}")
    return resultado

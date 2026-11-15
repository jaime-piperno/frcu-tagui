import json
import os
import tempfile
import threading

from config import CONFIGURACIONES_PATH

_PRESETS_LOCK = threading.Lock()


def _guardar_configuraciones_atomico(ruta_archivo: str, datos: dict):
    with _PRESETS_LOCK:
        dir_name = os.path.dirname(ruta_archivo) or '.'
        os.makedirs(dir_name, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
            json.dump(datos, tf, ensure_ascii=False, indent=2)
            temp_name = tf.name
        os.replace(temp_name, ruta_archivo)


def cargar_configuraciones():
    with _PRESETS_LOCK:
        if not os.path.isfile(CONFIGURACIONES_PATH):
            return {}
        try:
            with open(CONFIGURACIONES_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}


def obtener_presets(chat_id: int) -> dict:
    configuraciones = cargar_configuraciones()
    chat_id_str = str(chat_id)
    # Compatibilidad hacia atrás: si la raíz tiene 'rubro', no es formato de presets. Lo ignoramos o migramos.
    user_data = configuraciones.get(chat_id_str, {})
    if 'rubro' in user_data:
        # Formato viejo, lo sobreescribimos con un dict vacío para presets
        return {}
    return user_data


def obtener_preset_por_nombre(chat_id: int, nombre_preset: str) -> dict:
    presets = obtener_presets(chat_id)
    return presets.get(nombre_preset)


def guardar_preset(chat_id: int, nombre_preset: str, rubro: str, tipo_proceso: str, estado_proceso: str, tipo_operacion: str, periodo: str):
    configuraciones = cargar_configuraciones()
    chat_id_str = str(chat_id)

    if chat_id_str not in configuraciones or 'rubro' in configuraciones[chat_id_str]:
        configuraciones[chat_id_str] = {}

    configuraciones[chat_id_str][nombre_preset] = {
        'rubro': rubro,
        'tipo_proceso': tipo_proceso,
        'estado_proceso': estado_proceso,
        'tipo_operacion': tipo_operacion,
        'periodo': periodo,
    }

    _guardar_configuraciones_atomico(CONFIGURACIONES_PATH, configuraciones)


def eliminar_preset(chat_id: int, nombre_preset: str) -> bool:
    configuraciones = cargar_configuraciones()
    chat_id_str = str(chat_id)

    if chat_id_str in configuraciones and nombre_preset in configuraciones[chat_id_str]:
        del configuraciones[chat_id_str][nombre_preset]
        _guardar_configuraciones_atomico(CONFIGURACIONES_PATH, configuraciones)
        return True
    return False

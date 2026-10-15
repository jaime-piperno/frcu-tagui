import json
import os

from config import CONFIGURACIONES_PATH


def cargar_configuraciones():
    if not os.path.isfile(CONFIGURACIONES_PATH):
        return {}
    with open(CONFIGURACIONES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


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
    
    with open(CONFIGURACIONES_PATH, 'w', encoding='utf-8') as f:
        json.dump(configuraciones, f, ensure_ascii=False, indent=2)


def eliminar_preset(chat_id: int, nombre_preset: str) -> bool:
    configuraciones = cargar_configuraciones()
    chat_id_str = str(chat_id)
    
    if chat_id_str in configuraciones and nombre_preset in configuraciones[chat_id_str]:
        del configuraciones[chat_id_str][nombre_preset]
        with open(CONFIGURACIONES_PATH, 'w', encoding='utf-8') as f:
            json.dump(configuraciones, f, ensure_ascii=False, indent=2)
        return True
    return False

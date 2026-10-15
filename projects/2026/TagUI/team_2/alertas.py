import json
import os
import pandas as pd
from typing import List, Dict

from config import ALERTAS_PATH, VISTOS_PATH

def cargar_alertas() -> dict:
    if not os.path.isfile(ALERTAS_PATH):
        return {}
    with open(ALERTAS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def guardar_alertas(alertas: dict):
    with open(ALERTAS_PATH, 'w', encoding='utf-8') as f:
        json.dump(alertas, f, ensure_ascii=False, indent=2)

def obtener_alertas(chat_id: int) -> dict:
    alertas = cargar_alertas()
    return alertas.get(str(chat_id), {})

def guardar_alerta(chat_id: int, nombre_alerta: str, rubro: str, tipo_proceso: str, estado_proceso: str, tipo_operacion: str):
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
    if not os.path.isfile(VISTOS_PATH):
        return {}
    with open(VISTOS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def guardar_vistos(vistos: dict):
    with open(VISTOS_PATH, 'w', encoding='utf-8') as f:
        json.dump(vistos, f, ensure_ascii=False, indent=2)

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

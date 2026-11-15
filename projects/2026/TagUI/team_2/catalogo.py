import difflib
import os
import re
import tempfile
import threading
import unicodedata
import shutil
from typing import Dict, List, Tuple

import pandas as pd

from config import CATALOGO_PATH, RESULTADOS_DIR

_CATALOGO_LOCK = threading.Lock()
CATALOGO_BACKUP_PATH = os.path.join(RESULTADOS_DIR, 'catalogo_empresa.xlsx')

COLUMNAS_CATALOGO = ['Codigo', 'Descripcion', 'Palabras_Clave', 'Rubro']

STOPWORDS_ES = {
    'para', 'con', 'sin', 'por', 'del', 'las', 'los', 'una', 'uno', 'unos',
    'unas', 'tipo', 'uso', 'valor', 'segun', 'como', 'mas', 'menos', 'entre',
    'sobre', 'todo', 'toda', 'todos', 'todas', 'otro', 'otra', 'otros', 'otras',
}

ITEMS_CATALOGO_POR_DEFECTO = [
    {
        'Codigo': '2.3.2-1571.23',
        'Descripcion': 'Resma de papel A4 80g para fotocopiadora e impresión',
        'Palabras_Clave': 'resma, papel a4, fotocopiadora, papel obra, hojas',
        'Rubro': 'LIBRERIA,PAP. Y UTILES OFICINA',
    },
    {
        'Codigo': '4.3.6-4807.110',
        'Descripcion': 'Computadora de escritorio / PC / Notebook',
        'Palabras_Clave': 'computadora, notebook, pc, procesador, monitor, teclado',
        'Rubro': 'INFORMATICA',
    },
    {
        'Codigo': '2.9.5-2561.1',
        'Descripcion': 'Elementos e insumos de limpieza (lavandina, detergente, jabón)',
        'Palabras_Clave': 'lavandina, detergente, desinfectante, jabon liquido, limpieza, papel higienico',
        'Rubro': 'ELEMENTOS DE LIMPIEZA',
    },
    {
        'Codigo': '2.7.2-10031.13',
        'Descripcion': 'Chapas y perfiles metálicos de aluminio o acero',
        'Palabras_Clave': 'chapa, aluminio, acero, perfil metalico, hierro',
        'Rubro': 'METALURGIA',
    },
]


def normalizar_texto(texto: str) -> str:
    """Convierte a minúsculas, elimina tildes y reemplaza puntuación por espacios."""
    if not texto:
        return ''
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize('NFKD', texto)
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r'[^a-z0-9.\-]+', ' ', texto)
    return re.sub(r'\s+', ' ', texto).strip()


def extraer_tokens_relevantes(texto: str) -> set:
    """Extrae palabras significativas (>= 3 caracteres, sin stopwords)."""
    norm = normalizar_texto(texto)
    tokens = set()
    for token in norm.split():
        token_limpio = token.strip('.-')
        if len(token_limpio) >= 3 and token_limpio not in STOPWORDS_ES and not token_limpio.isdigit():
            tokens.add(token_limpio)
    return tokens


def generar_palabras_clave_automaticas(descripcion: str) -> str:
    """Genera una lista de palabras clave a partir de una descripción técnica de COMPR.AR."""
    if not descripcion:
        return ''
    # En COMPR.AR el primer segmento antes de ';' suele ser el nombre principal del ítem
    partes = str(descripcion).split(';')
    encabezado = partes[0].strip()
    tokens = list(extraer_tokens_relevantes(encabezado))
    if len(tokens) < 4:
        for extra in extraer_tokens_relevantes(descripcion):
            if extra not in tokens:
                tokens.append(extra)
            if len(tokens) >= 6:
                break
    return ', '.join(tokens[:6])


def limpiar_texto_markdown(texto: str) -> str:
    """
    Reemplaza caracteres especiales de Markdown V1 de Telegram (_, *, `, [, ])
    en textos dinámicos provenientes de comprar.gob.ar o del Excel para evitar
    errores BadRequest: Can't parse entities.
    """
    if not texto:
        return ''
    reemplazos = {
        '_': '-',
        '*': '',
        '`': "'",
        '[': '(',
        ']': ')',
    }
    resultado = str(texto)
    for orig, dest in reemplazos.items():
        resultado = resultado.replace(orig, dest)
    return resultado


def asegurar_catalogo_inicial() -> str:
    """Crea el archivo catalogo_empresa.xlsx con ítems de ejemplo si no existe o está vacío."""
    if not os.path.isfile(CATALOGO_PATH) or os.path.getsize(CATALOGO_PATH) == 0:
        # Si existe copia persistida en resultados/catalogo_empresa.xlsx, restaurarla
        if os.path.isfile(CATALOGO_BACKUP_PATH) and os.path.getsize(CATALOGO_BACKUP_PATH) > 0:
            shutil.copy2(CATALOGO_BACKUP_PATH, CATALOGO_PATH)
        else:
            df = pd.DataFrame(ITEMS_CATALOGO_POR_DEFECTO, columns=COLUMNAS_CATALOGO)
            guardar_catalogo(df)
    return CATALOGO_PATH


def cargar_catalogo() -> pd.DataFrame:
    """Carga el catálogo de la empresa desde el archivo Excel."""
    asegurar_catalogo_inicial()
    try:
        df = pd.read_excel(CATALOGO_PATH)
        # Asegurar que existan todas las columnas esperadas
        for col in COLUMNAS_CATALOGO:
            if col not in df.columns:
                df[col] = ''
        df = df[COLUMNAS_CATALOGO].fillna('')
        return df
    except Exception as e:
        print(f"Error al leer catalogo_empresa.xlsx ({e}). Recreando catálogo base.")
        df = pd.DataFrame(ITEMS_CATALOGO_POR_DEFECTO, columns=COLUMNAS_CATALOGO)
        guardar_catalogo(df)
        return df


def guardar_catalogo(df: pd.DataFrame):
    """Guarda el DataFrame del catálogo en catalogo_empresa.xlsx de forma atómica y sincroniza copia en resultados/."""
    with _CATALOGO_LOCK:
        for col in COLUMNAS_CATALOGO:
            if col not in df.columns:
                df[col] = ''
        df = df[COLUMNAS_CATALOGO].fillna('')

        dir_name = os.path.dirname(CATALOGO_PATH) or '.'
        with tempfile.NamedTemporaryFile('wb', dir=dir_name, suffix='.xlsx', delete=False) as tf:
            temp_path = tf.name

        try:
            df.to_excel(temp_path, index=False, engine='openpyxl')
            os.replace(temp_path, CATALOGO_PATH)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

        try:
            os.makedirs(RESULTADOS_DIR, exist_ok=True)
            shutil.copy2(CATALOGO_PATH, CATALOGO_BACKUP_PATH)
        except Exception:
            pass


def agregar_item_catalogo(codigo: str, descripcion: str, palabras_clave: str = '', rubro: str = '') -> bool:
    """Agrega un ítem al catálogo de la empresa (o lo actualiza si el código ya existe)."""
    df = cargar_catalogo()
    codigo_str = str(codigo or '').strip()
    descripcion_str = str(descripcion or '').strip()
    if not palabras_clave or not str(palabras_clave).strip():
        palabras_clave = generar_palabras_clave_automaticas(descripcion_str)

    nuevo_registro = {
        'Codigo': codigo_str,
        'Descripcion': descripcion_str,
        'Palabras_Clave': str(palabras_clave).strip(),
        'Rubro': str(rubro or '').strip(),
    }

    if codigo_str and (df['Codigo'].astype(str).str.strip() == codigo_str).any():
        idx = df.index[df['Codigo'].astype(str).str.strip() == codigo_str][0]
        for k, v in nuevo_registro.items():
            df.at[idx, k] = v
    else:
        df = pd.concat([df, pd.DataFrame([nuevo_registro])], ignore_index=True)

    guardar_catalogo(df)
    return True


def eliminar_item_catalogo(indice: int) -> bool:
    """Elimina un ítem del catálogo según su índice de fila (0-based)."""
    df = cargar_catalogo()
    if 0 <= indice < len(df):
        df = df.drop(df.index[indice]).reset_index(drop=True)
        guardar_catalogo(df)
        return True
    return False


def formatear_catalogo_texto() -> str:
    """Devuelve una representación legible del catálogo actual para mostrar en Telegram."""
    df = cargar_catalogo()
    if df.empty:
        return "📂 Tu catálogo de empresa está vacío."

    lineas = [f"📦 *Catálogo de la Empresa ({len(df)} ítems)*\n"]
    for idx, row in df.iterrows():
        codigo = limpiar_texto_markdown(str(row['Codigo']).strip()) or 'S/C'
        desc = limpiar_texto_markdown(str(row['Descripcion']).strip())
        if len(desc) > 70:
            desc = desc[:67] + '...'
        kw = limpiar_texto_markdown(str(row['Palabras_Clave']).strip())
        lineas.append(
            f"*{idx + 1}.* `{codigo}` — {desc}\n"
            f"   🔑 _Keywords:_ {kw or '-'}"
        )
    return '\n'.join(lineas)


def evaluar_item_contra_catalogo(item_pliego: dict, df_catalogo: pd.DataFrame = None) -> dict:
    """
    Evalúa si un ítem de una licitación coincide con algún ítem del catálogo de la empresa.
    Combina:
      1. Código de catálogo (exacto o prefijo de clase)
      2. Palabras clave
      3. Similitud de texto (SequenceMatcher + solapamiento de tokens)
    """
    if df_catalogo is None:
        df_catalogo = cargar_catalogo()

    resultado_base = {
        'coincide': False,
        'item_catalogo': '',
        'codigo_catalogo': '',
        'criterio': 'Sin coincidencia',
        'score': 0.0,
    }

    if df_catalogo.empty:
        return resultado_base

    codigo_pliego = str(item_pliego.get('codigo_item', '')).strip()
    desc_pliego = str(item_pliego.get('descripcion', '')).strip()
    desc_pliego_norm = normalizar_texto(desc_pliego)
    tokens_pliego = extraer_tokens_relevantes(desc_pliego)

    mejor_match = resultado_base.copy()

    for _, row in df_catalogo.iterrows():
        codigo_cat = str(row.get('Codigo', '')).strip()
        desc_cat = str(row.get('Descripcion', '')).strip()
        kw_raw = str(row.get('Palabras_Clave', '')).strip()

        score_actual = 0.0
        criterio_actual = ''

        # 1. Comparación por Código Oficial de COMPR.AR
        if codigo_pliego and codigo_cat:
            if codigo_pliego.lower() == codigo_cat.lower():
                score_actual = 100.0
                criterio_actual = f'Código exacto ({codigo_cat})'
            else:
                # Comparar prefijo de clase (ej: '2.3.2-1571.23' -> clase '2.3.2-1571')
                clase_pliego = codigo_pliego.split('.')[0:3]
                prefijo_pliego = codigo_pliego.rsplit('.', 1)[0] if '.' in codigo_pliego else codigo_pliego
                prefijo_cat = codigo_cat.rsplit('.', 1)[0] if '.' in codigo_cat else codigo_cat
                if prefijo_pliego and prefijo_pliego.lower() == prefijo_cat.lower():
                    score_actual = 88.0
                    criterio_actual = f'Misma clase de código ({prefijo_cat})'

        # 2. Comparación por Palabras Clave
        if score_actual < 100.0 and kw_raw and desc_pliego_norm:
            keywords = [normalizar_texto(k) for k in re.split(r'[,;]+', kw_raw) if normalizar_texto(k)]
            kw_coincidentes = []
            for kw in keywords:
                # Si es frase o palabra completa dentro de la descripción o tokens
                if ' ' in kw:
                    if kw in desc_pliego_norm:
                        kw_coincidentes.append(kw)
                else:
                    if kw in tokens_pliego or re.search(rf'\b{re.escape(kw)}', desc_pliego_norm):
                        kw_coincidentes.append(kw)

            if kw_coincidentes:
                proporcion = len(kw_coincidentes) / max(len(keywords), 1)
                # Basta 1 keyword muy específica o varias keywords para superar el umbral
                score_kw = min(95.0, 65.0 + (proporcion * 30.0) + (5.0 * (len(kw_coincidentes) - 1)))
                if score_kw > score_actual:
                    score_actual = score_kw
                    criterio_actual = f"Palabras clave ({', '.join(kw_coincidentes[:3])})"

        # 3. Comparación por Similitud de Texto
        if score_actual < 85.0 and desc_cat and desc_pliego_norm:
            desc_cat_norm = normalizar_texto(desc_cat)
            tokens_cat = extraer_tokens_relevantes(desc_cat)

            ratio_seq = difflib.SequenceMatcher(None, desc_cat_norm, desc_pliego_norm).ratio()
            overlap_tokens = 0.0
            if tokens_cat and tokens_pliego:
                comunes = tokens_cat.intersection(tokens_pliego)
                overlap_tokens = len(comunes) / max(min(len(tokens_cat), len(tokens_pliego)), 1)

            score_sim = max(ratio_seq, overlap_tokens * 0.85) * 100.0
            if score_sim >= 60.0 and score_sim > score_actual:
                score_actual = round(score_sim, 1)
                criterio_actual = f'Similitud de texto ({score_actual:.0f}%)'

        if score_actual >= 60.0 and score_actual > mejor_match['score']:
            mejor_match = {
                'coincide': True,
                'item_catalogo': desc_cat or codigo_cat,
                'codigo_catalogo': codigo_cat,
                'criterio': criterio_actual,
                'score': round(score_actual, 1),
            }

    return mejor_match


def cruzar_items_con_catalogo(items_por_proceso: Dict[str, List[dict]]) -> Dict[str, dict]:
    """
    Cruza el diccionario {numero_proceso: [lista_de_items]} contra el catálogo de la empresa.
    Devuelve por cada proceso el resumen de coincidencia y los ítems evaluados.
    """
    df_catalogo = cargar_catalogo()
    resultados = {}

    for num_proceso, items in items_por_proceso.items():
        total_items = len(items)
        items_evaluados = []
        coincidentes = []

        for item in items:
            eval_res = evaluar_item_contra_catalogo(item, df_catalogo)
            item_enriquecido = {**item, **eval_res}
            items_evaluados.append(item_enriquecido)
            if eval_res['coincide']:
                coincidentes.append(item_enriquecido)

        cant_match = len(coincidentes)
        porcentaje = round((cant_match / total_items) * 100.0, 1) if total_items > 0 else 0.0

        detalles_txt = []
        for m in coincidentes:
            desc_corta = m.get('descripcion', '')[:45]
            cant_str = f"{m.get('cantidad', '')} {m.get('unidad_medida', '')}".strip()
            detalles_txt.append(
                f"Renglón {m.get('renglon', '?')}: {desc_corta}... ({cant_str}) -> "
                f"Matchea '{m.get('item_catalogo', '')[:35]}' ({m.get('criterio', '')})"
            )

        resultados[num_proceso] = {
            'tiene_coincidencia': cant_match > 0,
            'total_items': total_items,
            'items_coincidentes': cant_match,
            'grado_coincidencia_pct': porcentaje,
            'detalle_coincidencias': ' | '.join(detalles_txt) if detalles_txt else 'Sin coincidencias con el catálogo',
            'items_evaluados': items_evaluados,
        }

    return resultados


def enriquecer_reporte_excel(archivo_xls: str, items_por_proceso: Dict[str, List[dict]]) -> Tuple[str, Dict[str, dict]]:
    """
    Lee el Excel descargado de comprar.gob.ar, le agrega las columnas de grado de coincidencia
    con el catálogo de la empresa y añade una segunda hoja 'Items_Licitados' con el desglose
    completo de ítems (descripción, cantidad, unidad de medida y resultado del cruce).
    Guarda el resultado como archivo .xlsx.
    """
    resultados_cruce = cruzar_items_con_catalogo(items_por_proceso)

    try:
        df_procesos = pd.read_excel(archivo_xls)
    except Exception as e:
        print(f"No se pudo leer el Excel original para enriquecer ({e})")
        return archivo_xls, resultados_cruce

    if df_procesos.empty:
        return archivo_xls, resultados_cruce

    col_num_proceso = df_procesos.columns[0]

    col_matchea = []
    col_cant_match = []
    col_grado_pct = []
    col_detalle = []

    for _, row in df_procesos.iterrows():
        num_proc = str(row[col_num_proceso]).strip()
        info = resultados_cruce.get(num_proc)
        if info is None:
            col_matchea.append('No inspeccionado')
            col_cant_match.append('-')
            col_grado_pct.append('-')
            col_detalle.append('No se recolectaron ítems para este proceso')
        else:
            col_matchea.append('SÍ' if info['tiene_coincidencia'] else 'NO')
            col_cant_match.append(f"{info['items_coincidentes']} de {info['total_items']}")
            col_grado_pct.append(f"{info['grado_coincidencia_pct']}%")
            col_detalle.append(info['detalle_coincidencias'])

    df_procesos['Coincide con Catálogo'] = col_matchea
    df_procesos['Ítems Coincidentes'] = col_cant_match
    df_procesos['Grado de Coincidencia'] = col_grado_pct
    df_procesos['Detalle de Coincidencias'] = col_detalle

    # Construir la segunda hoja con el detalle de todos los ítems recolectados
    filas_items = []
    for num_proc, info in resultados_cruce.items():
        for item in info['items_evaluados']:
            filas_items.append({
                'Número de Proceso': num_proc,
                'Renglón': item.get('renglon', ''),
                'Código Ítem COMPR.AR': item.get('codigo_item', ''),
                'Descripción del Ítem': item.get('descripcion', ''),
                'Cantidad': item.get('cantidad', ''),
                'Unidad de Medida': item.get('unidad_medida', ''),
                'Coincide con Catálogo': 'SÍ' if item.get('coincide') else 'NO',
                'Ítem del Catálogo': item.get('item_catalogo', ''),
                'Criterio de Coincidencia': item.get('criterio', ''),
                'Puntaje Match (%)': item.get('score', 0.0),
            })

    df_items = pd.DataFrame(filas_items) if filas_items else pd.DataFrame(
        columns=[
            'Número de Proceso', 'Renglón', 'Código Ítem COMPR.AR',
            'Descripción del Ítem', 'Cantidad', 'Unidad de Medida',
            'Coincide con Catálogo', 'Ítem del Catálogo',
            'Criterio de Coincidencia', 'Puntaje Match (%)',
        ]
    )

    archivo_xlsx = re.sub(r'\.xls$', '.xlsx', archivo_xls, flags=re.IGNORECASE)
    if archivo_xlsx == archivo_xls:
        archivo_xlsx = archivo_xls + '.xlsx'

    with pd.ExcelWriter(archivo_xlsx, engine='openpyxl') as writer:
        df_procesos.to_excel(writer, sheet_name='Procesos', index=False)
        df_items.to_excel(writer, sheet_name='Items_Licitados', index=False)

    return archivo_xlsx, resultados_cruce

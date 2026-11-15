import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTADOS_DIR = os.path.join(BASE_DIR, 'resultados')

# guarda, por chat de Telegram, el último rubro/período elegido, para que a
# futuro se pueda repetir esa misma búsqueda con un solo mensaje
CONFIGURACIONES_PATH = os.path.join(BASE_DIR, 'configuraciones_busqueda.json')
ALERTAS_PATH = os.path.join(BASE_DIR, 'alertas_busqueda.json')
VISTOS_PATH = os.path.join(BASE_DIR, 'licitaciones_vistas.json')

# Ruta al archivo Excel que almacena el catálogo de ítems propios de la empresa
CATALOGO_PATH = os.path.join(BASE_DIR, 'catalogo_empresa.xlsx')

# Cantidad máxima de procesos a inspeccionar ítems en profundidad por búsqueda
MAX_PROCESOS_INSPECCION = int(os.getenv('MAX_PROCESOS_INSPECCION', '10'))

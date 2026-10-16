# Bot de Gastos — Guía Completa

> Documento único y definitivo del proyecto. Reemplaza a `DESCRIPCION_PROYECTO.md`,
> `EXPLICACION_CODIGO.md`, `GUIA_EXPLICACION_PASO_A_PASO.md` y a la carpeta
> `explicacion_linea_por_linea/`.
>
> Todo lo que está acá se verificó **contra el código fuente**. Donde la documentación
> anterior differed del código, esta versión sigue al código.

---

## Índice

1. [Qué hace el proyecto](#1-qué-hace-el-proyecto)
2. [Arquitectura](#2-arquitectura)
3. [Requisitos previos](#3-requisitos-previos)
4. [Instalación paso a paso](#4-instalación-paso-a-paso)
5. [Estructura de archivos](#5-estructura-de-archivos)
6. [Variables de entorno](#6-variables-de-entorno)
7. [Comandos del bot](#7-comandos-del-bot)
8. [El flujo completo, de punta a punta](#8-el-flujo-completo-de-punta-a-punta)
9. [Explicación archivo por archivo](#9-explicación-archivo-por-archivo)
10. [Glosario](#10-glosario)
11. [Problemas reales y cómo se resolvieron](#11-problemas-reales-y-cómo-se-resolvieron)
12. [Diagnóstico rápido de errores](#12-diagnóstico-rápido-de-errores)
13. [Limitaciones conocidas](#13-limitaciones-conocidas)
14. [Qué cambió respecto a la documentación anterior](#14-qué-cambió-respecto-a-la-documentación-anterior)

---

## 1. Qué hace el proyecto

Un bot de Telegram al que le escribís un gasto como te salga —`almuerzo 4500`,
`$3200 uber al aeropuerto`, `netflix 1500 usd`, `8000 de bebida y 5000 de comida`— y una
inteligencia artificial lo convierte en datos estructurados, te los muestra para que los
confirmes o los corrijas, los guarda en una planilla de Google Sheets y, cuando querés,
genera un dashboard con totales y gráficos que se abre solo en tu navegador.

El proyecto combina los tres bloques de la materia:

| Bloque | Herramienta | Dónde está en el código |
|---|---|---|
| Interfaz de usuario | Telegram Bot API | `bot.py` |
| Inteligencia artificial | OpenRouter (prioritario) / Gemini | `llm_parser.py` |
| Automatización RPA | TagUI | `tagui/abrir_dashboard.tag`, invocado desde `bot.py` |
| Almacenamiento en la nube | Google Sheets API | `excel_manager.py`, `tagui_dashboard.py` |
| Datos externos | DolarHoy.com | `dolar.py` |

### El recorrido de un gasto

```
Vos escribís "almuerzo 4500" en Telegram
        ↓
bot.py recibe el mensaje
        ↓
llm_parser.py consulta al LLM y devuelve JSON
        ↓
bot.py te muestra el resumen con 6 botones
        ↓
Vos confirmás (o corregís un campo y confirmás)
        ↓
excel_manager.py escribe una fila en la hoja "Gastos"
        ↓
tagui_dashboard.py regenera la hoja "Dashboard" (totales + tortas + cartel del dólar)
        ↓
dolar.py scrapea DolarHoy.com para el cartel
```

---

## 2. Arquitectura

### Diagrama

```
┌──────────────┐
│  TELEGRAM    │   tu interfaz
└──────┬───────┘
       │  mensajes / botones
       ↓
┌──────────────────────────────────────────────┐
│                   bot.py                     │   orquestador
│  teclado, confirmación, edición, comandos,   │
│  lock de instancia única, invocación de TagUI│
└──┬────────┬────────┬─────────┬───────────────┘
   │        │        │         │
   ↓        ↓        ↓         ↓
llm_parser  datos  categorias  tagui_dashboard.py
   │                     │         │        │
   ↓                     ↓         ↓        ↓
OpenRouter      hoja "Gastos"  Google   tagui/
o Gemini                          Sheets   abrir_dashboard.tag
   │                              API        ↓
   ↓                                     Chrome
dolar.py ──► DolarHoy.com
```

### Roles de cada pieza

| Archivo | Líneas | Rol |
|---|---|---|
| `bot.py` | 434 | Orquestador. Comandos, teclado, confirmación, edición, estado on/off, lock de instancia, invocación de TagUI |
| `llm_parser.py` | 231 | Interpreta texto natural → lista de `Gasto`. OpenRouter con cascada de modelos, Gemini como alternativa |
| `tagui_dashboard.py` | 210 | Genera la hoja `Dashboard`: totales, tablas por moneda, tortas y el cartel del dólar |
| `dolar.py` | 83 | Scraper de DolarHoy.com. Cotizaciones de dólar Oficial, Blue, MEP, CCL y Mayorista |
| `excel_manager.py` | 60 | Lee y escribe la hoja `Gastos` en Google Sheets |
| `config.py` | 32 | Carga el `.env` y expone las variables de configuración |
| `datos.py` | 25 | Modelo de datos `Gasto` (dataclass) |
| `categorias.py` | 14 | Las 10 categorías y las 6 monedas permitidas |
| `tagui/abrir_dashboard.tag` | 6 | Flujo RPA: URL de la planilla + `wait 5` |
| `iniciar_bot.bat` | 4 | Lanzador en Windows |

### Orden de importación

Python carga los módulos al importarlos, así que el orden real es:

```
iniciar_bot.bat → py bot.py
    1. config.py        (lee el .env)
    2. datos.py         (define Gasto)
    3. categorias.py    (define los catálogos)
    4. excel_manager.py
    5. llm_parser.py    (importa datos y categorias)
    6. tagui_dashboard.py (importa dolar)
    7. main()           (empieza el polling)
```

### Un punto que confunde mucho

**`tagui_dashboard.py` no usa TagUI.** Pese al nombre, su único trabajo es llamar a la
Google Sheets API mediante `gspread`. TagUI solo aparece en `bot.py`, que invoca el
archivo `.tag` para que se abra el navegador. La cotización del dólar tampoco la trae
TagUI: la trae `dolar.py` por HTTP.

---

## 3. Requisitos previos

- Windows (el bot usa `msvcrt` y `subprocess.CREATE_NO_WINDOW`, ambos exclusivos de Windows)
- **Python 3.12+**, accesible como `py` en la terminal
  - El mínimo real es 3.10, porque `bot.py` usa `match texto: case ...`
- pip 23+
- Navegador **Chrome** instalado (lo abre TagUI)
- **TagUI** para Windows, instalado y en el PATH
- Cuenta de Google (para Google Sheets API)
- Telegram, con un bot creado en [@BotFather](https://t.me/BotFather)
- Conexión a internet

---

## 4. Instalación paso a paso

### Paso 1 — Entorno de Python

Opcional pero recomendado:

```bat
py -m venv .venv
.venv\Scripts\activate
```

### Paso 2 — Dependencias

```bat
pip install -r requirements.txt
```

> **Nota clave:** `google-auth` debe quedar en **2.57.x** (mayor que 2.56.0) porque
> `google-genai==2.22.0` exige esa versión mínima. Si se actualiza sola, el bot deja de
> importar.

### Paso 3 — Crear el bot de Telegram

1. Abrí [@BotFather](https://t.me/BotFather) en Telegram
2. Mandá `/newbot`
3. Le ponés nombre y usuario
4. Te devuelve un token tipo `1234567890:AAE...` — ese es tu `TELEGRAM_TOKEN`

### Paso 4 — Obtener la API key de la IA

**OpenRouter (recomendado).** La clave del proyecto tiene denegado el acceso a Gemini, así
que OpenRouter es la vía que realmente funciona.

1. Entrá a <https://openrouter.ai/keys>
2. Creá una key. Tiene que empezar con `sk-or-v1-` y estar **completa** (si la pegás
   truncada, con `...`, el bot lo detecta y avisa)
3. Pegala como `OPENROUTER_API_KEY`

Alternativa: <https://aistudio.google.com/apikey> para `GEMINI_API_KEY` (empieza con
`AIza...`).

### Paso 5 — Google Sheets API

1. En [Google Cloud Console](https://console.cloud.google.com) creá un proyecto
2. Habilitá la **Google Sheets API**
3. Creá una **Service Account** y generá una clave JSON
4. Descargala y renombrala a `credentials.json`, ponela en la carpeta del proyecto
5. Anotá el email de la Service Account, tiene esta forma:
   `algo@tu-proyecto.iam.gserviceaccount.com`

### Paso 6 — Crear y compartir la planilla

1. Creá una planilla nueva en Google Sheets
2. **Compartila** con el email de la Service Account, rol **Editor**. Sin esto da
   `403 The caller does not have permission`
3. Copiá el ID de la planilla. Es el texto de la URL entre `/d/` y `/edit`:

   ```
   https://docs.google.com/spreadsheets/d/1d-6FsBWTfojx8B4jyThL9uG5xnw83K14MZh5cikoqTM/edit
                                    └────────── el ID va acá ──────────┘
   ```

### Paso 7 — Armar el `.env`

```bat
copy .env.example .env
```

Y completá los valores (ver [sección 6](#6-variables-de-entorno)).

### Paso 8 — Instalar TagUI

Descargá TagUI para Windows y verificá que `tagui` quede en el PATH. En la instalación
probada quedó en `C:\TagUI_Windows\tagui\src\tagui.cmd`. Comprobá con:

```bat
tagui
```

### Paso 9 — Correr el bot

```bat
py bot.py
```

O doble clic en `iniciar_bot.bat`.

---

## 5. Estructura de archivos

```
Grupo15RPA/
├── .env                      # SECRETOS: tokens, IDs (NO subir a git)
├── .env.example              # Plantilla de configuración documentada
├── .gitignore                # Excluye .env, credentials.json, __pycache__, logs
├── README.md                 # Vista rápida (acceso, comandos, ejemplos)
├── GUIA_COMPLETA.md          # Este documento
├── INFORME_TRABAJO_RPA.docx  # Informe de trabajo integrador
├── requirements.txt          # Dependencias de Python con versiones fijadas
├── bot.py                    # Bot de Telegram (punto de entrada)
├── config.py                 # Configuración y carga del .env
├── llm_parser.py             # Intérprete con IA (OpenRouter o Gemini)
├── categorias.py             # Categorías y monedas (fuente única de verdad)
├── datos.py                  # Modelo Gasto
├── excel_manager.py          # Persistencia en Google Sheets
├── dolar.py                  # Scraper de DolarHoy.com
├── tagui_dashboard.py        # Generador del Dashboard
├── estado_bot.txt            # Flag on/off (1 = encendido, 0 = apagado)
├── bot.lock                  # Bloqueo de archivo: garantiza una sola instancia
├── iniciar_bot.bat           # Lanzador del bot en Windows
├── credentials.json          # Service Account de Google (SECRETO)
└── tagui/
    └── abrir_dashboard.tag   # Flujo RPA que abre el Dashboard en Chrome
```

---

## 6. Variables de entorno

El `.env` se lee al arrancar, desde `config.py`. **Nunca se sube a git.**

| Variable | Obligatoria | Default | Para qué |
|---|---|---|---|
| `TELEGRAM_TOKEN` | Sí | — | Token de @BotFather. Sin esto el bot no arranca |
| `OPENROUTER_API_KEY` | Una de las dos | — | Clave de OpenRouter (`sk-or-v1-...`). **Tiene prioridad sobre Gemini** |
| `OPENROUTER_MODELO` | No | `nvidia/nemotron-3-super-120b-a12b:free` | Primer modelo que se intenta |
| `GEMINI_API_KEY` | Una de las dos | — | Alternativa a OpenRouter (`AIza...`) |
| `LLM_MODELO` | No | `gemini-3.6-flash` | Modelo de Gemini, solo si no hay key de OpenRouter |
| `GOOGLE_SHEET_ID` | Sí | — | El ID de la planilla, entre `/d/` y `/edit` |

> **Prioridad:** si existe `OPENROUTER_API_KEY`, se usa OpenRouter y **Gemini se ignora
> por completo**, aunque también esté definida.

---

## 7. Comandos del bot

| Comando | Qué hace |
|---|---|
| `/start` | Mensaje de bienvenida, muestra el estado (encendido/apagado) y ejemplos |
| `/encender` | Activa el bot (escribe `1` en `estado_bot.txt`) |
| `/apagar` | Desactiva el bot (escribe `0` en `estado_bot.txt`) |
| `/reporte` | Regenera el Dashboard y lo abre en Chrome con TagUI |
| `/cancelar` | Descarta el gasto pendiente de confirmación |

Cualquier otro texto se interpreta como un gasto.

---

## 8. El flujo completo, de punta a punta

Caso: escribís `compre una camisa por 12000 pesos`

1. Telegram entrega el mensaje a `bot.py`
2. `bot.py` ve que el bot está encendido y que no hay nada pendiente para ese chat
3. Llama a `interpretar(texto)` de `llm_parser.py`
4. `llm_parser.py` arma el prompt (con la fecha de hoy y los catálogos) y lo manda a
   OpenRouter; si OpenRouter falla, cascadea por 4 modelos más
5. Recibe JSON, lo limpia de los ``` ``` ``` y lo convierte en objetos
6. `_normalizar_objeto` valida y corrige: moneda fuera de catálogo → `ARS`, categoría
   fuera de catálogo → `otros`, fecha inválida → hoy
7. Si el LLM devolvió un solo gasto, `_dividir_en_fragmentos` parte el texto por `y`, `e`,
   `,`, `;` y `N por`, y repregunta cada fragmento por separado. Solo se queda con el
   resultado partido si da **más** gastos que la respuesta original
8. `bot.py` descarta los que tengan monto ≤ 0 o descripción vacía
9. `bot.py` deduplica: dos gastos con la misma descripción, monto, moneda, categoría y
   fecha se cuentan uno solo
10. Guarda los gastos en `PENDIENTES[chat_id]` y te manda el resumen con los 6 botones
11. Tocás **✏️ Editar Categoría** → el bot pasa a estado de edición y ofrece el teclado con
    las 10 categorías
12. Tocás `ropa` → valida contra `CATEGORIAS`, la aplica a todos los gastos pendientes y
    vuelve a mostrarte el resumen actualizado
13. Tocás **✅ Sí, guardar** → `excel.registrar()` escribe una fila por gasto en la hoja
    `Gastos`
14. Inmediatamente `_actualizar_dashboard_silencioso()` regenera el Dashboard, y eso dispara
    un scrape a DolarHoy.com
15. Si después mandás `/reporte`, se regenera el Dashboard y `bot.py` reescribe
    `abrir_dashboard.tag` y corre `cmd /c tagui abrir_dashboard.tag` → se abre Chrome

> El dashboard **no espera a `/reporte`**: se actualiza solo en cada gasto guardado.

### El teclado de confirmación

```
Fila 1:   ✅ Sí, guardar            ❌ No, cancelar
Fila 2:   ✏️ Editar Moneda           ✏️ Editar Categoría
Fila 3:   📅 Editar Fecha            📝 Editar Descripción
```

### Los 4 estados de edición

| Botón | Qué valida | Error si falla |
|---|---|---|
| Editar Moneda | El texto en mayúsculas tiene que estar en `MONEDAS` | `❌ Moneda no válida` |
| Editar Categoría | El texto en minúsculas tiene que estar en `CATEGORIAS` | `❌ Categoría no válida` |
| Editar Fecha | `datetime.date.fromisoformat(texto)`, o sea `AAAA-MM-DD` | `❌ Formato incorrecto. Debía ser AAAA-MM-DD.` |
| Editar Descripción | Nada, texto libre | — |

En todos los casos la edición se aplica a **todos** los gastos pendientes de ese chat. Se
vuelve al resumen con el botón **⬅️ Cancelar edición** o después de elegir el valor.

---

## 9. Explicación archivo por archivo

### 9.1 `requirements.txt`

```
gspread==6.1.3
google-auth==2.57.1
python-telegram-bot==22.8
google-genai==2.22.0
httpx==0.28.1
```

| Paquete | Para qué lo usa el proyecto |
|---|---|
| `gspread` | Cliente de Google Sheets: `service_account`, `open_by_key`, `add_worksheet`, `update`, `batch_update` |
| `google-auth` | Autenticación como Service Account |
| `python-telegram-bot` | La API de Telegram: `ApplicationBuilder`, handlers, teclado en línea |
| `google-genai` | Cliente oficial de Gemini (la vía alternativa) |
| `httpx` | Las dos salidas a internet: llamar a OpenRouter y scrapear DolarHoy.com |

Las versiones están fijadas con `==` para que la instalación sea reproducible.

---

### 9.2 `config.py` (32 líneas)

Su trabajo es que **nada más en el proyecto tenga que saber de dónde salen los tokens**.
Si cambiás una key, tocás el `.env` y no el código.

```python
BASE_DIR = Path(__file__).resolve().parent
```

- `__file__` es la ruta de este archivo
- `.resolve()` la convierte en absoluta
- `.parent` saca el nombre del archivo y deja la carpeta
- `Path` sabe unir carpetas con `/`, así que `BASE_DIR / "tagui"` es la carpeta `tagui`

```python
def _cargar_env():
    if RUTA_ENV.exists():
        with open(RUTA_ENV, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                clave, _, valor = linea.partition("=")
                os.environ.setdefault(clave.strip(), valor.strip())
```

Línea por línea:

| Línea | Qué hace |
|---|---|
| `if RUTA_ENV.exists()` | Si no hay `.env`, no rompe |
| `encoding="utf-8"` | Permite acentos en los valores |
| `linea.startswith("#")` | Saltea comentarios |
| `"=" not in linea` | Saltea líneas mal formadas |
| `continue` | Pasa a la línea siguiente |
| `linea.partition("=")` | parte en clave / separador / valor |
| `os.environ.setdefault(...)` | **No pisa** variables que ya existen en el entorno |

> El proyecto **no** usa `python-dotenv`. El `.env` se parsea a mano, y por eso no hay que
> instalar nada extra.

Lo que expone:

```python
TOKEN_TELEGRAM     = os.environ.get("TELEGRAM_TOKEN", "")
GEMINI_API_KEY     = os.environ.get("GEMINI_API_KEY", "")
LLM_MODELO         = os.environ.get("LLM_MODELO", "gemini-3.6-flash")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODELO  = os.environ.get("OPENROUTER_MODELO", "nvidia/nemotron-3-super-120b-a12b:free")
GOOGLE_SHEET_ID    = os.environ.get("GOOGLE_SHEET_ID", "")
URL_DASHBOARD      = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
```

---

### 9.3 `categorias.py` (14 líneas)

```python
CATEGORIAS = [
    "comida", "transporte", "vivienda", "salud", "educacion",
    "entretenimiento", "ropa", "salario", "electrodomesticos", "otros",
]

MONEDAS = ["ARS", "USD", "EUR", "MXN", "CLP", "UYU"]
```

Es la **fuente única de verdad** del proyecto. Las listas se usan en tres lugares:

- `llm_parser.py` las inyecta en el prompt, para que la IA elija de entre ellas
- `llm_parser.py` valida lo que devuelve la IA
- `bot.py` las usa para los teclados de edición

Cambiar acá cambia todo el sistema.

---

### 9.4 `datos.py` (25 líneas)

```python
@dataclass
class Gasto:
    descripcion: str = ""
    monto: float = 0.0
    moneda: str = "ARS"
    categoria: str = "Otros"
    fecha: str = None
```

- `@dataclass` es un decorador: genera solo el `__init__`, el `__repr__` y el `__eq__`
- todos los campos tienen default, así que `Gasto(monto=4500)` es válido
- `fecha: str = None` es el patrón "optional sin `Optional`": None por defecto

```python
def __post_init__(self):
    if not self.fecha:
        self.fecha = _HOY()
```

`__post_init__` se llama **después** de que el dataclass armó el `__init__`. Acá se
completa la fecha con la de hoy si vino vacía.

```python
def resumen(self) -> str:
    return (
        f"Categoría: {self.categoria}\n"
        f"Descripción: {self.descripcion}\n"
        f"Monto: {self.monto:,.2f} {self.moneda}\n"
        f"Fecha: {self.fecha}"
    )
```

`:,.2f` es un especificador de formato: coma para separador de miles, dos decimales.
`4500` se muestra como `4,500.00`.

---

### 9.5 `excel_manager.py` (60 líneas)

Habla con Google Sheets como si fuera "el carnet del robot" del proceso: la Service
Account.

```python
_cliente = None

def _obtener_cliente(credenciales: str):
    global _cliente
    if _cliente is None:
        _cliente = gspread.service_account(filename=credenciales)
    return _cliente
```

Este es un **patrón de caché con `global`**: el cliente se autentica **una sola vez** y se
reusa. Sin esto, cada llamada a la API haría una autenticación nueva.

La hoja `Gastos` tiene 5 columnas:

| Columna | Contenido |
|---|---|
| A | Fecha |
| B | Categoría |
| C | Descripción |
| D | Monto |
| E | Moneda |

```python
def asegurar_hojas(sheet_id, credenciales) -> None:
    sh = abrir_hoja(sheet_id, credenciales)
    titulos = [ws.title for ws in sh.worksheets()]
    if HOJA_GASTOS not in titulos:
        ws = sh.add_worksheet(title=HOJA_GASTOS, rows=1000, cols=5)
        ws.append_row(ENCABEZADOS)
```

Se crea sola la primera vez, con 1000 filas y los encabezados.

Un detalle al leer:

```python
"monto": float(fila[3] or 0)
```

`fila[3] or 0` — si la celda viene como `""` (que es lo que devuelve Sheets para una
celda vacía), `or` lo convierte en `0`, y `float("")` no rompería el programa.

La clase `ExcelManager` existe para que `bot.py` no tenga que pasar el ID y las
credenciales en cada llamada:

```python
excel = ExcelManager(config.GOOGLE_SHEET_ID, str(config.RUTA_CREDENCIALES))
```

---

### 9.6 `llm_parser.py` (231 líneas)

El módulo más complejo. Traduce lenguaje natural a datos.

#### La selección del modelo

```python
def interpretar(texto: str) -> list:
    if config.OPENROUTER_API_KEY:
        ...interpretar_openrouter(texto)
    elif config.GEMINI_API_KEY:
        ...interpretar_llm(texto)
    else:
        raise RuntimeError("No hay ninguna API key configurada...")
```

**OpenRouter tiene prioridad absoluta.** Si está su key, Gemini no se toca.

#### El prompt

`PROMPT_SISTEMA` es una f-string que se arma con:

- `HOY` — la fecha de hoy
- `", ".join(MONEDAS)` — la lista de monedas
- `", ".join(CATEGORIAS)` — la lista de categorías, con una línea explicando qué entra en
  cada una

Le exige al modelo JSON puro, **una lista** de objetos:

```json
[{"descripcion": "...", "monto": 1234.56, "moneda": "ARS", "categoria": "comida", "fecha": "YYYY-MM-DD"}]
```

Y tiene una regla clave para los mensajes múltiples:

> Contá los gastos UNO POR UNO. Cada gasto tiene su PROPIO monto/número. [...] NUNCA fusiones
> dos importes en un solo objeto.

Los `{{` y `}}` del f-string son llaves literales: sin doble chave, `{` abriría un
reemplazo de variable.

> **Detalle que se escapa:** la categoría `electrodomesticos` existe en `CATEGORIAS` pero
> **no tiene descripción en el prompt**. La IA la conoce como opción válida, pero no tiene
> la guía de qué cosas van ahí.

#### La cascada de modelos de OpenRouter

```python
modelos = list(dict.fromkeys([
    config.OPENROUTER_MODELO,                      # el que quieras en el .env
    "z-ai/glm-5.2:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "google/gemma-4-31b-it:free",
    "openrouter/free",
]))
```

`dict.fromkeys(...)` quita duplicados **y conserva el orden**. Por eso, si
`OPENROUTER_MODELO` ya es `nvidia/nemotron-3-super-120b-a12b:free`, la lista queda de 4
elementos y no repite ese modelo.

Por cada modelo se intentan **3 veces**:

| Situación | Qué hace |
|---|---|
| `401` o `403` | Corta todo: la key está mal, no es un problema de cuota |
| `429` | Espera `5 × intento` segundos y reintenta |
| Otro error | Espera `2 × intento` segundos y reintenta |
| 3 fallos en un modelo | Pasa al siguiente modelo |
| Se agotan los 5 modelos | `RuntimeError` → el bot avisa que reintente en unos minutos |

La llamada usa `"temperature": 0` (respuestas deterministas) y
`"response_format": {"type": "json_object"}`.

> **Riesgo latente:** el prompt exige una **lista** de JSON, pero `json_object` le pide un
> **objeto** raíz a la API. Con la mayoría de modelos funciona igual porque `_parsear_json`
> envuelve un dict en lista, pero con algunos modelos gratuitos puede dar problemas.

#### Limpiar la respuesta

```python
def _parsear_json(texto: str) -> list:
    contenido = texto.strip()
    if contenido.startswith("```"):
        contenido = re.sub(r"^```[a-zA-Z]*\s*", "", contenido)
        contenido = re.sub(r"\s*```$", "", contenido)
    datos = json.loads(contenido)
    if isinstance(datos, dict):
        datos = [datos]
    return datos
```

Los modelos a veces envuelven el JSON en un bloque de markdown. Esta función le saca los
``` ``` ``` de arriba y de abajo, y si vino un solo objeto en vez de una lista, lo envuelve
en una lista de un elemento.

#### Normalizar y corregir

`_normalizar_objeto` es la red de seguridad:

| Campo | Regla |
|---|---|
| `moneda` | Mayúsculas; si no está en `MONEDAS` → `ARS` |
| `categoria` | Minúsculas; si no está en `CATEGORIAS` → `otros` |
| `fecha` | Si viene vacía o no es una fecha ISO válida → hoy |
| `descripcion` | Si viene vacía → `"Sin descripcion"` |

#### Partir mensajes múltiples

```python
separadores = r"\s+(?:y|e)\s+|[,;]|(?<=\d)\s+por\s+"
```

Parte por `y`, `e`, `,`, `;` y por `N por`. Solo se usa si el LLM devolvió **un solo**
gasto, y solo se acepta el resultado partido si aparecen **más** gastos que antes
(`if len(unicos) > len(gastos)`). Es una red de seguridad, no el camino normal.

#### La trampa de `HOY`

```python
HOY = date.today().isoformat()
```

Está **a nivel de módulo**, así que se calcula **una sola vez, al importar**. Como el bot
es un proceso de larga vida, si queda corriendo pasada la medianoche, `HOY` queda congelado y
todo lo relativo ("ayer", "el lunes pasado") se corre un día. Se corrige reiniciando el
proceso.

---

### 9.7 `tagui_dashboard.py` (210 líneas)

Genera la hoja `Dashboard`. **No usa TagUI**: solo `gspread`.

#### El flujo de `generar_dashboard`

| Paso | Qué hace |
|---|---|
| 1 | `asegurar_hojas()` — se asegura de que exista `Gastos` |
| 2 | `abrir_hoja()` — abre la planilla |
| 3 | `_leer_gastos()` — lee todas las filas de `Gastos` |
| 4 | **Borra** la hoja `Dashboard` si existe |
| 5 | La crea de nuevo: **200 filas × 22 columnas** |
| 6 | Calcula totales por moneda y por categoría+moneda |
| 7 | Escribe el encabezado, la cantidad de gastos y los totales |
| 8 | Pide las cotizaciones a `dolar.obtener_cotizaciones_dolar()` dentro de un `try/except` |
| 9 | Arma la grilla en un diccionario `{(fila, columna): valor}` |
| 10 | Convierte el diccionario en una lista de listas y la escribe de una vez |
| 11 | Arma los requests de los gráficos y los estilos |
| 12 | Manda **un solo** `batch_update` |

> El paso 4 importa: **el Dashboard se borra y se recrea en cada ejecución**, así que
> cualquier formato o anotación manual que hagas en esa pestaña se pierde.

#### El cartel del dólar

```python
_COLUMNA_CARTEL = 4        # columna D
_ULTIMA_FILA_CARTEL = 7

_CARTEL_TIPOS = [
    ("oficial", "Dólar Oficial"),
    ("blue", "Dólar Blue"),
    ("bolsa", "Dólar MEP"),
]
```

El cartel se escribe en las columnas D, E y F, entre las filas 3 y 7, con fondo crema
(`0.98, 0.93, 0.85`).

`dolar.py` parsea **cinco** tipos, pero el cartel muestra **tres**: Oficial, Blue y MEP.
**CCL y Mayorista se leen y se descartan.**

La degradación es elegante:

```python
try:
    info_dolar = dolar.obtener_cotizaciones_dolar()
except Exception:
    info_dolar = {}
cartel_activado = _agregar_cartel_dolar(celdas, info_dolar)
```

Si DolarHoy está caído o cambió su HTML, el dashboard **se genera igual**, solo que sin el
cartel (y sin los dos `repeatCell` de su formato).

#### Por qué `batch_update`

Escribir celda por celda con `update_cell` agota el límite de **60 escrituras por minuto**
de la API gratuita. El dashboard escribe:

- toda la grilla en **un** `ws.update("A1", grilla)`
- todos los gráficos y estilos en **un** `sh.batch_update({"requests": requests})`

#### La torta

La Sheets API no acepta `"basicChart"` con `BasicChartType: "PIE"`. Para una torta hay que
usar el objeto `pieChart`, con dos rangos:

- **dominio** (`domain`): los nombres de las categorías, columna X
- **serie** (`series`): los montos, columna X + 1

#### La distribución en columnas

Cada moneda ocupa 11 columnas:

```python
columna += 11
```

Con 22 columnas totales entran cómodamente 1 o 2 monedas. **A partir de una tercera moneda
las columnas necesarias superan el ancho de la hoja.** El catálogo admite 6.

---

### 9.8 `dolar.py` (83 líneas)

El único módulo que scrapea HTML. Entra a `https://dolarhoy.com/` con `httpx`, manda
cabeceras de navegador para que no lo bloqueen, y saca los valores con expresiones
regulares.

#### Qué es una expresión regular

Un patrón de texto. Por ejemplo:

```python
_RE_PRECIO = re.compile(r'<div class="val"[^>]*>\$([\d.,]+)')
```

| Parte | Significado |
|---|---|
| `r'...'` | String crudo: no interpreta `\` |
| `re.compile(...)` | Compila el patrón una vez para reutilizarlo |
| `<div class="val">` | Texto literal |
| `[^>]*` | Cualquier carácter que no sea `>` (los atributos que falten) |
| `\$` | Un signo `$` literal |
| `([\d.,]+)` | **Grupo a capturar**: uno o más dígitos, puntos o comas |
| `.findall(bloque)` | Devuelve **todas** las coincidencias |

#### Los 5 tipos

```python
TIPOS = {
    "oficial": "Dólar Oficial",
    "blue": "Dólar Blue",
    "bolsa": "Dólar MEP",
    "contadoconliqui": "Dólar CCL",
    "mayorista": "Dólar Mayorista",
}
```

Las claves son los **slugs** que usa DolarHoy en sus URLs. Por eso MEP es `"bolsa"`:
en el portal, el MEP cuelga de `/cotizaciondolarbolsa`.

> `ORDEN_TIPOS` existe en el archivo pero **no se usa en ningún lado**. Es código muerto.

#### Los dos formatos de HTML

El portal usa dos markup distintos para los precios, y el parser cubre los dos:

| Formato | Patrón | Dónde |
|---|---|---|
| Tarjetas | `<div class="val">$1.485</div>` | `_RE_PRECIO` |
| Tabla "más cotizaciones" | `<div class="compra">1.438,00</div><div class="venta">1.500,00</div>` | `_RE_PAR` |

#### La trampa de los precios argentinos

```python
def _limpiar_precio(valor: str) -> float:
    return float(re.sub(r"[^\d,]", "", valor).replace(",", "."))
```

| Entrada | Salida | Por qué |
|---|---|---|
| `$1.535` | `1535.0` | El punto era separador de miles, no decimal |
| `$1.535,80` | `1535.8` | La coma era el decimal |

Se borra todo lo que no sea dígito o coma, y la coma coma se reemplaza por punto. El
truco es que en Argentina el decimal es la coma, no el punto.

El camino inverso, `formatear_precio`, devuelve el formato con puntos de miles:

```python
formatear_precio(1535.0)    # "$1.535"
formatear_precio(1535.8)    # "$1.535,80"
```

#### La hora de actualización

```python
_RE_HORA = re.compile(r"\d{2}/\d{2}/\d{2} \d{2}:\d{2} (?:AM|PM)")
```

Saca la fecha y hora que pone el portal, tipo `22/09/26 04:18 PM`, y se escribe debajo
del cartel.

#### El dict de salida

```python
{
    "cotizaciones": {
        "oficial": {"compra": 960.0, "venta": 1000.0},
        "blue":    {"compra": 1190.0, "venta": 1210.0},
        "bolsa":   {"compra": 1010.0, "venta": 1020.0},
        "contadoconliqui": {"compra": ..., "venta": ...},
        "mayorista": {"compra": ..., "venta": ...},
    },
    "actualizado": "22/09/26 04:18 PM",
}
```

> **No hay caché.** Cada gasto guardado dispara una consulta a DolarHoy.com, porque
> `_actualizar_dashboard_silencioso()` corre después de cada confirmación.

---

### 9.9 `bot.py` (434 líneas)

El orquestador. Todo lo demás lo llama este archivo.

#### El teclado

```python
TECLADO = ReplyKeyboardMarkup([
    [SÍ, NO],
    [EDITAR_MONEDA, EDITAR_CATEGORIA],
    [EDITAR_FECHA, EDITAR_DESCRIPCION],
], resize_keyboard=True)
```

`ReplyKeyboardMarkup` es el teclado que aparece en el chat. `resize_keyboard=True` lo
adapta al ancho del celular.

#### El estado encendido/apagado

```python
def _leer_estado() -> bool:
    try:
        return Path(ESTADO_FILE).read_text(encoding="utf-8").strip() == "1"
    except FileNotFoundError:
        return True
```

Si el archivo **no existe**, asume que está encendido. Por eso nunca hace falta crear
`estado_bot.txt` a mano: si no está, el bot arranca funcionando.

#### `handle_message`: los 9 pasos

1. Si el bot está apagado, avisa y corta
2. Si el chat está en estado de edición, deriva a `_manejar_edicion`
3. Si tiene gastos pendientes, deriva a `_manejar_confirmacion`
4. Si tocó un botón sin nada pendiente, avisa
5. Llama a `interpretar(texto)` dentro de un `try` con tres `except` distintos:
   - `ValueError` → el mensaje de la IA es entendible para el usuario (key inválida)
   - `RuntimeError` → no hay ninguna API key configurada
   - `Exception` → la IA no está disponible, avisa que reintente
6. Filtra los que tengan monto ≤ 0 o descripción vacía
7. Deduplica
8. Si no queda nada, pide un ejemplo
9. Guarda en `PENDIENTES[chat_id]` y pide confirmación

#### La deduplicación

```python
clave = (g.descripcion.strip().lower(), round(g.monto, 2), g.moneda, g.categoria, g.fecha)
```

Dos gastos son el mismo si coinciden los cinco campos. `round(monto, 2)` evita que
`4500.0` y `4500.0000001` cuenten como distintos.

#### `match texto: case ...`

```python
match texto:
    case "✅ Sí, guardar":
        ...
    case "✏️ Editar Moneda":
        ...
    case _:
        ...
```

Es la sintaxis `switch` de Python 3.10+. El `case _` es el `default`: no coincide con
ninguno de los anteriores.

#### `parse_mode="Markdown"`

El resumen se manda con Markdown activado para poder poner los asteriscos de cursiva. El
riesgo: si una descripción trae un `*` o un `_`, Telegram responde `400 can't parse
entities` y el mensaje no sale.

#### La instancia única

La API de Telegram admite un solo `getUpdates` activo por token. Si corrés el bot dos
veces, Telegram corta el polling con `terminated by other getUpdates request`.

La solución tiene dos capas:

```python
def _cerrar_instancias_anteriores() -> None:
    ps = ("(Get-CimInstance Win32_Process | "
          "Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'bot\\.py' } | "
          "Select-Object -ExpandProperty ProcessId) -join ' '")
```

1. **Mata las anteriores**: consulta con PowerShell los `python.exe` cuya línea de
   comandos mentione `bot.py` y los termina con `taskkill /F`, salvo el proceso actual

```python
def _adquirir_lock_instancia() -> None:
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    for _ in range(30):
        if _intentar_bloquear(fd):
            break
        time.sleep(0.2)
```

2. **Toma un lock**: abre `bot.lock` y hace un bloqueo **no bloqueante** de 1 byte con
   `msvcrt.locking`. Reintenta 30 veces con pausas de 200 ms (6 segundos en total). Si no
   lo logra, avisa y termina con `sys.exit(1)`

`bot.lock` nunca se borra: el bloqueo lo libera el sistema operativo al cerrarse el
proceso. Es como un "token de exclusividad".

Además, `run_polling(drop_pending_updates=True)` descarta los updates pendientes, que es
justo lo que evita el `ConflictError`.

#### Generar y abrir el `.tag`

```python
def _abrir_dashboard_tagui() -> None:
    tag = config.BASE_DIR / "tagui" / "abrir_dashboard.tag"
    tag.write_text(
        f"{config.URL_DASHBOARD}\n\nwait 5\n",
        encoding="utf-8",
    )
    subprocess.Popen(
        ["cmd", "/c", "tagui abrir_dashboard.tag"],
        cwd=str(config.BASE_DIR / "tagui"),
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
```

El archivo `.tag` se **reescribe en cada `/reporte`**, así que siempre lleva el
`GOOGLE_SHEET_ID` actualizado. Los dos detalles que hacen que funcione:

- va por `cmd /c`, porque Windows no ejecuta `.cmd` directo desde `Popen`
- se pasa solo el nombre del archivo y el directorio va en `cwd`, para que la ruta con
  acentos no rompa la codepage

#### El arranque

```python
def main() -> None:
    if not config.TOKEN_TELEGRAM:
        logger.error("No se encontró TELEGRAM_TOKEN en .env")
        return
    _adquirir_lock_instancia()
    app = ApplicationBuilder().token(...).build()
    app.add_handler(CommandHandler("start", start))
    ...
    app.run_polling(drop_pending_updates=True)
```

`ApplicationBuilder()` es el patrón *builder*: se encadena y al final se llama `build()`.
`run_polling()` es el bucle infinito que queda escuchando.

`if __name__ == "__main__": main()` hace que el archivo se pueda importar sin arrancar el
bot, que es lo que/testing y las importaciones de otros módulos necesitan.

---

### 9.10 `tagui/abrir_dashboard.tag`

TagUI es un framework RPA de código abierto de AI Singapore. Los archivos `.tag` son
flujos de navegación.

```
// Abre el dashboard de gastos en Google Sheets (rol RPA de TagUI)
// En esta build de TagUI la navegación se indica con la URL en su propia línea.

https://docs.google.com/spreadsheets/d/1d-6FsBWTfojx8B4jyThL9uG5xnw83K14MZh5cikoqTM

wait 5
```

Tres cosas para saber:

- La URL va **desnuda en su propia línea**. Esta build **no** entiende el paso
  `url https://...`: responde `cannot understand step url`. El ejemplo oficial del
  proyecto (`flows/samples/1_google.tag`) hace igual.
- `wait 5` espera 5 segundos a que la página cargue antes de terminar el flujo
- El archivo lo regenera `bot.py` en cada `/reporte`, así que se puede editar a mano
  para pruebas, pero se pisa en cada `/reporte`

---

### 9.11 `iniciar_bot.bat`

```bat
@echo off
cd /d "%~dp0"
py bot.py
pause
```

| Línea | Qué hace |
|---|---|
| `@echo off` | No imprime cada comando |
| `cd /d "%~dp0"` | Cambia a la carpeta del `.bat`. El `/d` permite cambiar de disco; `%~dp0` es la ruta de la carpeta del propio archivo |
| `py bot.py` | Arranca el bot |
| `pause` | No cierra la ventana al terminar, así se puede leer el error |

---

### 9.12 Archivos de apoyo

| Archivo | Qué es |
|---|---|
| `credentials.json` | Llave JSON de la Service Account. **Secreto.** No es código |
| `estado_bot.txt` | Un `1` o un `0`. Si no existe, se asume encendido |
| `bot.lock` | Donde se anota el PID y se toma el lock de instancia |
| `.gitignore` | Excluye `.env`, `credentials.json`, `__pycache__`, logs y `bot.lock` |

---

## 10. Glosario

### Términos del dominio

| Término | Qué es |
|---|---|
| **RPA** | Robotic Process Automation. Automatizar tareas que una persona haría en una interfaz |
| **TagUI** | Framework RPA open source (AI Singapore) que automatiza el navegador. Los flujos son archivos `.tag` |
| **Bot de Telegram** | Programa que responde mensajes en un chat, usando la Telegram Bot API |
| **LLM** | Large Language Model. El modelo de IA que interpreta el texto |
| **Prompt** | Las instrucciones que se le mandan al modelo |
| **JSON** | Formato de texto estructurado, con listas `[]` y objetos `{}` |
| **API** | Interfaz para que un programa use otro servicio |
| **gspread** | Librería de Python para hablar con Google Sheets |
| **Scraping** | Leer datos del HTML de una web automáticamente |
| **Expresión regular** | Patrón que busca texto dentro de otro texto |
| **Service Account** | Cuenta de Google para un programa, con su propia llave JSON |
| **Secreto** | Token o clave que nunca se sube al repositorio |
| **Asíncrono** | Código que espera sin bloquear. `async` / `await` |
| **Batch update** | Mandar muchas operaciones a la API en un solo pedido |
| **PID** | Número de identificación de un proceso en Windows |
| **Lock** | Bloqueo de archivo para garantizar que un solo proceso lo use |

### Sintaxis de Python usada en el proyecto

| Sintaxis | Qué hace | Dónde |
|---|---|---|
| `@dataclass` | Genera la clase solo con sus campos | `datos.py` |
| `global` | Declara que la función modifica una variable de módulo | `bot.py`, `excel_manager.py`, `llm_parser.py` |
| `async` / `await` | Funciones que esperan sin bloquear | `bot.py` |
| `match` / `case` | `switch` de Python 3.10+ | `bot.py` |
| `f"..."` | String con variables dentro | en todo el proyecto |
| `f"{{...}}"` | Llaves literales dentro de un f-string | `llm_parser.py` |
| `r"..."` | String crudo: no interpreta `\` | `llm_parser.py`, `dolar.py` |
| `-> str` | Anotación de tipo de retorno. No obliga a nada | en todo el proyecto |
| `[... for x in y]` | List comprehension | `excel_manager.py` |
| `defaultdict(float)` | Diccionario que arranca en 0 si la clave no existe | `tagui_dashboard.py` |
| `dict.fromkeys(...)` | Quita duplicados conservando el orden | `llm_parser.py` |
| `try` / `except` | Atrapa errores | en todo el proyecto |
| `setdefault(k, v)` | Asigna solo si la clave no existe | `config.py` |
| `if __name__ == "__main__"` | Solo ejecuta si el archivo se corrió directamente | `bot.py` |
| `__post_init__` | Se ejecuta después de que el dataclass crea el objeto | `datos.py` |
| `lambda` | Función anónima de una línea | `datos.py`, `tagui_dashboard.py` |

---

## 11. Problemas reales y cómo se resolvieron

Esta es la parte más importante del documento: son problemas que **realmente pasaron**
durante el desarrollo.

### a) `subprocess.Popen(["tagui", ...])` fallaba y el bot no abría nada

**Síntoma.** El bot respondía `📊 Dashboard listo y abierto en tu PC` y no se abría nada.

**Causa.** En Windows, TagUI se invoca con un archivo `.cmd`. `CreateProcess` de Windows
**no ejecuta archivos `.cmd` directamente** desde `Popen`, así que salía
`FileNotFoundError` — que el `except Exception` se tragaba en silencio.

**Solución.** Envolver en `cmd` y setear el directorio de trabajo:

```python
subprocess.Popen(
    ["cmd", "/c", "tagui abrir_dashboard.tag"],
    cwd=str(BASE_DIR / "tagui"),
    creationflags=subprocess.CREATE_NO_WINDOW,
)
```

**Lección.** Un `except` que solo loguea puede esconder el error real. Por eso ahora se
loguea con `logger.exception()`, que incluye el traceback.

---

### b) El acento en la ruta rompía el flujo RPA

**Síntoma.** El flujo fallaba al ejecutarse, y el proyecto estaba en una carpeta llamada
`4to Año`.

**Causa.** `cmd /c` con una ruta que tiene acento rompe la codepage de la consola.

**Solución.** No pasar la ruta con acento como argumento: se pasa solo el nombre del
archivo y la carpeta va en `cwd`.

---

### c) Esta build de TagUI no entiende el paso `url`

**Síntoma.** Escribir `url https://...` en el `.tag` responde
`cannot understand step url`.

**Causa.** En esta versión la navegación se hace escribiendo la **URL desnuda en su
propia línea**. El ejemplo oficial (`flows/samples/1_google.tag`) lo hace así.

**Solución.** `bot.py` reescribe el `.tag` con la URL en su línea, sin el prefijo.

---

### d) Crash de PhantomJS con archivos locales

**Síntoma.** La versión de TagUI usada crasheaba con
`Fatal Windows exception, 0xc0000005` al intentar abrir un `.xlsx` local con el paso `run`.

**Causa.** Incompatibilidad de PhantomJS con esa build.

**Solución.** Migrar el dashboard a **Google Sheets** (nube) y cambiar la apertura por
navegación web, sin `run` local.

> **Histórico.** Ya no hay archivos locales en el proyecto, pero explica por qué la
> arquitectura es "nube + abrir URL" y no "generar archivo y abrirlo".

---

### e) `403 The caller does not have permission` en Google Sheets

**Síntoma.** La Service Account no podía leer ni escribir la planilla.

**Causa.** La Service Account no tenía acceso a la hoja. La cuenta de servicio **no puede
entrar manualmente**: hay que compartirle la planilla.

**Solución.** En la planilla, *Compartir* → pegar el email de la Service Account
(`algo@tu-proyecto.iam.gserviceaccount.com`) con rol **Editor**.

**Sigue siendo la causa número uno hoy.**

---

### f) `429 Quota exceeded` al escribir en Sheets

**Síntoma.** Errores de cuota al guardar.

**Causa.** Escribir celda por celda con `update_cell` agota el límite de **60 escrituras
por minuto** de la API gratuita.

**Solución.** Escribir la grilla entera en **un solo** `ws.update()` y agrupar gráficos y
estilos en **un único** `batch_update`.

---

### g) La Sheets API no acepta `PIE` como `BasicChartType`

**Síntoma.** El gráfico era rechazado por la API.

**Causa.** Para una torta hay que usar el objeto `pieChart` (`PieChartSpec`). El
`basicChart` con `BasicChartType: "PIE"` **no existe** en la API.

**Solución.** Usar `pieChart` con `domain` (los nombres de categoría) y `series` (los
montos) dentro del `spec`.

---

### h) Un documento de Google que "se colgaba eternamente"

**Síntoma.** Una planilla quedó correlacionada con sus gráficos embebidos y el navegador se
quedaba cargando para siempre, incluso para el propietario. Pero la API la leía bien.

**Diagnóstico.** El problema era **el documento, a nivel de servidor, no el código**. Esta
distinción fue clave: permitió dejar de buscar errores en el programa.

**Solución.** Crear una planilla nueva, migrar los datos por API y apuntar
`GOOGLE_SHEET_ID` a la nueva. La nueva renderiza perfecto.

> Esa planilla es la que usa el proyecto hoy, y de ahí sale el ID que aparece en el `.tag`.

---

### i) `terminated by other getUpdates request`

**Síntoma.** Telegram cortaba el polling.

**Causa.** Había más de una instancia del bot corriendo con el mismo token. Telegram solo
admite un pedido activo.

**Solución original.** Matar todas las instancias a mano y dejar una sola.

**Solución actual (automática).** `_cerrar_instancias_anteriores()` mata los `bot.py`
anteriores con PowerShell y `taskkill`, `bot.lock` garantiza la exclusividad, y
`run_polling(drop_pending_updates=True)` descarta los updates pendientes.

---

### j) Estado no persistido

**Síntoma.** Se pensaba que el estado on/off se perdía al cerrar el proceso.

**Realidad.** `estado_bot.txt` **sí** persiste el estado. Lo que sí se pierde son los
**gastos pendientes de confirmación**: viven en un diccionario en memoria, así que si el
proceso muere entre que el bot interpretó el mensaje y vos confirmaste, esa información se
va. La corrección sería persistir `PENDIENTES` en un archivo.

---

### k) La IA confunde los mensajes con varios gastos

**Síntoma.** Con `8000 de bebida y 5000 de comida`, la IA a veces devolvía un solo objeto
con un monto mezclado.

**Causa.** Fusionar importes es un error clásico de los LLM.

**Solución, en tres capas.**

1. El prompt lo prohíbe explícitamente: *"NUNCA fusiones dos importes en un solo objeto"*
2. `_dividir_en_fragmentos` parte el texto por `y`, `e`, `,`, `;` y `N por`, y repregunta
   cada fragmento
3. Solo se acepta el resultado partido si aparecen **más** gastos que en la respuesta
   original, así que nunca empeora el caso normal

---

### l) Claves de API mal copiadas

**Síntoma.** Errores raros de autenticación.

**Causa.** Pegar la key truncada, con `...` al final.

**Solución.** Validar la clave **antes** de gastar una request:

```python
def _clave_openrouter_valida() -> bool:
    clave = (config.OPENROUTER_API_KEY or "").strip()
    return bool(clave) and "..." not in clave and len(clave) >= 32
```

Si no es válida, el bot avisa con un mensaje claro en vez de mostrar un error 401.

---

## 12. Diagnóstico rápido de errores

| Síntoma | Causa probable | Cómo chequearlo |
|---|---|---|
| `No se encontró TELEGRAM_TOKEN en .env` | Falta el token | Pedilo en @BotFather y ponelo en el `.env` |
| `No hay ninguna API key configurada` | Faltan las dos keys | Revisá el `.env` |
| `La OPENROUTER_API_KEY en .env está incompleta o es inválida` | Key truncada con `...` | Pegala entera, tiene que empezar con `sk-or-v1-` |
| `OpenRouter no respondió en ninguno de los modelos probados` | Los 5 modelos fallaron | Esperá unos minutos y reintentá; puede ser rate limit |
| `403 The caller does not have permission` | La planilla no está compartida con la Service Account | Compartila con el email del `credentials.json`, rol Editor |
| `429 Quota exceeded` | Se pasó el límite de escrituras | El dashboard escribe en lote; si insiste, esperá un minuto |
| `El bot dice "Estoy apagado"` | `estado_bot.txt` tiene `0` | Mandá `/encender` |
| `Ya hay otra instancia del bot que no se pudo cerrar` | El lock no se liberó en 6 s | Cerrá el `bot.py` anterior desde el Administrador de tareas |
| El bot no guarda nada en Sheets | Credenciales mal, hoja no compartida, o `GOOGLE_SHEET_ID` mal | Verificá los tres |
| `/reporte` no abre nada | TagUI no está en el PATH | Corré `tagui` en la terminal; si no responde, reinstalalo |
| El dashboard no muestra el cartel del dólar | DolarHoy caído o cambió su HTML | Es esperado: el resto del dashboard se genera igual |
| `400 can't parse entities` | Un `*` o `_` en una descripción con `parse_mode="Markdown"` | Evitá esos caracteres en las descripciones |
| El bot se apaga solo a la medianoche | `HOY` quedó congelado al importar el módulo | Reiniciá el proceso |

---

## 13. Limitaciones conocidas

1. **La cotización depende de un sitio de terceros.** `dolar.py` interpreta el HTML con
   regex, así que un rediseño de DolarHoy rompe el parseo. Está protegido con `try/except`:
   el dashboard se genera igual, solo sin cartel. **No hay caché**: cada gasto guardado
   dispara una consulta al portal.

2. **El cartel muestra 3 de los 5 tipos.** Se parsean Oficial, Blue, MEP, CCL y Mayorista,
   pero `_CARTEL_TIPOS` solo pinta los tres primeros. **CCL y Mayorista se descartan.**

3. **El Dashboard se excede a partir de la tercera moneda.** Se crea con 22 columnas y el
   layout avanza 11 por moneda. Con 1 o 2 monedas (el uso habitual) está bien; con 3 o
   más se pasa del ancho. El catálogo admite 6. La corrección sería calcular las columnas
   dinámicamente.

4. **`ws.update("A1", grilla)` usa el orden de argumentos viejo.** En `gspread` 6.x la
   firma es `update(values, range_name)`. La librería detecta el caso e **intercambia los
   argumentos internamente**, así que la operación es correcta, pero emite un
   `DeprecationWarning`. Funciona hoy; conviene migrar al orden actual.

5. **Solo Windows.** El lock usa `msvcrt` y `subprocess.CREATE_NO_WINDOW`, y el reemplazo
   de instancias usa PowerShell. En Linux o macOS no arranca.

6. **No hay control de acceso.** No se valida un chat_id ni una lista de usuarios
   autorizados. Cualquiera que encuentre el bot puede registrar gastos en la planilla.

7. **Llamadas de red bloqueantes dentro de handlers async.** Las llamadas al LLM y a
   Sheets son `blocking` y se ejecutan dentro de funciones `async`, así que pueden bloquear
   el procesamiento de otros chats mientras responden. La mitigación sería ejecutarlas
   fuera del hilo principal.

8. **`HOY` se congela al importar.** Ver [sección 9.6](#la-trampa-de-hoy).

9. **Los gastos pendientes no persisten.** Ver [problema j](#j-estado-no-persistido).

10. **El Dashboard se borra y recrea en cada ejecución.** Se pierde todo lo que hayas
    formateado o anotado a mano en esa pestaña.

11. **`response_format: json_object` contra un prompt que pide lista.** Con algunos modelos
    gratuitos puede fallar. Ver [sección 9.6](#la-cascada-de-modelos-de-openrouter).

12. **`LLM_MODELO` apunta por defecto a `gemini-3.6-flash`,** un modelo que puede no
    existir. Como OpenRouter tiene prioridad, solo afecta si se cae OpenRouter y no hay
    key de Gemini.

13. **La categoría `electrodomesticos` no tiene descripción en el prompt.** La IA la
    conoce como opción válida, pero no tiene guía de qué corresponde ahí.

14. **Los gastos viejos con `entertaining` siguen agrupados aparte.** La categoría se
    renombró a `entretenimiento`, pero `tagui_dashboard.py` lee la columna tal cual está en
    la planilla, así que los registros históricos con el nombre viejo forman su propio
    grupo.

15. **No hay pruebas automatizadas.** La verificación fue manual, contra la planilla real.

---

## 14. Qué cambió respecto a la documentación anterior

Esta guía reemplaza cuatro documentos que se contradecían entre sí. Los cambios de fondo:

| Antes | Ahora |
|---|---|
| La cotización la consultaba TagUI | La consulta `dolar.py` por HTTP; TagUI solo abre la URL |
| `tagui_dashboard.py` "usaba TagUI" | No usa TagUI en absoluto: solo Sheets API |
| `tagui_dashboard.py` escribía el `.tag` | Lo escribe `bot.py`, en cada `/reporte` |
| Teclado de 2 botones | 6 botones y 4 estados de edición, con sus validaciones |
| Se usaba Gemini | **OpenRouter tiene prioridad**; Gemini es la alternativa |
| Sin cascada de modelos | 5 modelos en cascada, 3 reintentos cada uno, con esperas 2/4/6 s |
| `requirements.txt` con 4 paquetes | 5 paquetes, con `httpx==0.28.1` |
| `abrir_hoja()` autenticaba en cada llamada | Hay caché del cliente con `global _cliente` |
| "9 archivos Python" | 8 archivos Python |
| `probar_ia.py` documentado | **Eliminado**: el archivo nunca existió |
| `json.loads(response.text)` directo | `_parsear_json()` quita los ``` ``` ``` antes de parsear |
| Solución manual de instancias duplicadas | Automática: PowerShell + `taskkill` + `bot.lock` + `drop_pending_updates` |
| "Reintento manual" ante caída de la IA | 3 reintentos automáticos + cascada de 5 modelos |
| Sin sección de limitaciones | 15 limitaciones documentadas y verificadas |

### Documentos reemplazados

- `DESCRIPCION_PROYECTO.md` — su contenido único (procedimiento de creación paso a paso y
  las historias de problemas) está en las secciones 4 y 11
- `EXPLICACION_CODIGO.md` — su contenido único (orden de importación, tutorial de sintaxis
  de Python) está en las secciones 2 y 10
- `GUIA_EXPLICACION_PASO_A_PASO.md` — su contenido único (tutorial de Python, glosario de
  dominio, diagnósticos) está en las secciones 10 y 12
- `explicacion_linea_por_linea/` — su contenido está en la sección 9

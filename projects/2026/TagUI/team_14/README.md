# Automatización RPA: Conciliación de Mercado Pago

Proyecto de automatización para la conciliación de liquidaciones y ventas de **Mercado Pago**.
Lee el extracto descargado de Mercado Pago y reconstruye el importe bruto total de cada operación comercial (`MOV TOTAL`) a partir del importe neto y las deducciones impositivas y comisiones (**SIRCUPA, SIRTAC, IDC y Gastos**).

Genera un libro Excel resultante con:
- **Pestaña principal (`sheet0` / `TP`)**: las **10 columnas oficiales** con el bruto comercial reconstruido (`MOV TOTAL`) y las deducciones imputadas centavo a centavo.
- **Pestaña `Control y Cuadre`**: control independiente que contrasta el total de cada retención del extracto original contra lo efectivamente imputado en la hoja principal más lo derivado a no conciliados, y valida `MOV TOTAL` fila por fila (ver [Control de cuadre](#-control-de-cuadre)).
- **Pestaña `No Conciliados`**: detalle de los cargos sin contraparte en el período, con hoja, fila, importe y motivo.

### Novedades de la Etapa 2 (Grupo 14)

| Mejora | Descripción |
|---|---|
| 🤖 **Bot de Telegram** | Conciliar enviando el extracto por chat y recibir las métricas y el Excel conciliado. |
| 🗂 **Historial de corridas** | Cada ejecución (web, Telegram o consola) queda registrada en SQLite con su detalle. Resúmenes por mes, rango de meses, **intervalo de fechas** o día, y atajos al mes en curso y al anterior. |
| 🔎 **Trazabilidad y extractos repetidos** | Cada corrida registra quién la hizo y una **huella de los datos** del extracto. El sistema avisa si un extracto es idéntico a uno ya procesado (aunque esté renombrado o se haya vuelto a descargar) o si trae datos distintos que reemplazan los de ese mes, y notifica a los administradores cuando otro usuario concilia. |
| 🔐 **Acceso al bot** | Administradores definidos en `.env` y usuarios que se vinculan con un **código de acceso** (`/vincular`). Los administradores pueden listar y revocar usuarios. |
| ⚠️ **Alertas** | Aviso automático cuando quedan cargos sin conciliar o el cuadre detecta diferencias. |
| ✔ **Control de cuadre real** | El control anterior comparaba los cargos contra sí mismos y daba $0.00 por construcción. Ahora contrasta contra la hoja principal generada y valida `MOV TOTAL`. |
| 📈 **Métricas ampliadas** | Ingresos, egresos, balance y totales por retención en la API, el bot y la consola. |
| 📄 **Exportación PDF y CSV** *(adicional)* | Conciliación de un mes (informe PDF, CSV de la hoja principal y CSV de pendientes) y resúmenes del historial (PDF y CSV), desde el bot y la API. |

---

## 🌐 Opción 1: Docker (recomendada)

No requiere instalar Python. Levanta la **aplicación web** y el **bot de Telegram**.

### 1. Configurar el bot (opcional)

Si solo vas a usar la web, salteá este paso: el bot no se inicia si no hay token.

1. En Telegram, abrí **@BotFather** → `/newbot` → elegí un nombre y un usuario terminado en `bot`. Copiá el **token**.
2. Copiá `.env.example` como **`.env`** y completá:

| Variable | Valor |
|---|---|
| `TELEGRAM_TOKEN` | Token de BotFather. |
| `ALLOWED_CHAT_IDS` | chat_id de los **administradores** (se completa en el paso 3). |
| `API_KEY` | Clave interna larga y aleatoria entre el bot y la API: `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Habilita la vinculación de usuarios. |
| `BOT_CODIGO_ACCESO` | Código que los usuarios envían con `/vincular CODIGO`. Compartilo solo con quienes deban usar el bot. |

> ⚠️ Estos valores van **solo** en `.env`, que está excluido del repositorio. Nunca los pongas en `.env.example`.

### 2. Iniciar

```bash
docker compose up -d --build
```

*(En Windows podés hacer **doble clic en `iniciar.bat`**).*

- Web: **[http://localhost:8000](http://localhost:8000)**
- El historial se guarda en `data/conciliaciones.db` (volumen persistente).

### 3. Autorizar usuarios del bot

La autenticación la resuelve Telegram (cada mensaje llega con el `chat_id` de una cuenta verificada); la autorización, el bot:

- **Administradores:** escribile `/start` al bot, que responde con tu **chat_id**. Agregalo a `ALLOWED_CHAT_IDS` en `.env` y aplicá el cambio con `docker compose up -d`.
- **Usuarios:** envían `/vincular CODIGO` con el valor de `BOT_CODIGO_ACCESO`. El bot borra ese mensaje del chat, registra al usuario en la base y lo habilita sin reiniciar nada. Tras 5 intentos fallidos se bloquea ese chat durante 15 minutos.
- Los administradores ven los usuarios con `/usuarios` y quitan accesos con `/revocar CHAT_ID`. Cada usuario puede salir con `/desvincular`.

### 4. Usar

**Web:** arrastrá el extracto (`MP YYYY-MM (M).xlsx`), presioná **"Iniciar Conciliación RPA"** y descargá el resultado.

**Telegram:** enviá el extracto como archivo. El bot responde con las métricas, el Excel conciliado y las alertas que correspondan.

| Comando | Acción |
|---|---|
| *(enviar un .xlsx)* | Concilia el extracto. Si el nombre no tiene el período, lo toma del comentario del archivo o lo pregunta. |
| `/resumen 2025-10` | Resumen de un mes. |
| `/resumen 2025-09 2025-12` | Resumen de un rango de meses: totales y detalle mes a mes. |
| `/resumen 01-11-2025 a 15-11-2025` | Resumen de un intervalo de fechas (puede cruzar meses), con detalle por día. |
| `/resumen 23-11-2025` | Resumen de un día. |
| `/resumen actual` · `/resumen anterior` | Mes en curso o mes anterior. |
| `/historial [n]` | Últimas `n` corridas registradas (por defecto 10), con autor y si repitieron o reemplazaron datos. |
| `/vincular CODIGO` · `/desvincular` | Habilitar o quitar el acceso de la cuenta. |
| `/usuarios` · `/revocar CHAT_ID` | *(Administradores)* Ver usuarios vinculados y quitar accesos. |
| `/cancelar` | Descarta un archivo que quedó esperando el período. |
| `/start`, `/ayuda` | Ayuda y chat_id. |

**Exportar:** debajo del Excel conciliado aparecen los botones **📄 PDF**, **🧾 CSV** y, si hay cargos sin conciliar, **🧾 CSV pendientes** (disponibles durante 1 hora). Cada `/resumen` trae los botones **📄 PDF** y **🧾 CSV**.

| Archivo | Contenido |
|---|---|
| `conciliacion_YYYY-MM.pdf` | Informe: resultado, retenciones, control de cuadre y detalle de cargos no conciliados. |
| `conciliacion_YYYY-MM.csv` | Hoja principal conciliada (10 columnas oficiales). |
| `pendientes_YYYY-MM.csv` | Cargos no conciliados con su motivo. |
| `resumen_….pdf` / `.csv` | Resumen del historial: detalle por mes (o por día, si se pidió un intervalo de fechas) y totales. |

Los CSV usan `;` como separador, coma decimal y UTF-8 con BOM: se abren directamente en Excel en español.

Para detener todo: `docker compose down` (o doble clic en `detener.bat`).
Logs del bot: `docker compose logs -f bot-telegram`.

---

## 💻 Opción 2: Local con Python (sin Docker)

Requiere Python 3.11 o superior.

Si Docker no está en ejecución, **`iniciar.bat` usa este modo automáticamente**: instala las dependencias, abre el bot de Telegram en otra ventana (si `.env` tiene `TELEGRAM_TOKEN`) y levanta la web en `http://localhost:8000`. La API y el bot leen el mismo `.env`, con `API_URL=http://localhost:8000`. Para detener todo: `detener.bat`.

A mano:

```bash
# 1. Entorno virtual e instalación de dependencias
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

# 2. Servidor web + API
python -m uvicorn app:app --host 127.0.0.1 --port 8000

# 3. (Opcional) Bot de Telegram, en otra terminal con el entorno activado.
#    Lee el archivo .env; dejar API_URL=http://localhost:8000
python bot.py
```

---

## ⚙️ Opción 3: Consola (CLI / Batch)

```bash
# El período se detecta del nombre del archivo:
python conciliar.py --archivo "docs/MP 2025-09 (M).xlsx"
python conciliar.py --archivo "docs/MP 2025-11 (M).xlsx"

# Si el nombre no tiene el período, indicarlo:
python conciliar.py --archivo "extracto.xlsx" --periodo 2025-10

# Sin registrar la corrida en el historial:
python conciliar.py --archivo "docs/MP 2025-12 (M).xlsx" --no-registrar
```

Con Docker, sin instalar Python (la imagen no incluye `docs/`, por eso se monta la carpeta):

```powershell
docker run --rm -v "${PWD}:/app" -w /app team_14-conciliador-rpa python conciliar.py --archivo "docs/MP 2025-10 (M).xlsx"
```

El Excel queda en `outputs/conciliacion_YYYY-MM.xlsx` y la consola muestra métricas, el cuadre por hoja y la validación de `MOV TOTAL`.

---

## 🔌 API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/salud` | Estado del servicio. |
| `POST` | `/api/conciliar` | Form-data: `archivo` (.xlsx), `periodo` (opcional, `YYYY-MM`), `hoja` (default `sheet0`), `canal` (`web`/`telegram`), `chat_id` (opcional). Devuelve métricas, cuadre, pendientes y token de descarga, y registra la corrida. |
| `GET` | `/api/descargar/{token}?formato=xlsx` | Descarga el resultado (disponible durante 1 hora). `formato`: `xlsx` (default), `pdf`, `csv` o `csv-pendientes`. |
| `GET` | `/api/resumen?desde=YYYY-MM&hasta=YYYY-MM` | Resumen de un mes o rango (`hasta` opcional) con la última corrida de cada período. |
| `GET` | `/api/resumen/exportar?desde=YYYY-MM&hasta=YYYY-MM&formato=pdf` | El mismo resumen como archivo. `formato`: `pdf` o `csv`. |
| `GET` | `/api/resumen/dias?desde=DD-MM-AAAA&hasta=DD-MM-AAAA` | Resumen de un intervalo de fechas con detalle por día (también acepta `AAAA-MM-DD`). |
| `GET` | `/api/resumen/dias/exportar?desde=…&hasta=…&formato=pdf` | El resumen por fechas como archivo (`pdf` o `csv`). |
| `GET` | `/api/usuarios` · `/api/usuarios/{chat_id}` | Usuarios vinculados / si un chat está autorizado. Requiere encabezado `X-API-Key`. |
| `POST` | `/api/usuarios/vincular` · `/api/usuarios/desvincular` | Form-data `chat_id`, `codigo`, `nombre` / `chat_id`. Requiere `X-API-Key`. |
| `GET` | `/api/historial?limite=10` | Últimas corridas registradas (máx. 50). |

Documentación interactiva: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📁 Estructura del Proyecto

```text
team_6/
├── conciliar.py            # Motor de cruce y conciliación RPA + control de cuadre + CLI
├── app.py                  # API FastAPI y servidor del frontend
├── db.py                   # Historial de corridas (SQLite)
├── exportar.py             # Exportación a PDF y CSV
├── entorno.py              # Lectura del .env en modo local (sin Docker)
├── bot.py                  # Bot de Telegram (consume la API)
├── Dockerfile              # Imagen única para la API y el bot
├── docker-compose.yml      # Servicios: conciliador-rpa (puerto 8000) y bot-telegram
├── .env.example            # Plantilla de configuración del bot (copiar como .env)
├── iniciar.bat / detener.bat
├── requirements.txt
├── static/                 # Frontend web (HTML, CSS, JS)
├── docs/                   # Extractos de prueba (MP YYYY-MM (M).xlsx)
├── data/                   # Historial SQLite (se crea al ejecutar; no se versiona)
└── outputs/                # Excel generados en modo consola (no se versiona)
```

### Arquitectura

```text
 Navegador ──┐
             ├──► API FastAPI (app.py) ──► motor (conciliar.py) ──► Excel conciliado
 Telegram ───┘         │
   (bot.py)            └──► historial SQLite (db.py) ◄── consola (conciliar.py)
```

El bot no accede al motor directamente: usa la API por la red interna de Docker (`http://conciliador-rpa:8000`). Así todas las corridas, de cualquier canal, quedan en el mismo historial.

---

## 🔍 Reglas del Cruce Contable

1. **Lectura segura:** abre el Excel en modo solo lectura y corta al terminar la tabla oficial de Mercado Pago (omite notas o tablas pegadas al pie).
2. **Cruce por ID:** asocia cada retención o comisión al movimiento principal mediante su `REFERENCE_ID`, distinguiendo operaciones regulares de anulaciones o devoluciones.
3. **Resolución de IDC alfanuméricos:** los cargos de IDC con códigos internos (ej. `0007eymbh3`) se vinculan solo si hay un único candidato por fecha y por la ecuación `neto + deducciones + IDC = base imponible`.
4. **No conciliados:** si un cargo no tiene contraparte en el período, se lista en la pestaña `No Conciliados` con su motivo e importe.
5. **Protección contra bloqueos:** si el archivo destino está abierto en Excel, se guarda una copia con marca de tiempo.

## ✔ Control de cuadre

La pestaña `Control y Cuadre` (y la respuesta de la API y del bot) realiza dos verificaciones sobre la **hoja principal efectivamente generada**:

**1. Cuadre por hoja de cargos**

```text
Diferencia = Total del extracto − (Imputado en la hoja principal + No conciliado)
```

El *imputado* se suma desde las columnas `SIRCUPA`, `SIRTAC`, `GASTOS` e `IDC` de la hoja principal. Si un cargo se pierde, se duplica o se imputa por un importe distinto, la diferencia deja de ser cero (tolerancia: $0,01).

**2. Validación de `MOV TOTAL` fila por fila**

| Caso | Regla |
|---|---|
| General | `MOV TOTAL = TRANSACTION − (SIRCUPA + SIRTAC + GASTOS + IDC)` |
| Operación con fila "Impuesto por extracción" (mismo ID y fecha) | `MOV TOTAL = TRANSACTION − (SIRCUPA + SIRTAC + GASTOS)` |
| Fila "Impuesto por extracción" | `MOV TOTAL = TRANSACTION` |

Las deducciones se escriben con signo negativo, por eso se restan.

> **Nota (Etapa 2):** en la versión original, el control comparaba `asociados + pendientes` contra el total de esos mismos cargos, por lo que la diferencia era siempre $0.00 independientemente del resultado.

### Criterio de métricas

- **Ingresos:** suma de `TRANSACTION` positivos. **Egresos:** suma de `TRANSACTION` negativos (incluye las filas "Impuesto por extracción"). **Balance:** ingresos − egresos.
- **Totales por retención:** importes leídos del extracto para el período.
- **Resúmenes por rango:** se usa la **última corrida** registrada de cada mes, de modo que reprocesar un mes no duplica sus valores.
- **Resúmenes por fechas:** cada corrida guarda su detalle (movimientos y cargos no conciliados). Los movimientos se agrupan por `RELEASE_DATE`; las retenciones y gastos son los imputados a esos movimientos, y los cargos no conciliados se agrupan por la fecha de la retención. Al reprocesar un mes, se conserva solo el detalle de la última corrida. Las corridas registradas antes de esta función no tienen detalle: hay que volver a procesar el extracto.
- **Extractos repetidos:** la huella es un SHA-256 de los movimientos y cargos leídos del período (fecha, tipo, ID e importes), no del archivo. Por eso reconoce el mismo extracto aunque cambie el nombre o se vuelva a descargar, y detecta un extracto corregido aunque tenga el mismo nombre. Reprocesar el mismo extracto no altera los resultados (el proceso es idempotente): solo se registra la corrida y se informa. Si el extracto trae datos distintos, el bot muestra qué cambió (movimientos, balance y no conciliado) y la nueva corrida pasa a ser la que usan los resúmenes.
- **Notificaciones a administradores:** cuando alguien concilia por Telegram, los administradores (salvo quien concilió) reciben un aviso con el período, el autor, el resultado y si fue el mismo extracto o reemplazó datos. Las corridas hechas por la web o la consola quedan en el historial con su autor, pero no generan aviso.
- **Disponibilidad de los datos:** los resúmenes reflejan los extractos procesados. No hay consulta en tiempo real a Mercado Pago, porque la descarga automática del extracto quedó fuera del alcance del proyecto.

---

## 🛠 Solución de problemas

| Síntoma | Causa / solución |
|---|---|
| El bot no responde | Verificar que los contenedores estén levantados (`docker compose ps`) y revisar `docker compose logs bot-telegram`. |
| "No estás autorizado" | Enviar `/vincular CODIGO`, o agregar el chat_id a `ALLOWED_CHAT_IDS` en `.env` y ejecutar `docker compose up -d`. |
| "La vinculación por código no está habilitada" | Completar `API_KEY` y `BOT_CODIGO_ACCESO` en `.env` y ejecutar `docker compose up -d`. |
| "No tienen detalle diario guardado" | Esas corridas son anteriores al resumen por fechas: volver a procesar el extracto del mes. |
| "No se pudo detectar el período" | Renombrar el archivo como `MP YYYY-MM (M).xlsx` o indicar el período (comentario del archivo en Telegram, `--periodo` en consola). |
| "No se encontraron movimientos para el período" | El extracto no contiene operaciones de ese mes: verificar el período indicado. |
| La web no carga después de `iniciar.bat` | Esperar unos segundos a que el servidor termine de iniciar y actualizar (F5). |

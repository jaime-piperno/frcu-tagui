# Integrador RPA — Bot de Gastos

Bot RPA que registra gastos personales enviados por Telegram. El usuario
escribe el gasto en cualquier formato, el bot lo interpreta con un LLM
(Gemini), pide confirmación y lo guarda en una Google Sheet con
dashboard de análisis.

## Arquitectura

- **`bot.py`** — Bot de Telegram (punto de entrada). Usa `python-telegram-bot`.
- **`llm_parser.py`** — Interpreta el mensaje con un LLM (Gemini u OpenRouter, el
  que esté configurado en `.env`). Devuelve lista de `Gasto`; si la API falla,
  el bot avisa al usuario.
- **`categorias.py`** — Lista de categorías y monedas permitidas (usadas por el LLM
  y para ordenar el dashboard).
- **`datos.py`** — Modelo de datos del gasto.
- **`excel_manager.py`** — Lectura/escritura de los gastos en Google Sheets
  (API Google Sheets vía `gspread` + credenciales de Service Account).
- **`dolar.py`** — Consulta la cotización actual del dólar en
  https://dolarhoy.com (Oficial, Blue, MEP, CCL y Mayorista) para el cartel del dashboard.
- **`tagui_dashboard.py`** — Genera la hoja `Dashboard` (totales por categoría/moneda
  + tortas + cartel del dólar) dentro de la Google Sheet.
- **`tagui/abrir_dashboard.tag`** — Script RPA de TagUI que abre el dashboard
  en Google Sheets (navegación web con `url`, sin `run` local).
- **`config.py`** — Configuración desde `.env`.

## Instalación

```bash
pip install -r requirements.txt
```

## Configuración del token de Telegram

1. En Telegram, busca **@BotFather** y envía `/newbot`.
2. Elegí un nombre y un username (que termine en `bot`).
3. Copiá el token y ponelo en el archivo `.env`:

```
TELEGRAM_TOKEN=123456:ABC-DEF...
```

### API de Gemini (interpretación del mensaje)

1. Entrá a https://aistudio.google.com/apikey (con cuenta de Google).
2. Creá una API key (tiene límite gratuito, sin tarjeta).
3. Ponela en `.env`:

```
GEMINI_API_KEY=AIza...
```

Esta key es necesaria para interpretar los mensajes.

### Alternativa: OpenRouter (si Gemini está saturado o denegada)

El bot también soporta **OpenRouter** (API compatible con OpenAI). Si
`OPENROUTER_API_KEY` está seteada en `.env`, se usa esa y se ignora Gemini:

```
OPENROUTER_API_KEY=sk-or-v1-...
```

### Google Sheets (almacenamiento del dashboard)

1. Creá un proyecto en https://console.cloud.google.com y habilitá la
   **Google Sheets API**.
2. Creá una **Service Account** y generá una clave JSON.
3. Guardá ese JSON como `credentials.json` en la carpeta del proyecto.
4. Creá una hoja en Google Sheets y compartila con el email de la Service
   Account (rol **Editor**).
5. Copiá el ID de la hoja (la parte de la URL entre `/d/` y `/edit`) en `.env`:

```
GOOGLE_SHEET_ID=TU_SHEET_ID
```

## Ejecutar el bot

```bash
py bot.py
```

En Telegram, buscá el username de tu bot y enviá `/start`.

## Ejemplos de mensajes

- `almuerzo 4500`
- `$3200 uber al aeropuerto`
- `netflix 1500 usd`
- `compre una camisa por 12000 pesos`
- `50 en supermercado`

El bot responde con lo que entendió (categoría, descripción, monto, moneda)
y pide **confirmación** antes de guardar (✅ Sí, guardar / ❌ No, cancelar).

## Comandos

- `/start` — Iniciar.
- `/encender` — Activar la captura de gastos.
- `/apagar` — Desactivar la captura de gastos.
- `/reporte` — Actualiza el dashboard en Google Sheets y lo abre con TagUI.
- `/cancelar` — Cancela un gasto pendiente.

## Google Sheet

Los gastos se guardan en la hoja `Gastos`.
El comando `/reporte` agrega/actualiza la hoja `Dashboard` con totales y
tortas de gastos por categoría (una por moneda) y un cartel con la cotización
del dólar del día (tomada de dolarhoy.com), y lo abre en el navegador vía TagUI
(`url` de Google Sheets).

## Mejora futura

Extraer datos de imágenes (recibos/facturas) usando OCR (SikuliX de TagUI
o un modelo de visión) en lugar de solo texto.

---

## Etapa 2 – Mejora

- **Número de Grupo :** 7
- **Miembros (Members):**
  - Ducret Leturia, Damián Osvaldo
  - Leiva, Octavio
  - Meier, Carlos David
  - Schenberger, Valentina
  - Szajnowicz, Ignacio

### Descripción de la Mejora

- **¿Qué se mejoró?:**
  1. **Recepción y Procesamiento de Comprobantes por Imagen (`handle_photo` en `bot.py`):** El bot ahora acepta fotos de recibos, facturas o tickets de compra enviados directamente al chat (como foto o archivo de imagen).
  2. **Motor de OCR con TagUI y SikuliX (`ocr_tagui.py`):** Se integró el motor de visión y OCR de TagUI (basado en SikuliX y Tesseract). El módulo genera dinámicamente el script `.tag` y el paquete Jython (`.sikuli/ocr_ticket.py`) para ejecutar `sikulix.jar` de manera desatendida y extraer el texto bruto de la imagen.
  3. **Parser Multimodal Híbrido OCR + LLM (`interpretar_ocr` en `llm_parser.py`):** Se diseñó un prompt especializado de sistema (`PROMPT_SISTEMA_OCR`) para interpretar el texto desestructurado y ruidoso típico de tickets térmicos. El LLM (Gemini u OpenRouter) reconstruye importes, fecha del comprobante, comercio/descripción y categoría sugerida, permitiendo además que el usuario adjunte notas aclaratorias en el epígrafe de la foto.
  4. **Teclado Interactivo de Corrección y Confirmación:** Tras procesar el ticket (o mensaje de texto), el bot presenta un teclado con botones para modificar en caliente el monto, la categoría, la fecha o la descripción antes del guardado definitivo en Google Sheets.
  5. **Parametrización y Portabilidad del Entorno (`config.py` y `.env`):** Se desacopló la ruta absoluta de instalación de TagUI (`TAGUI_DIR`), permitiendo configurar instalaciones personalizadas con fallback automático a `C:\tagui\src`, y se aisló el script RPA `abrir_dashboard.tag` para evitar filtraciones de IDs en Git.
  6. **Control de Instancia Única y Concurrencia (`bot.lock`):** Se agregó un mecanismo de mutex por bloqueo de archivo (`msvcrt`) y terminación limpia de procesos huérfanos anteriores para evitar ejecuciones duplicadas del bot.

- **¿Por qué?:**
  En la Etapa 1, la carga de gastos requería que el usuario redactara manualmente el texto de cada compra. La captura automática mediante foto de tickets/facturas era la principal mejora futura planteada. Implementarla mediante el motor SikuliX/Tesseract de TagUI cumple con el requisito de integración RPA de la cátedra, combinándolo con la inteligencia de los LLMs para sanear errores de lectura óptica y estructurar la información sin fricción para el usuario.

### Instrucciones de Uso Actualizadas (Updated Usage Instructions)

- **Requisitos adicionales para OCR:**
  - Tener instalado **Java** (JRE de 64 bits en el `PATH` del sistema) necesario para ejecutar el motor SikuliX:
    - [Link para descargar Java (Oracle)](https://www.java.com/es/download/).
  - Tener instalado **TagUI** (se recomienda descomprimir en `C:\tagui` de modo que la carpeta `src` quede en `C:\tagui\src`, o bien definir la variable `TAGUI_DIR` en el `.env`):
    - [Repositorio de TagUI en GitHub para instalarlo](https://github.com/aisingapore/TagUI).
- **Nuevas interacciones en Telegram:**
  - **Envío de comprobantes:** Sacale una foto a un ticket o factura y enviala al chat (podés agregar una nota en el mensaje como *"almuerzo de trabajo"*).
  - El bot responderá con los datos detectados por el OCR y el LLM, desplegando el teclado interactivo con opciones:
    - `✅ Sí, guardar` / `❌ No, cancelar`
    - `✏️ Editar Moneda` / `✏️ Editar Categoría`
    - `📅 Editar Fecha` / `📝 Editar Descripción`
- **Variables de entorno opcionales en `.env`:**
  - `TAGUI_DIR` (opcional, por defecto `C:\tagui\src`): ruta al directorio `src` de instalación de TagUI.

### Información Adicional – Etapa 2

- **Decisiones técnicas y desafíos resueltos:**
  - **Integración Java/SikuliX sin ventana emergente:** SikuliX se ejecuta mediante un subproceso silencioso (`CREATE_NO_WINDOW`) inyectando dinámicamente `jython-standalone-2.7.1.jar` y redirigiendo la captura a un log local (`tagui/ocr_sikuli.log`) para depuración en caso de fallos.
  - **Tolerancia a ruido óptico en tickets:** Los tickets reales suelen tener caracteres cortados, tinta tenue o saltos de línea irregulares. En lugar de procesar el texto con expresiones regulares rígidas, se delega la normalización al LLM con un prompt especializado que reconoce patrones de tickets fiscales.
- **Limitaciones restantes:**
  - La velocidad del OCR depende de la respuesta del motor Java/SikuliX en la máquina host (suele tardar entre 3 y 8 segundos por imagen).
  - Imágenes muy borrosas o con iluminación deficiente pueden impedir que Tesseract reconozca texto legible, caso en el cual el bot notifica al usuario para que reintente con una foto más clara.

### Próximas Mejoras / Trabajo Futuro

- **Gestión de Concurrencia y Sesiones Aisladas en OCR:**
  - **Problema actual:** El pipeline de OCR utiliza rutas de archivos fijas (`ticket_actual.png`, `ocr_resultado.txt`), lo que provoca que peticiones concurrentes de múltiples usuarios se pisen y sobreescriban entre sí durante la ejecución de SikuliX.
  - **Posible solución:**
    - Reemplazar los archivos estáticos por directorios temporales únicos con identificadores UUID por mensaje/usuario (`tempfile`).
    - Incorporar un mecanismo de encolamiento asíncrono (`asyncio.Queue` o semáforo con `asyncio.Lock`) para serializar el uso intensivo de CPU/Java y garantizar que cada comprobante se procese de punta a punta de forma aislada e íntegra.
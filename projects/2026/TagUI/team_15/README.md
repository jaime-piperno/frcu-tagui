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
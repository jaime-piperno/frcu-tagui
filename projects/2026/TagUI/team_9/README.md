# 🛒 Comparador RPA Inteligente de Precios: Supermercados Argentinos
## UTN FRCU – Tecnologías para la Automatización (Año 2026)
### Trabajo Práctico Integrador – Etapa 2: Mejoras RPA (alertas por Telegram)

---

### 👥 Equipo de Trabajo (Grupo 9 · Etapa 2)
- **María Slootmans Corrá**
- **Franco Valli**
- **Victoria Nuñez Baccon**

### 🏗️ Proyecto Original (Etapa 1)
Este trabajo parte del bot RPA desarrollado por el **Grupo 1** (Lourdes Alvarez, Florencia Carballo, Alexander Ramos, Juan Martín Cruz, Santiago Manuel Allaud), disponible en [`projects/2026/TagUI/team_1`](../team_1). El motor de scraping (Puppeteer + `mouse_helper.exe`), los selectores de Carrefour/COTO/Día %, el motor de validación semántica y el reporte Excel **se mantienen intactos**: la Etapa 2 se acopla como una capa adicional al cierre de cada ejecución, sin modificar el scraping original. El detalle completo de qué se agregó y por qué está en [`docs/CAMBIOS_ETAPA2.md`](docs/CAMBIOS_ETAPA2.md).

---

## 📑 Tabla de Contenidos
1. [Nombre del Proyecto y Objetivo Principal](#1-nombre-del-proyecto-y-objetivo-principal)
2. [Problema que Resuelve y Caso de Negocio](#2-problema-que-resuelve-y-caso-de-negocio)
3. [Diagnóstico Heredado: Limitaciones de la Etapa 1](#3-diagnóstico-heredado-limitaciones-de-la-etapa-1)
4. [Funcionalidades Actuales](#4-funcionalidades-actuales)
5. [Arquitectura del Sistema](#5-arquitectura-del-sistema)
6. [Tecnologías Utilizadas](#6-tecnologías-utilizadas)
7. [Estructura Actual de Carpetas y Archivos](#7-estructura-actual-de-carpetas-y-archivos)
8. [Explicación de los Componentes Principales](#8-explicación-de-los-componentes-principales)
9. [Mejoras de la Etapa 2 en Detalle](#9-mejoras-de-la-etapa-2-en-detalle)
10. [Flujo Completo de Ejecución](#10-flujo-completo-de-ejecución)
11. [Requisitos y Dependencias](#11-requisitos-y-dependencias)
12. [Guía de Instalación y Configuración](#12-guía-de-instalación-y-configuración)
13. [Configuración del Bot de Telegram](#13-configuración-del-bot-de-telegram)
14. [Cómo Ejecutar el Proyecto (Frontend Web y Consola)](#14-cómo-ejecutar-el-proyecto-frontend-web-y-consola)
15. [Cómo Realizar una Prueba Completa](#15-cómo-realizar-una-prueba-completa)
16. [Persistencia de Datos](#16-persistencia-de-datos)
17. [Vinculación con la Materia](#17-vinculación-con-la-materia)
18. [Limitaciones Actuales](#18-limitaciones-actuales)
19. [Funcionalidades Pendientes y Próximos Pasos](#19-funcionalidades-pendientes-y-próximos-pasos)

---

## 1. Nombre del Proyecto y Objetivo Principal

**Nombre:** *Comparador RPA Inteligente de Precios y Optimizador de Canasta de Consumo Masivo — con monitoreo continuo y alertas por Telegram.*

**Objetivo Principal (Etapa 1, heredado):** Automatizar mediante RPA la recolección en vivo, validación semántica estricta, comparación y optimización de precios en tiempo real sobre los principales supermercados con plataforma online de Argentina (**Carrefour**, **COTO** y **Día %**).

**Objetivo de la Etapa 2 (agregado por el Grupo 9):** Transformar el comparador de un proceso de lazo abierto (cada corrida pisaba la anterior y dependía de que alguien abriera el dashboard) en un **vigilante autónomo del mercado**: persistir cada cotización en un historial, detectar caídas de precio reales contra ese historial y avisar de inmediato por Telegram, sin alterar el motor de scraping original.

El sistema demuestra una automatización robótica visible en Google Chrome, ejecutando las acciones paso a paso sobre el navegador de forma idéntica a la interacción de un usuario humano, persistiendo los resultados estructurados en CSV/JSONL y generando un reporte analítico de 5 hojas en Excel con el cálculo de la canasta óptima, además de un historial de precios navegable y notificaciones push cuando conviene comprar.

---

## 2. Problema que Resuelve y Caso de Negocio

En el mercado minorista argentino, la dispersión de precios para un mismo artículo o categoría entre distintas cadenas supera con frecuencia el 30% o 40%. Comparar manualmente decenas de artículos navegando múltiples portales web demanda tiempo y suele inducir a errores. Pero conocer el precio de *hoy* no alcanza: sin memoria de precios pasados, el usuario no puede saber si lo que ve es una verdadera oportunidad o el precio de siempre, y si no está mirando el dashboard en el momento exacto, se pierde la baja.

La Etapa 2 resuelve ese segundo problema: convierte al bot en un agente que recuerda cada cotización, la compara contra el pasado y **avisa proactivamente** cuando detecta una caída real de precio, sin que el usuario tenga que estar pendiente de la pantalla.

---

## 3. Diagnóstico Heredado: Limitaciones de la Etapa 1

Antes de agregar funcionalidad, se auditó el proyecto recibido y se identificaron tres limitaciones centrales que motivaron esta mejora:

| Limitación | Descripción |
| :--- | :--- |
| **Sin memoria de datos** | Cada corrida pisaba `resultados.csv`. No quedaba registro para cotejar valores entre fechas distintas. |
| **Sin detección de bajas** | El sistema contrastaba precios entre las tres cadenas en el mismo momento, pero no sabía si un producto alcanzaba su piso histórico. |
| **Sin canal proactivo** | No existían notificaciones remotas. El usuario debía abrir el dashboard y mirar la planilla para enterarse de un precio favorable. |

**Criterio técnico adoptado:** preservar intacto el código base recibido (selectores de navegador, motor de validación, reporte Excel) y acoplar la solución como una capa modular al cierre de cada ejecución del scraping, sin interferir con el motor original.

---

## 4. Funcionalidades Actuales

### Heredadas de la Etapa 1 (sin modificaciones)
- **Automatización 100% Visible Paso a Paso** sobre Google Chrome (navegación por Omnibox, tipeo letra por letra, scroll y ordenamiento por menor precio).
- **Cursor Virtual Autónomo** y **Controlador Nativo de Mouse/Omnibox** (`mouse_helper.exe`, Win32/C#).
- **Dashboard Web Interactivo** (`http://localhost:3000`) con WebSocket (`/ws/rpa-stream`) para logs y progreso en tiempo real.
- **Kill-switch** ante cierre de Chrome o del frontend, y endpoint `POST /api/abort`.
- **Motor de Validación Semántica Estricta** (`validador.js`): intención específica vs. genérica, diccionario de marcas, 4 estados de resultado.
- **Reporte Analítico en Excel de 5 Hojas** (`reporte_supermercados.xlsx`) vía `exceljs`.
- **Ejecución Dual:** Web UI (`interfaz.bat`), consola (`ejecutar.bat`) y script académico TagUI (`supermercados.tag`).

### Agregadas en la Etapa 2 (Grupo 9)
- **Historial persistente de precios** (`historial.js` + `historial_precios.jsonl`): cada corrida se anexa con fecha ISO, sin pisar corridas anteriores.
- **Motor de alertas** (en `server.js`): compara cada precio nuevo contra el historial de ese mismo producto y supermercado, y genera dos tipos de aviso — baja porcentual (`BAJA`) y mínimo histórico (`MINIMO_HISTORICO`) — evitando duplicados vía `alertas_emitidas.jsonl`.
- **Bot de Telegram** (`notificador.js`): envía el aviso de la baja detectada (y un mensaje de bienvenida al iniciar el servidor) usando `fetch()` nativo contra la API oficial de Telegram, con timeout de 10 s.
- **Panel de Historial en el Dashboard** (`public/historial-dashboard.js` + `.css`): gráfico de tendencia de precios por producto (Canvas), tabla de alertas emitidas y resumen de canasta, integrados en `public/index.html`.
- **Nuevos endpoints REST:** `GET /api/historial`, `GET /api/alertas`, `GET /api/resumen-canasta`.
- **Validación semántica reforzada con evidencia de imagen** (`validador.js`, `supermercados.tag`, `evidencia_imagenes.json`): además del nombre de texto, se compara la imagen del producto encontrado contra referencias de imagen ya confirmadas para ese ítem del catálogo, reduciendo falsos positivos cuando el nombre textual es ambiguo o está incompleto.

Ver el detalle técnico de cada mejora en la [sección 9](#9-mejoras-de-la-etapa-2-en-detalle) y en [`docs/CAMBIOS_ETAPA2.md`](docs/CAMBIOS_ETAPA2.md).

---

## 5. Arquitectura del Sistema

El sistema mantiene las tres capas originales y agrega una capa de monitoreo que se enciende al cierre de cada ejecución:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                              CAPA DE USUARIO                              │
├─────────────────────────────────────┬─────────────────────────────────────┤
│         Dashboard Web (UI)          │        Consola CLI (Windows)        │
│  - http://localhost:3000 (app.js)   │  - ejecutar.bat (Menú 7 opciones)   │
│  - historial-dashboard.js (Etapa 2) │  - Soporta argumentos directos      │
│  - WebSocket /ws/rpa-stream         │                                     │
└──────────────────┬──────────────────┴──────────────────┬──────────────────┘
                   │                                     │
                   ▼                                     ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      CAPA DE SERVICIOS Y ORQUESTACIÓN                     │
├───────────────────────────────────────────────────────────────────────────┤
│  server.js (Node.js + Express 5 + WebSocket Server 'ws')                  │
│  - API REST: /api/compra-mes, /api/buscar-individual, /api/abort, etc.    │
│  - Etapa 2: /api/historial, /api/alertas, /api/resumen-canasta            │
│  - Etapa 2: detectarAlertas() compara cada corrida contra el historial    │
└──────────────────┬─────────────────────────────────────┬──────────────────┘
                   │                                     │
                   ▼                                     ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────┐
│      MOTOR CANASTA / COMPRA MES     │   │    MOTOR BÚSQUEDA INDIVIDUAL    │
│         (rpa_runner.js)             │   │      (supermercados.tag)        │
│  Puppeteer-Core + mouse_helper.exe  │   │  Ejecutado vía TagUI CLI        │
└──────────────────┬──────────────────┘   └────────────────┬────────────────┘
                   │                                       │
                   └──────────────────┬────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                     CAPA DE VALIDACIÓN Y PERSISTENCIA                     │
├───────────────────────────────────────────────────────────────────────────┤
│  validador.js: intención, marcas, categorías + evidencia de imagen (E2)   │
│  resultados.csv: 10 columnas · reporte_supermercados.xlsx: 5 hojas        │
└──────────────────┬────────────────────────────────────────────────────────┘
                   │  (al cierre de cada corrida, capa agregada en Etapa 2)
                   ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                  CAPA DE MONITOREO CONTINUO (ETAPA 2)                     │
├───────────────────────────────────────────────────────────────────────────┤
│  historial.js → historial_precios.jsonl / alertas_emitidas.jsonl          │
│  detectarAlertas() en server.js → compara contra el historial            │
│  notificador.js → Telegram Bot API (fetch nativo, timeout 10s)           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Tecnologías Utilizadas

**Heredadas:** Node.js 18+, `puppeteer-core` 25.10.0, TagUI v6.110.0, C#/.NET Framework 4.0 (`mouse_helper.exe`), `express` 5.2.1, `ws` 8.21.3, `exceljs` 3.4.0, CSV/XLSX.

**Agregadas en la Etapa 2:**
- **Persistencia JSON Lines** (sin librerías nuevas): `historial.js` lee/escribe `.jsonl` con `fs.appendFileSync`, permitiendo anexar cada corrida sin reescribir ni releer todo el archivo.
- **Telegram Bot API:** `notificador.js` usa `fetch()` nativo de Node.js (sin SDK de terceros) contra `https://api.telegram.org/bot<token>/sendMessage`.
- **Variables de entorno:** no se agregó la dependencia `dotenv`; `server.js` incluye un parser propio (`cargarVariablesEntorno()`) que lee `.env` línea por línea y completa `process.env` sólo si la clave no está definida.
- **Gráfico de tendencias:** Canvas API nativo del navegador en `historial-dashboard.js` (sin librerías de charting).

> Nota de implementación: se evaluó una alternativa en Java/Maven (librería `telegrambots`) para el bot de Telegram; se descartó en favor de la implementación en Node.js (`notificador.js`) por no requerir un runtime ni una dependencia adicional, y por integrarse directamente con el resto del backend ya escrito en JavaScript.

---

## 7. Estructura Actual de Carpetas y Archivos

```
team_9/
├── docs/
│   ├── guia_visual.html          # Guía visual de la Etapa 1 (heredada, sin cambios).
│   └── CAMBIOS_ETAPA2.md         # Documentación detallada de los cambios del Grupo 9.
├── public/                       # Frontend web servido por Express
│   ├── app.js                    # Lógica del cliente web (WebSocket, REST, UI) — heredado.
│   ├── index.html                # Dashboard principal, ahora con panel de historial (Etapa 2).
│   ├── styles.css                # Estilos visuales — heredado.
│   ├── historial-dashboard.js    # [Etapa 2] Gráfico de tendencias, tabla de alertas y resumen.
│   └── historial-dashboard.css   # [Etapa 2] Estilos del panel de historial.
├── tests/                        # Pruebas y scripts de verificación (heredados).
├── .env.example                  # [Etapa 2] Plantilla de variables (token de Telegram, umbral).
├── .gitignore                    # Incluye ahora .env, build artifacts e IDE.
├── ejecutar.bat                  # Lanzador por lotes interactivo — heredado.
├── generar_excel.js              # Generador del reporte Excel — heredado.
├── historial.js                  # [Etapa 2] Lectura/escritura de historial y alertas en JSONL.
├── historial_precios.jsonl       # [Etapa 2] Historial acumulado de cotizaciones.
├── input.csv                     # Canasta básica mensual predefinida — heredado.
├── interfaz.bat                  # Lanzador directo del servidor y Dashboard Web — heredado.
├── mouse_helper.cs / .exe        # Controlador nativo Win32 — heredado, sin cambios.
├── notificador.js                # [Etapa 2] Envío de mensajes vía Telegram Bot API.
├── package.json / package-lock.json
├── README.md                     # Este documento.
├── resultados.csv                # Persistencia de extracciones (10 columnas) — heredado.
├── rpa_runner.js                 # Motor RPA 100% visible — heredado, sin cambios de lógica base.
├── server.js                     # Express + WebSocket + API REST + motor de alertas (Etapa 2).
├── supermercados.tag             # Script TagUI + extracción de evidencia de imagen (Etapa 2).
└── validador.js                  # Validación semántica + evidencia de imagen (Etapa 2).
```

---

## 8. Explicación de los Componentes Principales

| Archivo | Responsabilidad Principal | Origen |
| :--- | :--- | :--- |
| `rpa_runner.js` | Motor de Compra del Mes (Puppeteer + `mouse_helper.exe`). | Etapa 1 |
| `supermercados.tag` | Motor de Búsqueda Individual (TagUI); ahora también extrae imagen del producto para la validación por evidencia. | Etapa 1 + Etapa 2 |
| `catalogo.json` / `catalogo.js` | Catálogo oficial cerrado de 20 productos. | Etapa 1 |
| `mouse_helper.cs` / `.exe` | Control nativo de mouse/teclado Win32. | Etapa 1 |
| `validador.js` | Normalización, intención, marcas, categorías **y** referencias de imagen por producto/supermercado (`obtenerReferenciasImagen`, `registrarEvidenciaImagen`). | Etapa 1 + Etapa 2 |
| `generar_excel.js` | Reporte Excel de 5 hojas. | Etapa 1 |
| `server.js` | API REST + WebSocket + **detección de alertas de precio** (`detectarAlertas`) + endpoints de historial. | Etapa 1 + Etapa 2 |
| `public/app.js` | Dashboard principal (canasta, búsqueda individual, consola en vivo). | Etapa 1 |
| `historial.js` | Lectura/escritura de `historial_precios.jsonl` y `alertas_emitidas.jsonl`. | **Etapa 2** |
| `notificador.js` | Cliente mínimo de la API de Telegram (`enviar`, `enviarBienvenida`). | **Etapa 2** |
| `public/historial-dashboard.js` | Gráfico de tendencias, tabla de alertas y resumen de canasta en el dashboard. | **Etapa 2** |

---

## 9. Mejoras de la Etapa 2 en Detalle

### 9.1 Historial persistente (`historial.js`)
Se adoptó el formato **JSON Lines** (`historial_precios.jsonl`) porque permite anexar cada corrida al final del archivo (`fs.appendFileSync`) sin releer ni reescribir el archivo completo, evitando bloqueos y ahorrando memoria frente a reescribir un único JSON grande. Cada línea guarda `{ fecha, modo, producto, supermercado, precio }` para un ítem de una corrida.

### 9.2 Motor de alertas (`detectarAlertas` en `server.js`)
Al finalizar cada corrida (canasta o búsqueda individual), el servidor:
1. Lee el historial de ese producto + supermercado.
2. Calcula el porcentaje de baja entre el **último precio registrado** y el nuevo precio. Si supera `UMBRAL_BAJA_PCT` (10% por defecto, configurable por `.env`), genera una alerta tipo `BAJA`.
3. Si no hay baja porcentual pero el precio nuevo es menor al **mínimo histórico** (`Math.min` sobre todo el historial de ese ítem), genera una alerta tipo `MINIMO_HISTORICO`.
4. Guarda el resultado de la corrida y las alertas emitidas (`alertas_emitidas.jsonl` evita notificar dos veces la misma baja).

### 9.3 Bot de Telegram (`notificador.js`)
Cliente mínimo sobre la API oficial: `fetch()` nativo de Node.js con `AbortSignal.timeout(10000)`, sin SDK de terceros. Envía un mensaje de bienvenida al levantar el servidor y un mensaje por cada alerta detectada, con el formato:
> "¡Bajada de precio detectada! `<producto>` en `<supermercado>` bajó de `$X` a `$Y` (Ahorro: `Z%`)"

Las credenciales (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) se leen de `.env` (no versionado; ver [`.env.example`](.env.example)) mediante un parser propio en `server.js`, sin agregar la dependencia `dotenv`.

### 9.4 Panel de historial en el dashboard (`public/historial-dashboard.js`)
Agrega al dashboard existente: un selector de producto con gráfico de tendencia de precios por supermercado (Canvas nativo, sin librerías de charting), una tabla con las alertas emitidas y un resumen de la canasta actual. Consume los nuevos endpoints `GET /api/historial`, `GET /api/alertas` y `GET /api/resumen-canasta`.

### 9.5 Validación semántica reforzada con evidencia de imagen (`validador.js`, `supermercados.tag`)
Además del nombre textual del producto, el script TagUI ahora extrae la URL/alt/título de la imagen del resultado en cada tienda. `validador.js` guarda y consulta esas referencias por producto del catálogo + supermercado (`evidencia_imagenes.json`, no versionado — se regenera en cada corrida), de forma que si el nombre textual es ambiguo o está incompleto, la coincidencia de imagen con una referencia ya confirmada ayuda a confirmar o descartar el resultado, reduciendo falsos positivos y coincidencias inválidas.

---

## 10. Flujo Completo de Ejecución

```
1. INICIO (heredado) — Usuario inicia una búsqueda desde la Web UI o ejecutar.bat.
2. MOTOR RPA (heredado) — rpa_runner.js / supermercados.tag extraen precio + imagen de
   Carrefour, COTO y Día %, validando con validador.js (texto + evidencia de imagen).
3. POST-PROCESAMIENTO (Etapa 2):
   ├─ server.js compara los precios nuevos contra historial_precios.jsonl (detectarAlertas).
   ├─ historial.js anexa la corrida al historial y las alertas detectadas.
   ├─ notificador.js envía por Telegram cada alerta nueva (baja % o mínimo histórico).
   └─ Se regenera reporte_supermercados.xlsx (heredado, sin cambios).
4. DASHBOARD — El panel de historial (Etapa 2) muestra la tendencia de precios, las alertas
   emitidas y el resumen de canasta; el resto del dashboard (heredado) permanece igual.
```

---

## 11. Requisitos y Dependencias

Los mismos que la Etapa 1 (Windows 10/11, Google Chrome, Node.js 18+, TagUI opcional). **No se agregaron dependencias npm nuevas** — `historial.js` y `notificador.js` usan únicamente módulos nativos de Node.js (`fs`, `path`, `fetch`).

```json
{
  "dependencies": {
    "exceljs": "^3.4.0",
    "express": "^5.2.1",
    "puppeteer-core": "^25.10.0",
    "ws": "^8.21.3"
  }
}
```

---

## 12. Guía de Instalación y Configuración

### Paso 1: Clonar el repositorio y ubicarse en esta carpeta
```bash
git clone https://github.com/jaime-piperno/frcu-tagui.git
cd frcu-tagui/projects/2026/TagUI/team_9
```

### Paso 2: Instalar dependencias de Node.js
```bash
npm install
```

### Paso 3: Verificar `mouse_helper.exe` (heredado)
Ya está precompilado. Para recompilarlo desde `mouse_helper.cs`:
```cmd
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:exe /out:mouse_helper.exe mouse_helper.cs
```

### Paso 4 (Opcional — TagUI)
1. Descargar [TagUI_Windows.zip](https://github.com/aisingapore/tagui/releases/download/v6.110.0/TagUI_Windows.zip).
2. Descomprimir en `C:\tagui` y agregar `C:\tagui\src` al `PATH`.

### Paso 5 (Etapa 2 — variables de entorno)
Copiar `.env.example` a `.env` y completar con las credenciales reales del bot de Telegram (ver [sección 13](#13-configuración-del-bot-de-telegram)):
```bash
cp .env.example .env
```

---

## 13. Configuración del Bot de Telegram

1. Crear un bot con [@BotFather](https://t.me/BotFather) en Telegram y copiar el **token** que entrega.
2. Obtener el **chat ID** (propio o de un grupo) donde se recibirán las alertas — por ejemplo, enviando un mensaje al bot y consultando `https://api.telegram.org/bot<token>/getUpdates`.
3. Completar `.env` (nunca se versiona; ver `.gitignore`):
   ```env
   TELEGRAM_BOT_TOKEN=<token del bot>
   TELEGRAM_CHAT_ID=<chat id>
   UMBRAL_BAJA_PCT=10
   ```
4. `UMBRAL_BAJA_PCT` define el porcentaje mínimo de baja para disparar una alerta tipo `BAJA` (por defecto 10%); las bajas a mínimo histórico se detectan igual aunque no superen ese umbral.
5. Si no se completan `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`, `notificador.js` registra un aviso por consola y omite el envío — el resto del sistema sigue funcionando normalmente.

---

## 14. Cómo Ejecutar el Proyecto (Frontend Web y Consola)

### Opción A: Dashboard Web (recomendado)
1. Doble click en `interfaz.bat` (o `node server.js`).
2. Se abre `http://localhost:3000`. Las tarjetas de **Compra del Mes** y **Búsqueda Rápida** funcionan igual que en la Etapa 1.
3. El nuevo panel de **Historial** muestra la tendencia de precios y las alertas emitidas a medida que se acumulan corridas.

### Opción B: Consola Interactiva por Lotes
Igual que en la Etapa 1 (`ejecutar.bat`, menú de 7 opciones); las alertas y el historial se generan igual sin importar el modo de ejecución elegido.

---

## 15. Cómo Realizar una Prueba Completa

1. Completar `.env` con credenciales válidas de Telegram (ver sección 13).
2. Iniciar `interfaz.bat` y confirmar el mensaje de bienvenida en el chat de Telegram configurado (lo envía `notificador.enviarBienvenida()` al levantar el servidor).
3. Ejecutar una búsqueda (individual o canasta) dos veces para el mismo producto, bajando el precio esperado manualmente en `historial_precios.jsonl` de prueba o esperando una baja real en la tienda.
4. Verificar que:
   - El panel de **Historial** del dashboard muestra el nuevo punto en el gráfico de tendencia.
   - Si la baja supera el umbral configurado, llega un mensaje de Telegram con el formato "¡Bajada de precio detectada!...".
   - La misma alerta no se repite en una tercera corrida con el mismo precio (control de duplicados vía `alertas_emitidas.jsonl`).
   - El reporte Excel y el CSV de resultados siguen generándose igual que en la Etapa 1.

---

## 16. Persistencia de Datos

Además de `resultados.csv` (10 columnas, heredado de la Etapa 1), la Etapa 2 agrega:

| Archivo | Formato | Contenido |
| :--- | :--- | :--- |
| `historial_precios.jsonl` | JSON Lines | Una línea por ítem de cada corrida: `{ fecha, modo, producto, supermercado, precio }`. Nunca se sobrescribe. |
| `alertas_emitidas.jsonl` | JSON Lines | Una línea por alerta disparada (`BAJA` o `MINIMO_HISTORICO`), usada para no notificar dos veces la misma baja. |
| `evidencia_imagenes.json` | JSON | Referencias de imagen (`url`, `alt`, `title`) confirmadas por producto del catálogo + supermercado. Se regenera en cada corrida y no se versiona. |

---

## 17. Vinculación con la Materia

- **Retroalimentación (lazo cerrado):** el sistema original operaba a lazo abierto — medía y concluía. La Etapa 2 introduce retroalimentación: compara el estado presente con la referencia histórica y dispara una acción correctiva (la notificación) si detecta una oportunidad real de ahorro.
- **Perturbaciones exógenas:** la inflación y las promociones imprevistas en los sitios de los supermercados son perturbaciones del entorno que el sistema absorbe sin intervención manual, gracias a comparar siempre contra el historial real en vez de un valor fijo.
- **Calidad de los datos:** `validador.js` certifica marca, unidad y ahora también evidencia de imagen antes de autorizar que un precio entre al historial y pueda disparar una alerta.

---

## 18. Limitaciones Actuales

Heredadas de la Etapa 1 (sin cambios): dependencia de Windows para `mouse_helper.exe`, selectores sensibles a cambios de maquetación de VTEX/Angular, y el dropdown de ordenamiento de Día % puede requerir un retardo adicional de estabilización.

Propias de la Etapa 2:
- El envío de alertas depende de la disponibilidad de la API de Telegram y de una conexión a internet estable; si falla, `notificador.js` sólo deja un aviso por consola (no reintenta).
- El umbral de alerta (`UMBRAL_BAJA_PCT`) es único para todo el catálogo; no admite todavía un umbral distinto por producto.
- `evidencia_imagenes.json` se reconstruye en cada corrida a partir de lo observado; no incluye un paso de curación manual de referencias.

---

## 19. Funcionalidades Pendientes y Próximos Pasos

1. **Umbral de alerta por producto o categoría**, en vez de un único `UMBRAL_BAJA_PCT` global.
2. **Reintentos y cola de envío** en `notificador.js` ante caídas temporales de la API de Telegram.
3. **Panel histórico con rango de fechas configurable** y exportación del historial a Excel/CSV.
4. **Ampliación de cadenas minoristas** (heredado del roadmap de la Etapa 1: Jumbo, Disco, Changomas).

---

## 📄 Ámbito Académico
Trabajo Práctico Integrador — Etapa 2, desarrollado para la cátedra **Tecnologías para la Automatización (Año 2026)**, carrera de **Ingeniería en Sistemas de Información**, **Universidad Tecnológica Nacional – Facultad Regional Concepción del Uruguay (UTN FRCU)**, a partir del proyecto original del Grupo 1 (Etapa 1).

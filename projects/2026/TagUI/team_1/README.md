# 🛒 Comparador RPA Inteligente de Precios: Supermercados Argentinos
## UTN FRCU – Tecnologías para la Automatización (Año 2026)
### Trabajo Práctico Integrador – Etapa 1: Automatización Robótica de Procesos (RPA)

---

### 👥 Equipo de Trabajo (Grupo 1)
- **Lourdes Alvarez**
- **Florencia Carballo**
- **Alexander Ramos**
- **Juan Martín Cruz**
- **Santiago Manuel Allaud**

---

## 📑 Tabla de Contenidos
1. [Nombre del Proyecto y Objetivo Principal](#1-nombre-del-proyecto-y-objetivo-principal)
2. [Problema que Resuelve y Caso de Negocio](#2-problema-que-resuelve-y-caso-de-negocio)
3. [Funcionalidades Actuales](#3-funcionalidades-actuales)
4. [Arquitectura del Sistema](#4-arquitectura-del-sistema)
5. [Tecnologías Utilizadas](#5-tecnologías-utilizadas)
6. [Estructura Actual de Carpetas y Archivos](#6-estructura-actual-de-carpetas-y-archivos)
7. [Explicación de los Componentes Principales](#7-explicación-de-los-componentes-principales)
8. [Funcionamiento del Motor RPA (Automatización 100% Visible)](#8-funcionamiento-del-motor-rpa-automatización-100-visible)
9. [Funcionamiento de TagUI (Script Académico)](#9-funcionamiento-de-tagui-script-académico)
10. [Funcionamiento del Frontend y Dashboard Web](#10-funcionamiento-del-frontend-y-dashboard-web)
11. [Flujo Completo de Ejecución](#11-flujo-completo-de-ejecución)
12. [Requisitos y Dependencias](#12-requisitos-y-dependencias)
13. [Guía de Instalación y Configuración](#13-guía-de-instalación-y-configuración)
14. [Cómo Ejecutar el Proyecto (Frontend Web y Consola)](#14-cómo-ejecutar-el-proyecto-frontend-web-y-consola)
15. [Cómo Realizar una Prueba Completa](#15-cómo-realizar-una-prueba-completa)
16. [Reglas de Validación Semántica y Detección de Intención](#16-reglas-de-validación-semántica-y-detección-de-intención)
17. [Estructura del Reporte Excel (5 Hojas)](#17-estructura-del-reporte-excel-5-hojas)
18. [Persistencia de Datos (CSV de 10 Columnas)](#18-persistencia-de-datos-csv-de-10-columnas)
19. [Limitaciones Actuales](#19-limitaciones-actuales)
20. [Funcionalidades Pendientes y Próximos Pasos](#20-funcionalidades-pendientes-y-próximos-pasos)

---

## 1. Nombre del Proyecto y Objetivo Principal

**Nombre:** *Comparador RPA Inteligente de Precios y Optimizador de Canasta de Consumo Masivo.*

**Objetivo Principal:** Automatizar mediante RPA (*Robotic Process Automation*) la recolección en vivo, validación semántica estricta, comparación y optimización de precios en tiempo real sobre los principales supermercados con plataforma online de Argentina (**Carrefour**, **COTO** y **Día %**).

El sistema demuestra una automatización robótica visible en Google Chrome, ejecutando las acciones paso a paso sobre el navegador (navegación por barra de direcciones, tipeo letra por letra, scroll y selección de filtros de ordenamiento) de forma idéntica a la interacción de un usuario humano, persistiendo los resultados estructurados en CSV y generando un reporte analítico de 5 hojas en Microsoft Excel con el cálculo de la canasta óptima.

---

## 2. Problema que Resuelve y Caso de Negocio

En el mercado minorista argentino, la dispersión de precios para un mismo artículo o categoría entre distintas cadenas supera con frecuencia el 30% o 40%. Comparar manualmente decenas de artículos navegando múltiples portales web demanda un tiempo considerable y suele inducir a errores por diferencias de presentación, empaques o sustituciones no deseadas cuando una tienda no dispone de stock.

Este bot RPA actúa como un agente de software que:
1. **Navega de forma autónoma y visible** los catálogos públicos de las tres tiendas online en Google Chrome.
2. **Interactúa con los controles reales del navegador y de la página:** barra de direcciones (Omnibox), buscadores con autocompletado, scrolls progresivos y dropdowns de ordenamiento por menor precio.
3. **Extrae en tiempo real** el nombre exacto del artículo, precio vigente, enlace directo a la publicación y estado de disponibilidad en el DOM.
4. **Evalúa semánticamente** la coincidencia a través de un motor de validación (`validador.js`) que distingue entre búsquedas específicas (marca, variedad, presentación) y búsquedas genéricas (categoría abierta), evitando falsos positivos (por ejemplo, rechazar sustituciones absurdas como frutas o artículos de limpieza ante la búsqueda de una bebida).
5. **Calcula la canasta económica óptima:** Determina el supermercado ganador por costo total acumulado y calcula el ahorro máximo posible comprando cada artículo en su tienda más barata.
6. **Consolida la información** en persistencia local (`resultados.csv`) y genera un reporte analítico visual de 5 hojas en Excel (`reporte_supermercados.xlsx`).

---

## 3. Funcionalidades Actuales

- **Automatización 100% Visible Paso a Paso:** El robot abre Google Chrome maximizado y ejecuta visiblemente cada acción: mueve el cursor hacia la barra de direcciones, tipea la URL letra por letra, presiona Enter, ubica el buscador, tipea el producto, ejecuta la búsqueda, hace scroll y selecciona el filtro de menor precio ("Precios más bajo" / "Menor precio").
- **Cursor Virtual Autónomo e Indicador Visual:** Inyección de un cursor gráfico con trayectorias de curvas Bézier cúbicas, animaciones de pulso en clicks y badge identificador "BOT RPA".
- **Controlador Nativo de Mouse y Omnibox (`mouse_helper.exe`):** Binario Win32 desarrollado en C# que interactúa con la API de Windows (`user32.dll`) para mover el cursor físico y activar la barra de direcciones mediante atajos del sistema (`Alt+D` / `Ctrl+L`).
- **Dashboard Web Interactivo (`http://localhost:3000`):** Interfaz gráfica desarrollada con diseño glassmorphism moderno que permite lanzar búsquedas individuales, ejecutar la compra del mes, editar la canasta en una tabla interactiva, configurar la velocidad del robot y monitorear la ejecución en tiempo real.
- **Transmisión de Estado en Tiempo Real (WebSocket):** Conexión bidireccional (`/ws/rpa-stream`) que transmite logs, barra de progreso porcentual y estado paso a paso de cada supermercado (Carrefour ➔ COTO ➔ Día %).
- **Mecanismos de Aborto Inmediato (Kill-Switch):**
  - Si el usuario cierra la ventana de Chrome o la pestaña de navegación, el proceso se interrumpe al instante.
  - Si el usuario cierra el frontend web, el servidor detecta la desconexión y cancela el RPA.
  - Endpoint dedicado `POST /api/abort` para detención inmediata.
- **Motor de Validación Semántica Estricta (`validador.js`):**
  - Detección de intención (`ESPECIFICA` vs `GENERICA`).
  - Diccionario de marcas argentinas y extracción de cantidades/unidades (`1kg`, `500g`, `2.25L`).
  - Detección y bloqueo de términos incompatibles por categoría.
  - Clasificación en 4 estados: `VALIDADA`, `SIN STOCK`, `NO ENCONTRADO`, `COINCIDENCIA NO VÁLIDA`.
- **Reporte Analítico en Excel de 5 Hojas (`reporte_supermercados.xlsx`):** Generación automatizada con `exceljs` que incluye KPIs ejecutivos, matriz comparativa de la canasta, ranking global de menor a mayor, historial de consultas individuales y panel de control de stock/incidencias.
- **Soporte de Ejecución Dual:**
  - Modo Web UI vía `interfaz.bat`.
  - Modo Consola interactiva vía `ejecutar.bat` con menú interactivo de 7 opciones.
  - Compatibilidad con el script TagUI (`supermercados.tag`) para cumplimiento de los requisitos de la cátedra.

---

## 4. Arquitectura del Sistema

El sistema implementa una arquitectura modular desacoplada en tres capas:

```
┌───────────────────────────────────────────────────────────────────────────┐
│                              CAPA DE USUARIO                              │
├─────────────────────────────────────┬─────────────────────────────────────┤
│         Dashboard Web (UI)          │        Consola CLI (Windows)        │
│  - http://localhost:3000 (app.js)   │  - ejecutar.bat (Menú 7 opciones)   │
│  - WebSocket /ws/rpa-stream         │  - Soporta argumentos directos      │
└──────────────────┬──────────────────┴──────────────────┬──────────────────┘
                   │                                     │
                   ▼                                     ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                      CAPA DE SERVICIOS Y ORQUESTACIÓN                     │
├───────────────────────────────────────────────────────────────────────────┤
│  server.js (Node.js + Express 5 + WebSocket Server 'ws')                  │
│  - API REST: /api/compra-mes, /api/buscar-individual, /api/abort, etc.    │
│  - Control de concurrencia (1 ejecución activa a la vez)                  │
│  - Transmisión de logs, progreso y estados a los clientes conectados      │
└──────────────────┬─────────────────────────────────────┬──────────────────┘
                   │                                     │
                   ▼                                     ▼
┌─────────────────────────────────────┐   ┌─────────────────────────────────┐
│      MOTOR CANASTA / COMPRA MES     │   │    MOTOR BÚSQUEDA INDIVIDUAL    │
│         (rpa_runner.js)             │   │      (supermercados.tag)        │
├─────────────────────────────────────┤   ├─────────────────────────────────┤
│ - Motor Exclusivo: Compra del Mes   │   │ - Motor Exclusivo: Búsq. Indiv. │
│ - Puppeteer-Core + mouse_helper.exe │   │ - Ejecutado vía TagUI CLI       │
│ - Tipeo/click/scroll visibles reales│   │ - Productos 100% de Catálogo    │
│ - Módulos: Carrefour, COTO, Día %   │   │ - Carrefour, COTO y Día %       │
└──────────────────┬──────────────────┘   └────────────────┬────────────────┘
                   │                                       │
                   └──────────────────┬────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                     CAPA DE VALIDACIÓN Y PERSISTENCIA                     │
├───────────────────────────────────────────────────────────────────────────┤
│  validador.js:                                                            │
│    - Normalización de texto y remoción de diacríticos                     │
│    - Inferencia de intención (específica de marca vs genérica)            │
│    - Filtro de términos incompatibles y validación de categorías          │
│                                                                           │
│  resultados.csv:                                                          │
│    - Persistencia estructurada en 10 columnas (modo, producto, precio,    │
│      supermercado, url, fecha, stock_status, cantidad, unidad)            │
│                                                                           │
│  generar_excel.js:                                                        │
│    - Motor ExcelJS: genera reporte_supermercados.xlsx (5 hojas estilizadas)│
│    - Cálculo de canasta ganadora, compra óptima combinada y ahorro        │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Tecnologías Utilizadas

- **Entorno de Ejecución:** Node.js (v18 o superior).
- **Automatización de Navegador:**
  - `puppeteer-core` (v25.10.0): Control de Google Chrome sobre el protocolo DevTools (CDP), ejecución con ventana maximizada, eventos de teclado y mouse reales.
  - TagUI v6.110.0 (AI Singapore): Framework de RPA por comandos utilizado para cumplir las pautas académicas.
- **Controlador Nativo de Sistema Operativo:**
  - C# / .NET Framework 4.0: Código fuente en `mouse_helper.cs`, compilado en `mouse_helper.exe`. Utiliza `user32.dll` (`SendInput`, `GetCursorPos`, `SetCursorPos`, `keybd_event`) para interactuar con la barra de direcciones de Chrome y emular movimientos de mouse con curvas de Bézier cúbicas y DPI Awareness.
- **Backend y API:**
  - `express` (v5.2.1): Servidor web HTTP para servir el frontend y atender los endpoints REST.
  - `ws` (v8.21.3): Servidor WebSocket para streaming en tiempo real de logs y telemetría.
- **Frontend:**
  - HTML5 semántico, CSS3 moderno (Glassmorphism, CSS Grid, Flexbox, variables CSS) y JavaScript Vanilla (ES6+).
  - Tipografía Inter (Google Fonts) e iconos FontAwesome 6.
- **Generación de Reportes:**
  - `exceljs` (v3.4.0): Creación programática de hojas de cálculo `.xlsx`, estilos corporativos, formatos numéricos de moneda, fórmulas y formato condicional.
- **Almacenamiento y Formatos de Datos:**
  - CSV (RFC 4180 / UTF-8) y Microsoft Excel (.xlsx).

---

## 6. Estructura Actual de Carpetas y Archivos

```
Rpa programa/
├── docs/
│   └── guia_visual.html          # Guía visual explicativa de reglas y funcionamiento.
├── public/                       # Frontend web servido por Express
│   ├── app.js                    # Lógica del cliente web (WebSocket, REST, UI).
│   ├── index.html                # Dashboard principal con panel de control y monitor.
│   └── styles.css                # Estilos visuales (diseño glassmorphism moderno).
├── tests/                        # Pruebas y scripts de verificación
│   ├── capture_frontend_ui.js    # Captura de interfaz de usuario.
│   ├── test_error_concurrency.js # Prueba de control de concurrencia y errores.
│   ├── verify_compra_mes.js      # Verificación del flujo de compra del mes.
│   └── verify_live_search_manaos.js # Verificación de validación semántica estricta.
├── .gitignore                    # Exclusión de node_modules, temporales y reportes locales.
├── ejecutar.bat                  # Lanzador por lotes interactivo (menú CLI de 7 opciones).
├── generar_excel.js              # Generador del reporte Excel de 5 hojas con ExcelJS.
├── input.csv                     # Canasta básica mensual predefinida (editable).
├── interfaz.bat                  # Lanzador directo del servidor y Dashboard Web.
├── mouse_helper.cs               # Código fuente C# del controlador nativo Win32.
├── mouse_helper.exe              # Ejecutable compilado del helper nativo de mouse y Omnibox.
├── package.json                  # Definición de dependencias npm del proyecto.
├── package-lock.json             # Árbol de versiones bloqueadas de npm.
├── README.md                     # Documentación general y manual de usuario del proyecto.
├── resultados.csv                # Persistencia de extracciones (10 columnas).
├── rpa_runner.js                 # Motor de automatización RPA 100% visible con Chrome.
├── server.js                     # Servidor Express + WebSocket + API REST.
├── supermercados.tag             # Script TagUI para ejecución académica alternativa.
└── validador.js                  # Motor de validación semántica y reporte por consola.
```

---

## 7. Explicación de los Componentes Principales

| Archivo | Responsabilidad Principal |
| :--- | :--- |
| **`rpa_runner.js`** | Motor EXCLUSIVO para la Canasta / Compra del Mes. Puppeteer sólo lee el DOM para ubicar/extractar; navegación, foco, clicks, teclas y rueda pasan por `mouse_helper.exe`. Coordina Carrefour, COTO y Día % y guarda los resultados en `resultados.csv`. |
| **`supermercados.tag`** | Motor EXCLUSIVO para la Búsqueda Rápida Individual. Ejecutado vía `tagui supermercados.tag temp_input.csv` tanto desde el Dashboard Web como desde la consola Windows `ejecutar.bat`. Opera estrictamente con los 20 productos oficiales del catálogo cerrado. |
| **`catalogo.json` / `catalogo.js`** | Catálogo oficial cerrado de exactamente 20 productos verificados. Provee validación dimensional estricta, consultas por diccionario y menú interactivo. |
| **`mouse_helper.cs` / `.exe`** | Herramienta Win32 que controla el mouse y teclado físicos: Omnibox (`Alt+D`, URL y Enter), coordenadas del viewport, clicks, tipeo y rueda. Convierte las coordenadas CSS leídas por Puppeteer al escritorio real de Chrome. |
| **`server.js`** | Levanta el servidor HTTP en el puerto 3000, gestiona la conexión WebSocket `/ws/rpa-stream`, expone los endpoints para lanzar búsquedas individuales (TagUI) y compra del mes (Puppeteer), editar canasta, abortar procesos y regenerar reportes. |
| **`public/app.js`** | Controla los eventos del dashboard web: gestiona la conexión WebSocket, actualiza la consola virtual en vivo, sincroniza los indicadores de paso de los 3 supermercados y restringe la búsqueda individual a los productos oficiales del catálogo cerrado. |
| **`validador.js`** | Normaliza textos, detecta la intención del usuario, evalúa la pertinencia del producto encontrado frente a lo solicitado (marcas, términos incompatibles y categorías) y genera `temp_input.csv` validando contra el catálogo cerrado. |
| **`generar_excel.js`** | Lee `resultados.csv`, calcula la canasta más económica y el óptimo combinado, y construye `reporte_supermercados.xlsx` con 5 hojas formateadas profesionalmente. |
| **`ejecutar.bat`** | Script de inicio para consola Windows con validación de dependencias (Node.js, ExcelJS, TagUI) y menú interactivo de 8 opciones, incluyendo visor de catálogo y búsqueda individual TagUI por número [1-20]. |
| **`interfaz.bat`** | Script de inicio rápido que libera el puerto 3000 si estuviera ocupado, inicia `server.js` en segundo plano y abre automáticamente el navegador en `http://localhost:3000`. |

---

## 8. Funcionamiento del Motor RPA (Automatización 100% Visible)

A diferencia de los scripts tradicionales que utilizan llamadas HTTP internas o asignaciones sintéticas en el DOM (`element.value = ...`), este motor implementa una **interacción visible de extremo a extremo**:

1. **Detección de Chrome:** La función `getChromePath()` localiza el ejecutable de Google Chrome en las rutas estándar de Windows (`Program Files`, `Program Files (x86)`, `LocalAppData`).
2. **Lanzamiento Visible:** Puppeteer inicia Chrome con `headless: false`, `--start-maximized` y desactivando flags de automatización.
3. **Cursor físico en Pantalla:** No se usa un cursor virtual para aparentar acciones. `mouse_helper.exe` mueve el puntero de Windows por curvas Bézier y ejecuta el click físico sobre Chrome.
4. **Navegación Visible por Barra de Direcciones (`visibleNavigate`):**
   - El cursor se mueve hacia la parte superior de la ventana.
   - `mouse_helper.exe` envía los eventos nativos de Windows para enfocar la barra de direcciones de Chrome (`Alt+D`).
   - Escribe la URL carácter por carácter con un retardo humano configurable (por defecto 50 ms).
   - Presiona Enter y espera a que el navegador complete la carga de la página.
5. **Tipeo Progresivo Real (`visibleType`):**
   - El cursor se mueve hasta el campo de búsqueda del supermercado y hace click.
   - Envía `Ctrl+A` seguido de `Backspace` para limpiar búsquedas previas.
   - Escribe la consulta con `SendKeys` nativo, carácter por carácter, sobre el campo que recibió el click físico.
6. **Scroll Progresivo (`visibleScroll`):** Usa eventos nativos de rueda en pasos sucesivos; no usa `scrollIntoView()` ni `window.scrollBy()`.
7. **Ordenamiento de Menor a Mayor:**
   - **Carrefour:** Localiza el botón `orderByButton`, lo despliega y hace click en la opción "Precios más bajo".
   - **COTO:** Localiza el elemento `<select class="form-select">` y selecciona la opción `price|ascending`.
   - **Día %:** Localiza el botón de ordenamiento y selecciona la opción correspondiente a menor precio.
8. **Extracción y Validación:** Tras estabilizar el DOM pos-ordenamiento, evalúa los primeros artículos contra las reglas de `validador.js` y selecciona el producto con stock y precio válido más representativo.

---

## 9. Funcionamiento de TagUI (Motor Exclusivo de Búsqueda Individual)

El archivo `supermercados.tag` constituye el motor EXCLUSIVO para la **Búsqueda Rápida Individual**, tanto desde la interfaz web como desde el script de consola `ejecutar.bat`:

- **Restricción de Catálogo:** Sólo procesa productos validados que pertenezcan a los 20 ítems del catálogo cerrado (`catalogo.json`).
- **Estructura de Ejecución:** Invocado directamente mediante:
  ```cmd
  tagui supermercados.tag temp_input.csv
  ```
- **Procesamiento de Parámetros:** TagUI lee variables nativas (`producto`, `cantidad`, `unidad`, `termino`) generadas de manera segura por `validador.crearTempInput`.
- **Interacción por Supermercado:**
  - Visita Carrefour, gestiona el banner de cookies (`if present('Aceptar todo') click`), escribe en el buscador `input.vtex-styleguide-9-x-input` con coma decimal (ej. `Coca Cola 2,25 L`) y extrae datos mediante un bloque JavaScript `dom begin ... dom finish` con filtros de incompatibilidad de marcas.
  - Visita COTO, escribe en `input#cio-autocomplete-0-input` y extrae los resultados del componente `<constructor-result-item>`.
  - Visita Día %, adapta términos de catálogo (ej. `Luchetti`) y extrae los datos del catálogo online.
- **Persistencia:** Al finalizar cada tienda, escribe la fila estructurada en `resultados.csv` con `modo = individual` mediante la función interna `csv_row(...)`.

---

## 10. Funcionamiento del Frontend y Dashboard Web

El frontend web (`public/index.html`, `styles.css`, `app.js`) proporciona una experiencia visual de control:

- **Tarjeta "Compra del Mes":** Botón de inicio rápido del procesamiento masivo con motor Puppeteer y botón "Editar Lista" que abre un modal con una tabla editable interactiva donde agregar, modificar o quitar productos, cantidades y unidades.
- **Tarjeta "Búsqueda Rápida (Catálogo Cerrado)":** Menú desplegable con los 20 productos verificados del catálogo oficial con ficha técnica en tiempo real (marca, variante, presentación) y botón "Comparar en 3 Súper" ejecutado con TagUI.
- **Controles de Demostración:**
  - Switch para alternar el modo demostración visual.
  - Deslizador de velocidad de tipeo (de 0.02s a 0.12s por letra).
  - Deslizador de velocidad de movimiento de mouse (de 0.2s a 1.2s).
- **Monitor de Pasos de Supermercados:** Tres tarjetas de estado sincronizadas con badges de progreso en tiempo real:
  - `1. Carrefour` ➔ `2. COTO Digital` ➔ `3. Día %`
  - Estados: *En espera*, *En curso...* y *✓ Completado*.
- **Consola Virtual en Vivo:** Panel con scroll automático que refleja todos los mensajes emitidos por el motor RPA mediante el canal WebSocket.
- **Modal de Limpieza:** Opciones para purgar los datos de la compra del mes, el historial individual o la totalidad de los registros sin tocar `input.csv`.

---

## 11. Flujo Completo de Ejecución

```
1. INICIO
   ├─ Usuario presiona "Iniciar Proceso" o "Buscar Producto" en la Web UI (o vía ejecutar.bat).
   └─ server.js recibe la solicitud y verifica el bloqueo de concurrencia.

2. PREPARACIÓN
   ├─ Se cierran instancias bloqueantes de Excel (taskkill EXCEL.EXE para evitar EBUSY).
   ├─ Se limpian registros previos del modo correspondiente en resultados.csv.
   └─ Se inicializa la conexión WebSocket y se emite el estado 'connecting'.

3. MOTOR RPA (rpa_runner.js)
   ├─ Abre Google Chrome maximizado en la pantalla del usuario.
    ├─ Prepara el controlador Win32 mouse_helper.exe; no inyecta un cursor virtual.
   │
   ├─ SUPERMERCADO 1: CARREFOUR ARGENTINA
   │  ├─ Navega vía Omnibox (tipeo visible de URL).
   │  ├─ Cierra banners de cookies.
   │  ├─ Mueve cursor al buscador y escribe el producto letra por letra.
   │  ├─ Presiona Enter y espera la carga de resultados.
   │  ├─ Realiza scroll progresivo.
   │  ├─ Despliega el menú de ordenamiento y selecciona "Precios más bajo".
   │  ├─ Extrae el producto candidato y valida con validador.js.
   │  └─ Emite telemetría: [SUPERMERCADO 1] Finalizado.
   │
   ├─ SUPERMERCADO 2: COTO DIGITAL
   │  ├─ Navega vía Omnibox a https://www.coto.com.ar.
   │  ├─ Mueve cursor al buscador de COTO y tipea letra por letra.
   │  ├─ Presiona botón de búsqueda / Enter.
   │  ├─ Aplica scroll progresivo.
   │  ├─ Aplica ordenamiento por menor precio.
   │  ├─ Extrae el producto candidato y valida con validador.js.
   │  └─ Emite telemetría: [SUPERMERCADO 2] Finalizado.
   │
   ├─ SUPERMERCADO 3: DÍA %
   │  ├─ Navega vía Omnibox a https://diaonline.supermercadosdia.com.ar.
   │  ├─ Mueve cursor al buscador de Día % y tipea letra por letra.
   │  ├─ Presiona Enter y espera resultados.
   │  ├─ Aplica scroll progresivo y ordenamiento.
   │  ├─ Extrae el producto candidato y valida con validador.js.
   │  └─ Emite telemetría: [SUPERMERCADO 3] Finalizado.
   │
   └─ Cierra la sesión de Chrome de manera ordenada.

4. POST-PROCESAMIENTO Y SALIDA
   ├─ Los registros se persisten en resultados.csv (10 columnas).
   ├─ En búsquedas individuales, se imprime el reporte semántico por consola.
   ├─ Se ejecuta generar_excel.js y se actualiza reporte_supermercados.xlsx.
   ├─ Se abre automáticamente el archivo Excel en Microsoft Excel.
   └─ El frontend web emite 'finished' y restablece el estado del sistema.
```

---

## 12. Requisitos y Dependencias

### Requisitos del Sistema Operativo
- **Sistema Operativo:** Microsoft Windows 10 o Windows 11 (64-bit).
- **Navegador Web:** Google Chrome instalado en su ruta predeterminada de sistema.
- **Node.js:** Versión 18.x o superior (verificar con `node -v`).
- **TagUI (opcional/académico):** TagUI v6.110.0 configurado en la variable `PATH` si se desea ejecutar el script `.tag`.

### Dependencias declaradas en `package.json`
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

## 13. Guía de Instalación y Configuración

### Paso 1: Clonar o descargar el repositorio
```bash
git clone https://github.com/SantiagoAllaud/Rpa-grupo-1.git
cd "Rpa-grupo-1/Rpa programa"
```

### Paso 2: Instalar dependencias de Node.js
Ejecutar en la carpeta raíz del proyecto:
```bash
npm install
```
Esto descargará e instalará `exceljs`, `express`, `puppeteer-core` y `ws` dentro del directorio `node_modules`.

### Paso 3: Verificar el ejecutable auxiliar `mouse_helper.exe`
El archivo `mouse_helper.exe` ya se encuentra precompilado en la raíz. Si por alguna razón de entorno se desea recompilar desde su código fuente `mouse_helper.cs`, se puede ejecutar desde una consola con el compilador de .NET Framework de Windows:
```cmd
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:exe /out:mouse_helper.exe mouse_helper.cs
```

### Paso 4 (Opcional - Sólo para TagUI):
Si se va a utilizar el motor TagUI mediante la opción de consola o ejecución manual:
1. Descargar [TagUI_Windows.zip](https://github.com/aisingapore/tagui/releases/download/v6.110.0/TagUI_Windows.zip).
2. Descomprimir en `C:\tagui`.
3. Agregar `C:\tagui\src` a la variable de entorno `Path` de Windows.

---

## 14. Cómo Ejecutar el Proyecto (Frontend Web y Consola)

### Opción A: Dashboard Web (Método Recomendado)
1. Hacer doble click sobre el archivo **`interfaz.bat`** (o ejecutar en terminal: `node server.js`).
2. Se iniciará el servidor en `http://localhost:3000` y se abrirá automáticamente en tu navegador por defecto.
3. Para buscar un producto puntual, ingresarlo en la tarjeta **Búsqueda Rápida** y presionar "Buscar Producto".
4. Para procesar la canasta completa, presionar "Iniciar Proceso" en la tarjeta **Compra del Mes**.

### Opción B: Consola Interactiva por Lotes
1. Hacer doble click sobre el archivo **`ejecutar.bat`**.
2. Se desplegará el menú interactivo con las siguientes opciones:
   - `[1] Procesar compra del mes (desde input.csv)`
   - `[2] Buscar producto individual (consulta interactiva)`
   - `[3] Abrir reporte Excel (reporte_supermercados.xlsx)`
   - `[4] Editar lista de compra del mes (input.csv)`
   - `[5] Limpiar resultados / historial`
   - `[6] Diagnóstico del sistema y pruebas unitarias`
   - `[7] Salir`
3. También permite pasar el producto directamente como argumento por línea de comandos:
   ```cmd
   ejecutar.bat "leche la serenisima"
   ```

---

## 15. Cómo Realizar una Prueba Completa

Para comprobar que todos los componentes funcionan de forma armónica:

1. Iniciar la interfaz web ejecutando `interfaz.bat`.
2. Verificar que en la esquina superior de la consola virtual figure el indicador **Listo**.
3. En la tarjeta de **Búsqueda Rápida**, seleccionar un producto del desplegable del catálogo (por ejemplo, `Arroz Gallo Largo Fino 1 kg`) y presionar **Comparar en 3 Súper**.
4. Observar en el escritorio:
   - Se abre Google Chrome mediante TagUI.
   - El robot visita Carrefour, escribe el producto del catálogo, extrae el artículo y su precio.
   - Pasa a COTO Digital, realiza la búsqueda y extrae.
   - Pasa a Día %, ejecuta la búsqueda y extrae.
   - Chrome se cierra de forma limpia.
5. Observar en el navegador:
   - Los indicadores de los 3 supermercados pasan a verde con el tilde de completado.
   - La barra de progreso llega al 100%.
   - Los logs de TagUI se transmiten en vivo a la consola web.
6. Comprobar que automáticamente se actualiza y abre Microsoft Excel exhibiendo el archivo `reporte_supermercados.xlsx` con los datos de la consulta en las 5 hojas.

---

## 16. Reglas de Validación Semántica y Detección de Intención

El módulo `validador.js` actúa como filtro de calidad sobre las extracciones:

### Intención Específica (`ESPECIFICA`)
Se activa cuando el término contiene una marca conocida (*La Serenísima*, *Molinos Ala*, *Coca Cola*, *Playadito*, *Lucchetti*, etc.) o especificaciones cuantitativas estrictas:
- **Exigencia de Marca:** La marca requerida debe estar presente en el título devuelto por la tienda. Si no coincide, el producto es rechazado con el estado `COINCIDENCIA NO VÁLIDA`.
- **Filtro de Incompatibilidad:** Se definen listas de exclusión categórica cruzada (por ejemplo, ante la búsqueda de gaseosa o arroz, se descartan artículos de limpieza, tocador o frutas).

### Intención Genérica (`GENERICA`)
Se activa ante búsquedas abiertas de consumo general (ej: *arroz*, *leche*, *fideos*):
- Valida que el artículo pertenezca a la categoría solicitada.
- Permite la competencia entre diversas marcas para descubrir la opción más accesible de góndola.

---

## 17. Estructura del Reporte Excel (5 Hojas)

El archivo generado `reporte_supermercados.xlsx` está estructurado en 5 pestañas:

1. **🏆 Conclusiones:** Tarjetas KPI con el supermercado ganador de la canasta, costo de la canasta más económica, costo de la compra combinada óptima y ahorro potencial absoluto. Incluye la tabla de ganadores por producto con hipervínculos directos a la tienda.
2. **🛒 Canasta Mensual:** Matriz comparativa que cruza los productos cotizados contra cada cadena. Las celdas de menor precio se destacan en verde pastel y en el pie se calculan los totales acumulados.
3. **📊 Ranking Menor a Mayor:** Lista completa de todos los productos extraídos ordenados estrictamente por precio unitario ascendente con medallas 🥇, 🥈 y 🥉.
4. **🔎 Consultas Individuales:** Historial cronológico de las búsquedas rápidas realizadas por los usuarios.
5. **⚠️ Disponibilidad y Stock:** Auditoría de incidencias que lista productos con `SIN STOCK`, `NO ENCONTRADO` y aquellos rechazados por validación semántica (`COINCIDENCIA NO VÁLIDA`) detallando el motivo exacto del descarte.

---

## 18. Persistencia de Datos (CSV de 10 Columnas)

El archivo `resultados.csv` almacena el histórico estructurado con cabecera fija y formato UTF-8:

```csv
modo,producto_solicitado,nombre_encontrado,precio,supermercado,url,fecha,stock_status,cantidad,unidad
```

- **`modo`:** `compra_mes` o `individual`.
- **`producto_solicitado`:** Término original ingresado.
- **`nombre_encontrado`:** Título exacto extraído del DOM.
- **`precio`:** Precio extraído en formato texto (ej: `$ 1.940,00`).
- **`supermercado`:** Cadena correspondiente (`Carrefour`, `COTO` o `Día %`).
- **`url`:** Enlace directo a la ficha del producto en la tienda.
- **`fecha`:** Fecha de la captura en formato `AAAA-MM-DD`.
- **`stock_status`:** `DISPONIBLE`, `SIN STOCK`, `NO ENCONTRADO` o `COINCIDENCIA NO VÁLIDA`.
- **`cantidad`:** Cantidad solicitada (entero, por defecto 1).
- **`unidad`:** Unidad de medida asociada (ej: `1kg`, `500g`, `2L`).

---

## 19. Limitaciones Actuales

- **Plataforma Exclusiva Windows:** El controlador nativo `mouse_helper.exe` depende de las APIs Win32 de Windows (`user32.dll`) para el movimiento físico y navegación de la barra de direcciones. En entornos Linux o macOS, la navegación debe recaer exclusivamente en comandos de Puppeteer o TagUI.
- **Variaciones de Maquetación Dinámica:** Las plataformas de comercio electrónico (especialmente VTEX IO en Carrefour y Día %, y Angular en COTO) actualizan con frecuencia clases CSS ofuscadas y estructuras de modales (banners de código postal, suscripciones y promociones bancarias), lo que exige mantener selectores semánticos resilientes.
- **Dropdown de Ordenamiento en Día %:** En determinadas resoluciones o estados del DOM de Día %, el menú de ordenamiento por precio puede requerir un retardo adicional de estabilización tras el click para garantizar que la grilla de productos se reordene antes de la lectura.

---

## 20. Funcionalidades Pendientes y Próximos Pasos

1. **Ajuste fino del selector de orden en Día %:** Refinar la selección del elemento exacto del dropdown "Precios más bajo" para evitar coincidencias con contenedores padre.
2. **Soporte Headless Opcional con Grabación de Video:** Permitir alternar entre el modo demostración 100% visible y un modo en segundo plano con exportación de video de la sesión para auditoría automatizada.
3. **Ampliación de Cadenas Minoristas:** Integración modular de nuevas cadenas de supermercados (ej: Jumbo, Disco, Changomas) siguiendo el mismo patrón de arquitectura desacoplada.

---

## 📄 Ámbito Académico
Trabajo Práctico desarrollado para la cátedra **Tecnologías para la Automatización (Año 2026)**, carrera de **Ingeniería en Sistemas de Información**, **Universidad Tecnológica Nacional – Facultad Regional Concepción del Uruguay (UTN FRCU)**.

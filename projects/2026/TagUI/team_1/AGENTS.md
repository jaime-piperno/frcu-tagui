# 🤖 AGENTS.md — Instrucciones Técnicas para Agentes de Programación

# Reglas de Ejecución Local
- Este agente solo debe operar dentro del directorio raíz de 'Rpa programa'.
- Tienes autorización para compilar el helper C#, correr scripts .bat y ejecutar pruebas con Puppeteer y TagUI sin solicitar confirmaciones intermedias de plan.
- No intentes acceder a rutas fuera de este workspace.

> **Audiencia:** Este documento está dirigido exclusivamente a agentes de IA y desarrolladores de software que deban inspeccionar, mantener, refactorizar o extender este repositorio. Describe la arquitectura interna real, contratos de interfaz, dependencias críticas, reglas de negocio inmutables y el estado técnico actual.

---

## 1. Objetivo Técnico del Proyecto

Desarrollar y mantener un sistema de **Automatización Robótica de Procesos (RPA)** en entorno **Windows 10/11** capaz de recolectar, validar semánticamente, comparar y optimizar precios de productos de consumo masivo en tres cadenas de supermercados argentinas (**Carrefour**, **COTO** y **Día %**).

### Principio Rector de Diseño:
> **Toda interacción con el navegador DEBE ser 100% visible y paso a paso.**
> Está estrictamente prohibido recurrir a atajos sintéticos que omitan la acción visual del robot (como `page.goto('/producto/...')`, inyecciones directas `input.value = ...` o llamadas fetch internas al catálogo que no reflejen la interacción real de un usuario en pantalla).

---

## 2. Arquitectura Actual

El repositorio implementa una arquitectura desacoplada en cuatro capas de software:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. CAPA DE INTERFAZ Y PRESENTACIÓN                                    │
│    - Web Dashboard: Express 5 + Vanilla JS (public/index.html, app.js) │
│    - Consola CLI Windows: ejecutar.bat (Menú de 7 opciones)            │
├───────────────────────────────────┬────────────────────────────────────┤
│ 2. CAPA DE COMUNICACIÓN Y API     │ 3. CAPA DE MOTORES RPA             │
│    - server.js: HTTP REST + WS    │    A) Motor Canasta / Compra Mes:  │
│    - WebSocket: /ws/rpa-stream    │       rpa_runner.js (Puppeteer)    │
│    - Lock de concurrencia único   │       mouse_helper.exe (Win32 API) │
│    - Kill-switch por desconexión  │    B) Motor Búsqueda Individual:   │
│                                   │       supermercados.tag (TagUI)    │
├───────────────────────────────────┴────────────────────────────────────┤
│ 4. CAPA DE VALIDACIÓN, PERSISTENCIA Y REPORTES                         │
│    - validador.js: Inferencia semántica, detección de intención (marca)│
│    - resultados.csv: Almacén estructurado en 10 columnas (RFC-4180)    │
│    - generar_excel.js: Motor ExcelJS (5 hojas analíticas con estilos)  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Estructura Importante del Repositorio

```
Rpa programa/
├── docs/                         # Documentación complementaria
│   └── guia_visual.html          # Guía visual HTML offline de reglas y flujos
├── public/                       # Frontend web servido por server.js
│   ├── app.js                    # Cliente Web: WebSocket, REST y DOM
│   ├── index.html                # UI principal: Glassmorphism, controles y monitor
│   └── styles.css                # Estilos CSS modernos (variables, dark theme)
├── tests/                        # Banco de pruebas de integración y verificación
│   ├── capture_frontend_ui.js    # Captura de pantalla de la interfaz web
│   ├── test_error_concurrency.js # Test de concurrencia y bloqueo de ejecuciones
│   ├── verify_compra_mes.js      # Verificación del flujo de canasta mensual
│   └── verify_live_search_manaos.js # Verificación de validación semántica estricta
├── .gitignore                    # Exclusiones de Git (node_modules, xlsx temporales)
├── AGENTS.md                     # [ESTE ARCHIVO] Instrucciones y directivas para agentes
├── ejecutar.bat                  # Lanzador CLI por lotes para Windows (UTF-8 / CRLF)
├── generar_excel.js              # Generador de reporte_supermercados.xlsx (5 hojas)
├── input.csv                     # Canasta mensual predefinida (producto,cantidad,unidad)
├── interfaz.bat                  # Lanzador directo del servidor web y apertura de UI
├── mouse_helper.cs               # Código fuente C# del helper nativo Win32
├── mouse_helper.exe              # Binario compilado para control de cursor y Omnibox
├── package.json                  # Dependencias npm (exceljs, express, puppeteer-core, ws)
├── package-lock.json             # Árbol de dependencias bloqueado
├── README.md                     # Documentación de usuario y caso de negocio
├── resultados.csv                # Persistencia histórica estructurada (10 columnas)
├── rpa_runner.js                 # Motor de automatización RPA visible con Puppeteer
├── server.js                     # Servidor Express, API REST y WebSocket Stream
├── supermercados.tag             # Script TagUI para cumplimiento curricular
└── validador.js                  # Motor de normalización, validación y reporte CLI
```

---

## 4. Responsabilidad de Cada Módulo Importante

### `rpa_runner.js`
- **Responsabilidad:** Motor EXCLUSIVO para la Canasta / Compra del Mes. Orquesta el recorrido visible por los 3 supermercados con Puppeteer.
- **Entrada:** Objeto de opciones `{ modo: 'compra_mes', items: [{ producto, cantidad, unidad }], demoMode, typingDelay, mouseDuration, onStatus }`.
- **Salida:** Array de objetos con resultados extraídos; adición en `resultados.csv`.
- **Restricción:** No debe utilizarse para búsquedas individuales (bloqueado con guard estricto).
- **Funciones clave:**
  - `getChromePath()`: Encuentra el binario de Chrome/Edge en Windows.
  - `visibleNavigate(page, url)`: Mueve el cursor a la barra de direcciones, ejecuta `mouse_helper.exe nav <url>` y aguarda navegación real.
  - `visibleType(page, selector, text, delay)`: Mueve el cursor físico al input, hace click nativo, borra texto previo (`Ctrl+A` + `Backspace`) y tipea carácter por carácter con el helper Win32.
  - `visibleClick(page, selector)`: Lee la posición del elemento, mueve el mouse físico de forma progresiva y ejecuta el click nativo.
  - `visibleScroll(page, pixels, steps)`: Desplazamiento progresivo con la rueda física del mouse.
  - `searchCarrefour()`, `searchCoto()`, `searchDia()`: Módulos específicos por tienda.
  - `abortCurrentRun()`: Kill-switch para detener la ejecución y cerrar Chrome inmediatamente.

### `mouse_helper.cs` / `mouse_helper.exe`
- **Responsabilidad:** Capa única de interacción visible para el motor de producción: Omnibox, cursor físico, clicks, tipeo y rueda dentro de Chrome.
- **Mecanismo:** Invoca `SetProcessDPIAware`, `SetCursorPos`, `mouse_event` y `SendKeys`, convirtiendo coordenadas CSS del viewport a coordenadas reales de la ventana.
- **Modos:**
  - `nav <url> [delay]`: Mueve el mouse físico a la barra de direcciones de Chrome (~y=82), hace click, envía `Ctrl+L` / `Alt+D`, tipea la URL y pulsa `Enter`.
  - `move <x> <y> [duration]`: Movimiento físico por curvas de Bézier cúbicas.

### `server.js`
- **Responsabilidad:** Servidor HTTP y orquestador de API para la Web UI.
- **Concurrencia:** Variable de bloqueo booleana `isRpaRunning`. Solo 1 RPA simultáneo permitido; rechaza con código HTTP 409 si hay otro en curso.
- **WebSocket:** Canal `/ws/rpa-stream`. Transmite eventos: `{ type: 'log'|'progress'|'status', ... }`. Si todos los clientes de frontend se desconectan durante una ejecución, aborta automáticamente el RPA.
- **Manejo EBUSY:** Ejecuta `taskkill /F /IM EXCEL.EXE` antes de cualquier corrida para evitar bloqueos del archivo Excel en Windows.

### `validador.js`
- **Responsabilidad:** Normalización y validación semántica de datos extraídos.
- **Detección de Intención:**
  - `ESPECIFICA`: Exige coincidencia estricta de la marca solicitada (`La Serenísima`, `Molinos Ala`, `Coca Cola`, etc.) y coherencia de presentación/volumen.
  - `GENERICA`: Compara dentro de la categoría y valida que no pertenezca a listas de términos incompatibles (`terminosIncompatibles`).
- **Estados generados:** `VALIDADA`, `SIN STOCK`, `NO ENCONTRADO`, `COINCIDENCIA NO VÁLIDA`.
- **Modo CLI:** Soporta `--reporte-individual <producto>`, `--limpiar <1|2|3>`, `--crear-temp <producto>`.

### `generar_excel.js`
- **Responsabilidad:** Transformar `resultados.csv` en `reporte_supermercados.xlsx` con formato corporativo.
- **Hojas generadas:**
  1. `🏆 Conclusiones` (KPIs ejecutivos, tabla de ganadores, mejor canasta).
  2. `🛒 Canasta Mensual` (Matriz comparativa de precios con menor valor en verde).
  3. `📊 Ranking Menor a Mayor` (Podio con medallas de precio ascendente).
  4. `🔎 Consultas Individuales` (Histórico de búsquedas unitarias).
  5. `⚠️ Disponibilidad y Stock` (Detalle de productos sin stock o rechazados con motivo).

### `supermercados.tag`
- **Responsabilidad:** Motor EXCLUSIVO para la Búsqueda Rápida Individual. Ejecutado mediante `tagui supermercados.tag <archivo_de_entrada>`.
- **Entrada:** Archivo CSV de entrada (`temp_input.csv` o similar con cabecera `producto,modo,cantidad,unidad`).
- **Salida:** Escritura en `resultados.csv` con columna `modo = individual` respetando las 10 columnas RFC-4180.
- **Restricción:** No debe utilizar Puppeteer, ni `rpa_runner.js`, ni `page.goto()`. Compra del Mes no utiliza TagUI.

---

## 5. Tecnologías y Versiones

| Tecnología | Versión | Uso |
| :--- | :--- | :--- |
| **Node.js** | `>= 18.0.0` | Runtime principal |
| **express** | `^5.2.1` | Servidor HTTP REST |
| **ws** | `^8.21.3` | Servidor WebSocket |
| **puppeteer-core** | `^25.10.0` | Automatización de Chrome vía CDP |
| **exceljs** | `^3.4.0` | Construcción de planillas Excel |
| **C# / .NET** | `4.0+` | Compilador `csc.exe` para `mouse_helper.exe` |
| **TagUI** | `v6.110.0` | Motor de RPA académico |

---

## 6. Cómo Ejecutar el Proyecto

### Vía Dashboard Web:
```cmd
interfaz.bat
```
*(O alternativamente: `node server.js` y abrir `http://localhost:3000`).*

### Vía Consola Windows:
```cmd
ejecutar.bat
```

### Vía CLI directo (búsqueda individual):
```cmd
ejecutar.bat "arroz largo fino"
```

### Vía TagUI directo:
```cmd
tagui supermercados.tag input.csv
```

---

## 7. Cómo Probar el Proyecto

1. **Prueba de validación y limpieza semántica:**
   ```bash
   node validador.js --diagnostico
   ```
2. **Prueba de generación de Excel:**
   ```bash
   node generar_excel.js
   ```
3. **Prueba de búsqueda individual exclusiva por TagUI:**
   ```bash
   node validador.js --crear-temp "Arroz Gallo Largo Fino 1 kg" && tagui supermercados.tag temp_input.csv
   ```
4. **Pruebas de regresión automatizadas:**
   ```bash
   node tests/verify_compra_mes.js
   node tests/test_error_concurrency.js
   node tests/verify_live_search_manaos.js
   ```

---

## 8. Reglas que el Agente DEBE Respetar

1. **NO atajos sintéticos:** No usar `page.goto(url_con_busqueda)` para saltear el buscador de la tienda, ni `input.value = ...` sin tipeo real. La visualización paso a paso es la razón de ser del proyecto.
2. **NO romper el esquema de `resultados.csv`:** El archivo debe mantener exactamente las 10 columnas:
   `modo,producto_solicitado,nombre_encontrado,precio,supermercado,url,fecha,stock_status,cantidad,unidad`.
3. **NO romper el reporte Excel:** `generar_excel.js` depende estrictamente de las 10 columnas de `resultados.csv` y debe seguir generando las 5 hojas sin alterar los nombres de las pestañas.
4. **NO eliminar `supermercados.tag`:** Es un entregable obligatorio para la cátedra universitaria. Cualquier cambio de selectores o columnas debe replicarse en él.
5. **Cierre preventivo de Excel en Windows:** Antes de escribir en `reporte_supermercados.xlsx`, siempre asegurarse de que el archivo no esté bloqueado por el proceso de Microsoft Excel.
6. **Kill-Switch y control de aborto:** Toda función que realice pausas o bucles debe invocar `checkAborted()` para respetar cancelaciones inmediatas del usuario.
7. **Respetar formato CRLF en scripts `.bat`:** Los archivos `.bat` en Windows deben conservarse con saltos de línea Windows (`CRLF`) para evitar que el intérprete de comandos falle al leer bloques condicionales.
8. **Regla Estricta FailSafe de Movimiento del Mouse:** Si el usuario mueve físicamente el mouse en cualquier momento durante la ejecución del RPA, el proceso DEBE abortar de inmediato (< 0.05s), cerrar Google Chrome y terminar la corrida completa limpiamente, sin continuar a otros supermercados ni generar/abrir el reporte Excel.

---

## 9. Requisitos de la Cátedra (UTN FRCU - Tecnologías para la Automatización)

- **Institución:** Universidad Tecnológica Nacional – Facultad Regional Concepción del Uruguay.
- **Año Académico:** 2026.
- **Materia:** Tecnologías para la Automatización.
- **Etapa 1:** Automatización Robótica de Procesos (RPA).
- **Supermercados requeridos:** Carrefour Argentina, COTO Digital y Supermercados Día %.
- **Salida esperada:** Persistencia estructurada, cálculo de canasta ganadora, compra óptima combinada y reporte en Microsoft Excel.
- **Entregable fundamental:** Script TagUI ejecutable con `tagui supermercados.tag input.csv`.

---

## 10. TagUI y las Partes Obligatorias

El archivo `supermercados.tag` debe:
- Aceptar el archivo `input.csv` como argumento.
- Iterar mediante variables nativas de TagUI (`iteration`, `producto`, etc.).
- Visitar las 3 tiendas online en Chrome.
- Ejecutar extracción en bloques `dom begin ... dom finish`.
- Escribir las filas en `resultados.csv` con la función `csv_row(...)`.

---

## 11. Qué Partes NO Debe Romper un Agente

- El formato de `input.csv`: cabecera `producto,cantidad,unidad` (o `producto,modo`).
- Los nombres de las columnas en `resultados.csv`.
- Las 5 hojas de `reporte_supermercados.xlsx` y la lógica de cálculo de la compra óptima.
- El endpoint WebSocket `/ws/rpa-stream` y el formato de mensajes `{ type, message, percent, state }`.
- El ejecutable `mouse_helper.exe` (si se modifica `mouse_helper.cs`, debe ser recompilado con `csc.exe`).

---

## 12. Convenciones de Código

- **Node.js:** Modularidad mediante CommonJS (`require` / `module.exports`).
- **Asincronía:** Uso prioritario de `async/await` con manejo explícito de errores `try/catch`.
- **Codificación:** UTF-8 sin BOM para todos los archivos `.js`, `.json`, `.csv`, `.tag`, `.html`, `.css`.
- **Scripts de Windows:** Codificación CRLF en archivos `.bat`.
- **Selectores CSS:** Diseñar selectores robustos ante actualizaciones de clase de VTEX y Angular, usando atributos parciales como `[class*="productBrand"]`, `[placeholder*="busc" i]`.

---

## 13. Decisiones de Arquitectura Actuales

- **¿Por qué Puppeteer-Core además de TagUI?**
  TagUI se conserva como entregable curricular independiente. El Dashboard no lo encadena ni duplica su flujo: `rpa_runner.js` es el único motor de producción visible y provee streaming WebSocket.
- **¿Por qué `mouse_helper.cs`?**
  Puppeteer se utiliza sólo para lectura de coordenadas, navegación observada y extracción. `mouse_helper.exe` realiza toda acción visible, tanto en la Omnibox como dentro del viewport.
- **¿Por qué el validador está separado en `validador.js`?**
  Para permitir que tanto la consola CLI, como el motor Puppeteer, el script TagUI y el generador de Excel consuman exactamente el mismo criterio de negocio sobre qué producto es válido y cuál es un falso positivo.

---

## 14. Problemas Conocidos

1. **Robo de foco de teclado:** `mouse_helper.exe` envía eventos reales de teclado de Windows (`keybd_event`). Si el usuario hace click en otra ventana durante los primeros 2 segundos de navegación a un súper, la URL podría escribirse en la aplicación equivocada.
2. **Bloqueo EBUSY en Excel:** Si el usuario tiene abierto `reporte_supermercados.xlsx` en Microsoft Excel, Windows bloquea la escritura. Para prevenirlo, `server.js` y `ejecutar.bat` ejecutan `taskkill /F /IM EXCEL.EXE`.
3. **Modales emergentes en e-commerce:** Carrefour y Día % despliegan frecuentemente modales de código postal o promociones que se neutralizan en `eliminarCookies(page)`.

---

## 15. Bugs Pendientes

- ~~**Selector del dropdown de ordenamiento en Día % (`rpa_runner.js`):** RESUELTO en septiembre 2026.~~ Se reemplazó el selector genérico por un selector priorizado (`[role="menuitem"], [role="option"]`) con fallback a `page.evaluate` que busca el texto exacto «más bajo» / «menor precio» entre todos los candidatos interactivos.
- No se reportan bugs pendientes en el estado actual del proyecto.

---

## 16. Funcionalidades Pendientes

1. ~~**Afinamiento del selector de orden en Día %:**~~ COMPLETADO. Selector refinado con fallback a `page.evaluate`.
2. **Modo Headless opcional con grabación:** Permitir alternar en la Web UI entre demostración en vivo (visible) y ejecución silenciosa en segundo plano con exportación de video de la corrida.
3. **Soporte para más cadenas:** Posibilidad de sumar Jumbo o Changomas utilizando la misma interfaz modular.

---

## 17. Código que Puede Simplificarse

- **Extracción DOM compartida Carrefour / Día %:** Ambos sitios están construidos sobre VTEX IO. La función de evaluación del DOM para extraer tarjetas y validar con `validador.js` puede unificarse en una función auxiliar común para reducir líneas repetidas.
- **Visor experimental (`public/visor-proceso.html`):** Eliminado por requerimiento de usuario para mantener la arquitectura centrada en el reporte Excel y el Dashboard principal.

---

## 18. Código que NO Debería Eliminarse sin Analizar Dependencias

- **`mouse_helper.exe` / `mouse_helper.cs`:** Utilizado por `rpa_runner.js` para la navegación por Omnibox.
- **`supermercados.tag`:** Requisito curricular de cátedra; invocado desde `ejecutar.bat`.
- **`validador.js`:** Esencial para `server.js`, `rpa_runner.js`, `generar_excel.js` y `ejecutar.bat`.
- **`generar_excel.js`:** Requerido para la salida en Excel por todos los lanzadores.
- **`input.csv`:** Fuente de datos de la canasta mensual.

---

## 19. Cómo Verificar los Cambios Antes de Considerarlos Terminados

Antes de dar por concluida cualquier modificación en el código:

1. **Verificar sintaxis de Node.js:**
   ```bash
   node -c rpa_runner.js server.js validador.js generar_excel.js
   ```
2. **Ejecutar diagnóstico semántico:**
   ```bash
   node validador.js --diagnostico
   ```
3. **Ejecutar una prueba en vivo con producto individual vía TagUI:**
   ```bash
   node validador.js --crear-temp "Arroz Gallo Largo Fino 1 kg" && tagui supermercados.tag temp_input.csv
   ```
4. **Verificar que se genera el archivo Excel sin errores:**
   ```bash
   node generar_excel.js
   ```
5. **Revisar estado de Git:**
   ```bash
   git status
   ```

---

## 20. Estado Actual del Proyecto

- **Qué está funcionando:**
  - **Motor RPA Visible (`rpa_runner.js`):** Inicia Chrome maximizado, navega por Omnibox con `mouse_helper.exe`, y usa ese mismo helper para mouse, clicks, tipeo y scroll físicos visibles. El cursor virtual se inyecta automáticamente tras cada navegación.
  - **Carrefour Argentina:** Navegación, tipeo, búsqueda, ordenamiento por "Precios más bajo" y extracción 100% funcionales.
  - **COTO Digital:** Navegación, tipeo en autocompletado Constructor, ejecución, ordenamiento `price|ascending` y extracción 100% funcionales.
  - **Día %:** Navegación, tipeo, ordenamiento con selector refinado y fallback, extracción de productos y detección de precios reales con descuentos 100% funcionales.
  - **Dashboard Web (`http://localhost:3000`):** Conexión WebSocket `/ws/rpa-stream`, streaming de logs y telemetría, sliders de velocidad, controles de demostración, modal interactivo de edición de canasta, monitor de pasos de supermercados, botón Kill-Switch para abortar RPA, enlace al visor de resultados y footer con créditos UTN 100% funcionales.
  - **Validación Semántica (`validador.js`):** Detección de intención específica vs genérica, exclusión estricta de marcas ajenas y categorías incompatibles 100% funcional. CSV con 10 columnas consistentes en limpieza parcial.
  - **Reporte Excel (`generar_excel.js`):** Las 5 hojas se generan con formatos condicionales, medallas y cálculo matemático de canasta ganadora y compra combinada óptima: 🏆 Conclusiones, 🛒 Canasta Mensual, 📊 Ranking Menor a Mayor, 🔎 Consultas Individuales, ⚠️ Disponibilidad y Stock.
  - **Regla Estricta FailSafe de Mouse:** Supervisor watchdog en `mouse_helper.exe watchdog` y detección activa de desvío en `MoveSmooth` (> 35px en movimiento, > 14px en reposo) que detiene inmediatamente el RPA, cierra Google Chrome y emite aviso por WebSocket ante cualquier movimiento manual del mouse por parte del usuario.
  - **TagUI (`supermercados.tag`):** Script preservado y compatible para los requerimientos de la cátedra.
- **Qué está parcialmente funcionando:**
  - Nada parcial. Todos los módulos funcionan al 100%.
- **Qué está roto:**
  - Nada roto a nivel de servidor, rutas, APIs o integración general.
- **Qué estamos intentando conseguir:**
  - Una automatización RPA ejemplar, fluida y 100% visible que demuestre paso a paso el comportamiento humano sobre Google Chrome, integrada a un Dashboard Web moderno y a un pipeline de análisis de datos riguroso.
- **Cuál debería ser el próximo objetivo lógico:**
  - Correr una prueba integral de la "Compra del Mes" completa desde la Web UI para validar los 10 productos de la canasta contra los 3 supermercados.

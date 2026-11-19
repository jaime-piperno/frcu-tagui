# Documentación de Cambios — Etapa 2 (Grupo 9)

**Equipo:** María Slootmans Corrá, Franco Valli, Victoria Nuñez Baccon.
**Proyecto base:** [`team_1`](../../team_1) — Comparador RPA de Precios (Grupo 1, Etapa 1).
**Alcance de esta etapa:** agregar monitoreo continuo con persistencia histórica y alertas automáticas por Telegram, sin modificar el motor de scraping original.

Este documento complementa al [`README.md`](../README.md) y describe, archivo por archivo, qué se agregó o modificó respecto del proyecto recibido y por qué.

---

## 1. Punto de partida

El proyecto recibido automatiza la búsqueda de productos en Carrefour, COTO y Día % con Puppeteer y un controlador Win32 nativo para mover el cursor y tipear en pantalla de forma visible, valida los nombres de los artículos y vuelca las cotizaciones en un reporte de Excel.

**Limitaciones detectadas en la auditoría previa:**
- **Sin memoria de datos:** cada corrida pisaba `resultados.csv`; no quedaba registro para cotejar valores entre fechas distintas.
- **Sin detección de bajas:** el sistema comparaba precios entre cadenas en el mismo momento, pero no contra el historial propio de cada producto.
- **Sin canal proactivo:** no había notificaciones remotas; había que abrir el dashboard para enterarse de una baja.

**Criterio técnico seguido:** preservar intacto el código base (selectores de navegador, reporte Excel, motor de validación) y acoplar la mejora como una capa modular al cierre de cada ejecución del scraping.

---

## 2. Archivos nuevos

| Archivo | Qué hace | Por qué se hizo así |
| :--- | :--- | :--- |
| `historial.js` | Lee/escribe `historial_precios.jsonl` (una línea por ítem de cada corrida) y `alertas_emitidas.jsonl` (alertas ya notificadas, para no repetir avisos). | Se eligió **JSON Lines** en vez de un único JSON grande porque permite `fs.appendFileSync` directo al final del archivo sin releer ni reescribir todo el contenido — menor uso de memoria y sin bloqueos de escritura. |
| `notificador.js` | Cliente mínimo de la API de Telegram: `enviar(texto)` y `enviarBienvenida()`, usando `fetch()` nativo de Node.js con `AbortSignal.timeout(10000)`. | Se descartó agregar un SDK de Telegram de terceros (se probó una variante en Java/Maven con la librería `telegrambots`, ver `pom.xml` del lado de desarrollo, descartada) a favor de una llamada HTTP directa: menos dependencias, mismo lenguaje que el resto del backend. |
| `public/historial-dashboard.js` + `.css` | Agrega al dashboard un selector de producto con gráfico de tendencia de precios (Canvas nativo), una tabla de alertas emitidas y un resumen de la canasta actual. | Reutiliza el Canvas 2D nativo del navegador en vez de sumar una librería de gráficos para mantener el frontend sin dependencias nuevas. |
| `historial_precios.jsonl` | Historial acumulado de cotizaciones (se genera en ejecución; se incluye como evidencia de funcionamiento). | — |
| `.env.example` | Plantilla de variables de entorno sin credenciales reales. | El `.env` real (con el token del bot) nunca se versiona — ver sección 4. |

---

## 3. Archivos modificados

| Archivo | Qué se le agregó |
| :--- | :--- |
| `server.js` | - `require('./historial.js')` y `require('./notificador.js')`.<br>- `UMBRAL_BAJA_PCT` leído de `.env` (10% por defecto).<br>- Función `detectarAlertas(previo, actuales)`: por cada ítem de la corrida nueva, busca su historial (mismo producto + supermercado) y genera una alerta `BAJA` si el precio cae ≥ `UMBRAL_BAJA_PCT`% respecto del último registrado, o `MINIMO_HISTORICO` si el precio nuevo es menor al mínimo de todo el historial (`Math.min`).<br>- Al cerrar cada corrida (canasta e individual): guarda la corrida en el historial, guarda las alertas nuevas y las envía por Telegram (`notificador.enviar`).<br>- Envía el mensaje de bienvenida al iniciar el servidor.<br>- Nuevos endpoints: `GET /api/historial`, `GET /api/alertas`, `GET /api/resumen-canasta`.<br>- Parser propio de `.env` (`cargarVariablesEntorno()`), sin agregar la dependencia `dotenv`. |
| `validador.js` | Nuevas funciones `obtenerReferenciasImagen(itemId, supermercado)` y `registrarEvidenciaImagen(query, itemResultado)`, que leen/escriben `evidencia_imagenes.json`: guardan la URL/alt/título de la imagen del producto confirmado para cada ítem del catálogo + supermercado, y permiten consultarlas luego. |
| `supermercados.tag` | El bloque `dom` de extracción de Carrefour y de COTO ahora también lee la imagen del resultado (`img.currentSrc/src/data-src`, `alt`, `title`), construye una URL canónica comparable y la contrasta contra las referencias ya confirmadas del catálogo (`trustedImages`) para reforzar el nombre detectado cuando el texto es ambiguo o incompleto. El resultado persiste la evidencia de imagen junto con el resto de la fila en `resultados.csv`. |
| `public/index.html` | Incorpora el panel de historial (gráfico, tabla de alertas, resumen de canasta) y carga `historial-dashboard.css`/`.js`. |
| `.gitignore` | Se agregan `.env`, `.idea/`, `.DS_Store`, `target/`, `pom.xml` y `alertas_emitidas.jsonl` para no versionar secretos, configuración de IDE ni artefactos de build. |

Los demás archivos heredados (`rpa_runner.js`, `catalogo.js`/`.json`, `mouse_helper.cs`/`.exe`, `generar_excel.js`, `AGENTS.md`, `docs/guia_visual.html`) no fueron modificados.

---

## 4. Seguridad: credenciales fuera del repositorio

El `.env` original de desarrollo contenía el token real del bot de Telegram y el chat ID. **No se sube al repositorio** (está en `.gitignore`); en su lugar se publica `.env.example` con placeholders, siguiendo la misma convención que ya usan otros equipos de la cátedra (`team_2`, `team_15`). Quien clone el proyecto debe copiar `.env.example` a `.env` y completarlo con sus propias credenciales (ver [README, sección 13](../README.md#13-configuración-del-bot-de-telegram)).

---

## 5. Experimento descartado: bot en Java/Maven

Durante el desarrollo se probó una variante del bot de notificaciones en Java, usando Maven y la librería `telegrambots` (quedó un `pom.xml` y un `.class` compilado sin el código fuente `.java` correspondiente). Se descartó en favor de `notificador.js` por no requerir un segundo runtime (JVM) además de Node.js, y por integrarse directamente con `server.js` sin necesidad de un proceso separado. Ese experimento no forma parte de esta entrega.

---

## 6. Flujo de ejecución actualizado

```
1. Extracción web      → Puppeteer/TagUI leen los valores en Carrefour, COTO y Día %.
2. Registro             → historial.guardarCorrida() anexa los datos al JSONL con marca temporal.
3. Lectura              → server.js recupera los registros previos de ese mismo artículo.
4. Comparación          → detectarAlertas() evalúa si el precio actual bajó respecto del
                          último registro o del mínimo histórico.
5. Filtro anti-duplicado→ alertas_emitidas.jsonl evita notificar la misma baja dos veces.
6. Aviso push           → notificador.enviar() manda el mensaje a Telegram con producto,
                          valores y porcentaje de ahorro.
```

Módulo adicional en paralelo: el panel web de historial (`historial-dashboard.js`) consulta `GET /api/historial` y `GET /api/alertas` para graficar la tendencia y listar los avisos, sin intervenir en el flujo de scraping.

---

## 7. Resultados observados

- **Tiempo de aviso:** menor a 1 segundo entre el cierre de la búsqueda y la llegada del mensaje a Telegram (acotado por el timeout de 10 s de `fetch`, en la práctica muy por debajo).
- **Pérdida de datos:** 0% — `historial_precios.jsonl` es un archivo acumulativo que nunca se sobrescribe.
- **Control de duplicados:** 100% de las bajas ya notificadas quedan registradas en `alertas_emitidas.jsonl` y no se vuelven a enviar.

---

## 8. Reflexión sobre el proyecto recibido

**Lo más complejo de comprender:** la sincronización entre Puppeteer y el ejecutable en C# (`mouse_helper.exe`), junto con los selectores dinámicos de cada tienda; y la necesidad de estudiar a fondo la estructura interna antes de acoplar nuevas capas de software sin romper nada existente.

**Puntos que, a futuro, convendría documentar mejor en el proyecto original:** los prerrequisitos completos del entorno (.NET para el helper nativo, resolución de pantalla, variables de configuración) y el mapeo de puertos locales para agilizar el despliegue en computadoras ajenas.

**Conclusión:** el desacoplamiento del proyecto original facilitó enganchar las mejoras de la Etapa 2 al cierre del proceso, sin alterar el scraping base.

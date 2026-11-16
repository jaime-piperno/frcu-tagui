# 📌 UTN FRCU – Tecnologías para la Automatización 2026

[](https://github.com/jaime-piperno/frcu-tagui/tree/main/projects/202X/TagUI/team_x#-utn-frcu--tecnolog%C3%ADas-para-la-automatizaci%C3%B3n-year)

## 👥 Grupo

[](https://github.com/jaime-piperno/frcu-tagui/tree/main/projects/202X/TagUI/team_x#-team)

- **Cantidad de Integrantes:** 5
- **Miembros:**
    - Caire Federico
    - Cardozo Gabriel
    - Hanza Garcia Matías Emanuel
    - Retamar Schumacher Jeremías
    - Rojas Tobías Uriel

---

## 🤖 Descripcion del Bot

- **Descripcion:** Bot web (RPA) que permite automatizar la búsqueda de procesos de compra que los organismos de la Administración Pública cargaron utilizando la plataforma [comprar.gob.ar](https://comprar.gob.ar/). Permite filtrar por **Rubro**, **Tipo de Proceso**, **Estado del Proceso**, **Tipo de Operación** y **Fechas**. 
Cuenta con un sistema de **Presets** (`/presets`) para guardar tus filtros más utilizados y reejecutarlos rápidamente. Además, incorpora un sistema de **Alertas Automáticas** (`/alertas`) que busca licitaciones en segundo plano periódicamente y te notifica de forma proactiva cada vez que encuentra procesos nuevos que coinciden con tus criterios, generándote un reporte en Excel.
- **Tecnologías utilizadas:** Python + TagUI (a través de la librería `rpa`/`tagui`)
- **Estructura del repositorio:**
    - config.py — carga de .env y rutas/constantes globales.
    - alertas.py — lógica de guardado y validación de las alertas y sus estados.
    - rubros.py — el diccionario RUBROS (dato estático).
    - opciones.py — los diccionarios de opciones para filtros avanzados.
    - scraper.py — la automatización RPA sobre comprar.gob.ar.
    - configuraciones.py — CRUD de los presets guardados.
    - teclados.py — construcción de los teclados inline.
    - handlers.py — los handlers de Telegram y la navegación de menús.
    - bot.py — arma la app de Telegram, tarea de fondo, y expone main().
    - main.py — entrypoint principal.

---

## 🛠️ Instrucciones de uso

### Ejecucion Recomendada: Despliegue con Docker

La imagen ya incluye todas las dependencias externas (Python, PHP, Google Chrome headless y TagUI), así que no hace falta instalar nada de lo anterior. Sólo requiere el `TELEGRAM_BOT_TOKEN` en el `.env` y tener instalado Docker (Instalacion en Windows: https://docs.docker.com/desktop/setup/install/windows-install/ . Instalacion en Linux(Debian/Ubuntu): `sudo apt install docker.io` . Instalacion en MacOs: https://docs.docker.com/desktop/setup/install/mac-install/ )

Despliegue en Windows:

1. Inicializacion de archivos de configuracion (Se realiza una unica vez):

```Powershell
$utf8SinBom = New-Object System.Text.UTF8Encoding($false)

[System.IO.File]::WriteAllText("$PWD\configuraciones_busqueda.json", "{}", $utf8SinBom)
[System.IO.File]::WriteAllText("$PWD\alertas_busqueda.json", "{}", $utf8SinBom)
[System.IO.File]::WriteAllText("$PWD\licitaciones_vistas.json", "{}", $utf8SinBom)
```

2. Construccion y despliegue del contenedor (Se realiza cada vez que se quiera correr el bot):

```Powershell
docker build -t bot-comprar .
docker run -d --name bot-comprar --restart unless-stopped `
  --env-file .env `
  -v "${PWD}\resultados:/app/resultados" `
  -v "${PWD}\configuraciones_busqueda.json:/app/configuraciones_busqueda.json" `
  -v "${PWD}\alertas_busqueda.json:/app/alertas_busqueda.json" `
  -v "${PWD}\licitaciones_vistas.json:/app/licitaciones_vistas.json" `
  bot-comprar
```

Despliegue en Linux/MacOS:

1. Inicializacion de archivos de configuracion (Se realiza una unica vez):

```Bash
echo '{}' > alertas_busqueda.json
echo '{}' > configuraciones_busqueda.json
echo '{}' > licitaciones_vistas.json
```

2. Construccion y despliegue del contenedor (Se realiza cada vez que se quiera correr el bot):

```Bash
docker build -t bot-comprar .
docker run -d --name bot-comprar --restart unless-stopped \
  --env-file .env \
  -v "$(pwd)/resultados:/app/resultados" \
  -v "$(pwd)/configuraciones_busqueda.json:/app/configuraciones_busqueda.json" \
  -v "$(pwd)/alertas_busqueda.json:/app/alertas_busqueda.json" \
  -v "$(pwd)/licitaciones_vistas.json:/app/licitaciones_vistas.json" \
  bot-comprar
```

### Ejecucion Local (Experimental): Windows, Linux, MacOS

#### 1. Requisitos externos (no cubiertos por `requirements.txt`)

`requirements.txt` sólo instala los paquetes de Python. TagUI, el motor que ejecuta la automatización, necesita además lo siguiente:

- **Python 3.8+** instalado en el sistema.
- **PHP CLI:** TagUI usa `php` para su script de arranque. Instalacion en Linux (Debian/Ubuntu): `sudo apt install -y php-cli`. Instalacion en Windows: instalar PHP (por ejemplo desde [windows.php.net](https://windows.php.net/download/) o `choco install php`). Instalacion en MacOs: `brew install php`.
- **Un navegador soportado:** Google Chrome (recomendado) o Firefox instalado en el equipo. 
- **Java JDK 8+ (opcional):** permite ver los comandos de automatización visual.

#### 2. Instalación

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

#### 3. Configuración

Copiá `.env.example` a `.env` y completá las variables:

```bash
cp .env.example .env
```

- `TELEGRAM_BOT_TOKEN` (obligatoria): token del bot de Telegram, obtenido desde [@BotFather](https://t.me/BotFather).

#### 4. Ejecución

**Linux / macOS**

```bash
source venv/bin/activate
python3 main.py
```

**Windows (PowerShell)**

```powershell
venv\Scripts\Activate.ps1
python main.py
```

---

## 📝 Información Adicional

[](https://github.com/jaime-piperno/frcu-tagui/tree/main/projects/202X/TagUI/team_x#-additional-notes)

- Actualmente la ejecucion local para Windows resulta experimental ya que la libreria rpa/TagUI de python puede generar conflictos con dependencias del sistema operativo especificas (archivos .dll, binarios, etc) los cuales varian dependiendo la maquina de ejecucion, ademas el anitivirus de Windows puede generar conflicto el uso de rpa. Por lo que tomo la decision tecnica de dockerizar la aplicacion para aumentar la compatibilidad y reducir la configuracion y despliegue en dos comandos.
- Actualmente el bot no permite concurrencia, ya que utiliza archivos .json a las cuales no se le realiza un control de sincronizacion y acceso al recurso compartido.
- Posible mejora a futuro: En la pagina actualmente existe un apartado que permite buscar Items (https://comprar.gob.ar/Item/Item/BuscarItemCiudadano). La idea es aprovecharlo para que, al scrapear los procesos, el bot también recolecte los ítems asociados a cada uno (descripción, cantidad, unidad de medida, etc.) y los cruce contra un catálogo de ítems propio de la empresa, cargado desde un Excel o una base de datos. De esta forma el bot podría:
    - Detectar automáticamente qué licitaciones incluyen ítems que la empresa puede proveer.
    - Indicar en el reporte de Excel el grado de coincidencia de cada proceso (cuántos y cuáles ítems matchean con el catálogo).
    - Priorizar las alertas, notificando sólo los procesos que tengan al menos un ítem relevante para la empresa.
    - Como el matching por texto exacto puede ser limitado (las descripciones varían entre organismos), podría complementarse con búsqueda por palabras clave, similitud de texto o códigos de catálogo.

---

## 🔄 Etapa 2 – Mejora (Stage 2 – Improvement)

- **Número de Grupo (Team number):** 10
- **Miembros (Members):**
  - Octavio Orcellet
  - Milton Ibarra
  - Francisco Bournissen
  - Edgardo Del Real
  - Marcos Cettour

### 🚀 Descripción de la Mejora (Improvement Description)

- **Qué se mejoró (What was improved):**
  1. **Gestión del Catálogo de la Empresa (`/catalogo` y `catalogo.py`):** Se creó un nuevo comando `/catalogo` en Telegram y el módulo `catalogo.py` para administrar un archivo Excel propio (`catalogo_empresa.xlsx` con columnas `Codigo`, `Descripcion`, `Palabras_Clave` y `Rubro`). Desde Telegram el usuario puede listar su catálogo, eliminar ítems, agregar ítems manualmente, descargar o subir/reemplazar el archivo `.xlsx` completo, y consultar en vivo el buscador oficial [BuscarItemCiudadano](https://comprar.gob.ar/Item/Item/BuscarItemCiudadano) de COMPR.AR para agregar ítems con su código oficial tocando un botón inline.
  2. **Recolección de Ítems por Licitación (`scraper.py`):** Durante la búsqueda de procesos, el bot ahora accede a la vista previa del pliego (`VistaPreviaPliegoCiudadano.aspx`) y extrae la tabla `"Detalle de productos o servicios"` (`#ctl00_CPH1_UCVistaPreviaPliego_UC_DetalleProductos_gvLineaPliego`), recolectando para cada renglón: número de renglón, objeto del gasto, código oficial del ítem, descripción técnica, cantidad y unidad de medida.
  3. **Motor de Cruce Inteligente en 3 Niveles (`catalogo.py`):** Cada ítem licitado se compara contra `catalogo_empresa.xlsx` combinando tres niveles: **1) Código oficial de COMPR.AR** (100% código exacto / 88% misma clase), **2) Palabras clave normalizadas** (65% a 95% sin tildes ni signos) y **3) Similitud de texto difusa y solapamiento de tokens** (`difflib.SequenceMatcher` 60% filtrando *stopwords*).
  4. **Reporte Excel Enriquecido de 2 Hojas (`.xlsx`):** El reporte descargado se transforma en un archivo `.xlsx` con dos hojas: `Procesos` (que conserva las columnas originales y agrega `Coincide con Catálogo`, `Ítems Coincidentes`, `Grado de Coincidencia` y `Detalle de Coincidencias`) e `Items_Licitados` (desglose renglón por renglón de todos los ítems extraídos y el criterio/puntaje de coincidencia de cada uno), además de enviar un resumen destacado en el chat de Telegram.
  5. **Priorización de Alertas Automáticas (`/alertas`):** Al crear una alerta se incorporó la opción de elegir entre **"🎯 Solo si incluye ítems de mi catálogo"** (`solo_catalogo=True`) o **"🌐 Notificar todas las del rubro"**, permitiendo que la tarea en segundo plano filtre y notifique únicamente aquellas licitaciones que tengan al menos un ítem coincidente con la empresa.
  6. **Control de Concurrencia y Pruebas Unitarias (`tests/test_catalogo.py`):** Se agregó sincronización sobre el navegador (`TAGUI_LOCK`), escrituras atómicas thread-safe en archivos `.json` y `.xlsx`, y una batería de pruebas unitarias en `tests/test_catalogo.py`.

- **Por qué (Why):**
  En la Etapa 1, el bot sólo descargaba la planilla general de cabeceras (`ReporteProcesos.xls`), donde únicamente figura el título general de la contratación pero no qué productos específicos ni qué cantidades demanda el organismo público. Esto obligaba al usuario a revisar manualmente cada pliego en la web para saber si podía cotizar y hacía que las alertas automáticas notificaran procesos irrelevantes para la empresa. Además, como las descripciones redactadas por cada organismo suelen variar, era necesario un motor de cruce flexible (código oficial, palabras clave y similitud de texto), junto con un control de sincronización que resolviera la limitación de concurrencia de la Etapa 1 cuando una alerta automática coincidía con una búsqueda manual.

### 🛠️ Instrucciones de Uso Actualizadas (Updated Usage Instructions)

- **Despliegue en Docker y Local (Sin cambios respecto a la Etapa 1):** Los pasos y comandos de instalación y ejecución en Docker y Local de la Etapa 1 se mantienen exactamente iguales. El archivo `catalogo_empresa.xlsx` se inicializa automáticamente con ítems de ejemplo al arrancar el bot y mantiene una copia sincronizada dentro del volumen ya existente `/app/resultados` (`resultados/catalogo_empresa.xlsx`) para persistir entre reinicios del contenedor.
- **Nuevos comandos e interacciones en Telegram:**
  - `/catalogo` — abre el menú interactivo para ver los ítems cargados, buscar ítems oficiales en `BuscarItemCiudadano` de COMPR.AR (por palabra o código) y sumarlos con un botón, cargar ítems manualmente (`CODIGO | DESCRIPCION | PALABRAS_CLAVE`), descargar `catalogo_empresa.xlsx`, subir un Excel `.xlsx` actualizado o eliminar ítems.
  - `/alertas` — al crear una nueva alerta, ahora permite seleccionar si se desea recibir avisos sólo cuando la licitación incluya ítems del catálogo de la empresa.
  - `/buscar` y `/presets` — ejecutan automáticamente la inspección de pliegos, envían en el chat un resumen de los procesos que coinciden con el catálogo y adjuntan el nuevo reporte `.xlsx` con las hojas `Procesos` e `Items_Licitados`.
- **Variable de entorno opcional en `.env`:**
  - `MAX_PROCESOS_INSPECCION` (opcional, por defecto `10`): define la cantidad máxima de procesos por búsqueda a los que se les inspeccionan los renglones del pliego en profundidad.
- **Ejecución de pruebas unitarias (opcional):**
  ```bash
  python -m unittest discover -s tests
  ```

### 📝 Información Adicional – Etapa 2 (Additional Notes)

- **Decisiones técnicas y desafíos resueltos:**
  - **Sincronización y Concurrencia (`TAGUI_LOCK` y escrituras atómicas):** Se incorporó un mutex global (`TAGUI_LOCK` en `scraper.py`) para serializar el uso de TagUI/Chrome. Si una revisión periódica de alertas coincide con una búsqueda manual de un usuario, el bot le avisa por Telegram que el navegador está ocupado y encola su consulta automáticamente en lugar de provocar un fallo de sesión en Chrome. Asimismo, la persistencia de `.json` y `catalogo_empresa.xlsx` utiliza guardado atómico (`tempfile` + `os.replace`) protegido por `threading.Lock`.
  - **Estrategia de Scraping Híbrido (HTTP + TagUI):** Abrir proceso por proceso únicamente con TagUI añadía varios segundos de latencia por cada pliego. Para optimizarlo, la consulta al buscador ciudadano (`BuscarItemCiudadano` / `_GrillaItems`) y la extracción de renglones (`VistaPreviaPliegoCiudadano.aspx`) priorizan peticiones HTTP directas con `httpx` replicando el estado de vista de ASP.NET (`__VIEWSTATE`, `__EVENTVALIDATION`), respondiendo en milisegundos y utilizando TagUI de forma transparente como mecanismo de respaldo (fallback) si la consulta HTTP falla.
- **Limitaciones restantes:**
  - Para mantener tiempos de respuesta ágiles en Telegram cuando un rubro devuelve decenas de contrataciones, la inspección detallada de renglones se acota por defecto a los primeros `MAX_PROCESOS_INSPECCION` procesos (10 por defecto, configurable por variable de entorno).
  - Si bien el acceso concurrente a los archivos ahora está protegido mediante locks en memoria y reemplazo atómico en un mismo contenedor/proceso, la persistencia continúa basada en archivos locales (`.json` y `.xlsx`) en lugar de un motor de base de datos cliente-servidor.

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
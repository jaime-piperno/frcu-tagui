# Instructivo de instalación

Cómo dejar el bot funcionando desde cero, en una máquina donde no hay nada instalado.
Está pensado para alguien que no participó del desarrollo.

Para usarlo una vez instalado, ver el [instructivo de uso](instructivo-uso.md).

---

## Qué vas a necesitar

1. **Python 3** — el lenguaje en el que está escrito el bot.
2. **Google Chrome** — el navegador que maneja el robot.
3. **La librería `rpa`** (RPA for Python) — la herramienta de RPA. Por dentro usa
   **TagUI**, que se descarga sola la primera vez.
4. **Un bot de Telegram** — con su token.
5. **Una cuenta de Telegram** y **un grupo** donde el robot va a escribir la lista.
6. **Este repositorio** descargado.

No hace falta instalar Microsoft Excel ni ningún otro programa: los datos se leen de
archivos `.csv` como texto plano, justamente para que funcione igual en cualquier sistema.

---

## Paso 1 — Instalar Python, Chrome y las librerías

### Windows

1. Instalá Python 3 desde https://www.python.org/downloads/ . En la primera pantalla
   del instalador **tildá "Add python.exe to PATH"**.
2. Verificá en una terminal nueva:
   ```
   py --version
   ```
   (Windows trae el lanzador `py`. Si no lo tenés, probá `python --version`.)
3. Instalá Google Chrome si no lo tenés: https://www.google.com/chrome/
4. Parado en la carpeta raíz del proyecto, instalá las librerías:
   ```
   py -m pip install -r requirements.txt
   ```

> **PHP en Windows:** no hace falta instalarlo. El TagUI que descarga la librería trae su
> propia copia adentro y la usa automáticamente.

### Linux

1. Instalá Python, pip y **PHP**. En Linux, a diferencia de Windows, TagUI **no** trae
   PHP incluido: lo busca en el sistema, y si falta falla con errores confusos.
   ```bash
   sudo apt update && sudo apt install python3 python3-pip php-cli
   ```
   (en Fedora/RHEL: `sudo dnf install python3 python3-pip php-cli`)
2. Instalá Google Chrome (el paquete `.deb` de https://www.google.com/chrome/ ).
3. Parado en la carpeta raíz del proyecto:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
   Si pip se niega con el error `externally-managed-environment` (pasa en Ubuntu 23.04
   o más nuevo y en Debian 12), agregale `--break-system-packages`:
   ```bash
   python3 -m pip install --user --break-system-packages -r requirements.txt
   ```

> **Nota honesta:** la instalación en Linux **todavía no se probó** en este proyecto 
> . Los pasos salen de la documentación de la librería `rpa`, que avisa que en Linux hace falta PHP.
> **Cuando alguien lo pruebe en Linux, actualizar esta sección con lo que realmente pasó.**

---

## Paso 2 — Crear el bot de Telegram

### 2.1 — Crear el bot y obtener el TOKEN

1. Abrí Telegram y buscá el contacto **@BotFather** (es el bot oficial de Telegram).
2. Mandale `/newbot`.
3. Te va a pedir dos cosas:
   - un **nombre** para el bot (cualquiera, ej: `Compras Grupo 13`)
   - un **username**, que tiene que terminar en `bot` (ej: `ComprasGrupo13_bot`)
4. Cuando termine, BotFather te responde con el **token**. Es una cadena larga con dos
   partes separadas por dos puntos, así:
   ```
   1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   Guardalo: es la contraseña del bot. **No lo compartas ni lo subas al repositorio.**

> 📸 *Sacar acá una captura de la conversación con BotFather (tapando el token) para
> incluir en el entregable.*

### 2.2 — Obtener el CHAT_ID

El chat_id es **el chat desde donde le vas a hacer los pedidos al bot**. El bot ignora
cualquier otro chat: si no, cualquiera que encontrara el bot podría manejar tu PC.

Lo más simple es usar tu chat privado con el bot:

1. Buscá tu bot en Telegram por el username que le pusiste y mandale cualquier mensaje
   (por ejemplo `hola`).
2. Abrí esta dirección en el navegador, reemplazando `<TOKEN>` por tu token:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
3. Vas a ver un texto en formato JSON. Buscá `"chat":{"id":` — ese número es tu chat_id.

(Si preferís hacer los pedidos desde un grupo, agregá el bot al grupo, escribí algo ahí y
buscá en `getUpdates` el id del chat cuyo `"type"` sea `"group"` o `"supergroup"`. El id
de un grupo es **negativo**, ej: `-1001234567890`.)

> 📸 *Sacar acá una captura del resultado de `getUpdates` (tapando el token) para el
> entregable.*

### 2.3 — Crear el grupo donde el robot escribe la lista

1. En Telegram: **Nuevo grupo**. Agregá al bot como integrante (Telegram pide al menos
   uno) y a quien tenga que recibir la lista.
2. Anotá el **nombre exacto** del grupo, con mayúsculas, tildes y espacios. El robot lo
   escribe en el buscador de Telegram Web para encontrarlo.

---

## Paso 3 — Configurar el proyecto

1. En la carpeta raíz del proyecto vas a encontrar `config.ejemplo.txt`.
   **Copialo y renombrá la copia como `config.txt`**, en la misma carpeta.

   ```bash
   # Linux / macOS
   cp config.ejemplo.txt config.txt
   ```
   ```
   rem Windows
   copy config.ejemplo.txt config.txt
   ```

2. Abrí `config.txt` con cualquier editor de texto y completá tus datos:
   ```
   TELEGRAM_TOKEN=1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TELEGRAM_CHAT_ID=1234567890
   GRUPO_TELEGRAM=Lista de Compras
   ```
   Sin espacios alrededor del `=` y sin comillas.

> **Por qué `config.txt` está separado del código:** las credenciales del bot no se
> suben al repositorio (`config.txt` está en `.gitignore`). Así cada integrante del
> grupo usa su propio bot sin pisarle la configuración a los demás, y el token no queda
> guardado para siempre en el historial de git.

---

## Paso 4 — Verificar el token

Parado en la carpeta `Ejecutables`, corré la prueba de conexión.
**Esta prueba no le manda un mensaje a nadie**, solo comprueba que el token sirva:

```
py prueba_conexion.py
```
(en Linux: `python3 prueba_conexion.py`)

Tiene que responder algo así:

```
OK - el token es válido. Bot: @ComprasGrupo13_bot
```

---

## Paso 5 — Iniciar sesión en Telegram Web (una sola vez)

El robot escribe desde **tu cuenta de Telegram**, usando Telegram Web en un Chrome
propio de TagUI (separado de tu Chrome de todos los días). Hay que iniciar sesión una vez:

1. Parado en `Ejecutables`:
   ```
   py robot_telegram_web.py
   ```
2. **La primera vez descarga TagUI (~200 MB)**: tarda unos minutos y no muestra progreso.
3. Se abre Chrome con Telegram Web y un **código QR**. Escanealo con el celular:
   Telegram → Ajustes → Dispositivos → Vincular dispositivo.
4. En la terminal tiene que aparecer `OK - hay sesión iniciada en Telegram Web.`

La sesión queda guardada: las próximas veces entra directo.

> **Si Chrome se abre y no pasa nada:** cortá con `Ctrl+C` y corré el comando de nuevo.
> Pasa la primera vez: al estrenar el perfil, Chrome le cierra a TagUI la pestaña que
> iba a manejar.

Para probar un envío real sin molestar a nadie, mandate un mensaje a vos mismo:

```
py robot_telegram_web.py "Saved Messages"
```

(Si tu Telegram Web está en castellano, el chat se llama `"Mensajes guardados"`.)
Si te llega un mensaje de 3 líneas a tus mensajes guardados, la instalación está
terminada.

> 📸 *Sacar acá una captura del robot escribiendo en Telegram Web para el entregable.*

---

## Errores comunes en la instalación

| Qué ves | Qué pasa |
|---|---|
| `py` / `python` no se reconoce como comando | Python no quedó en el PATH. Reinstalalo tildando "Add python.exe to PATH" y abrí una terminal nueva. |
| `No module named 'rpa'` o `'requests'` | Faltó el `pip install -r requirements.txt` del Paso 1. |
| `No existe config.txt` / `Faltan valores en config.txt` | Falta el Paso 3, o `config.txt` no tiene alguna de las 3 líneas. |
| `Unauthorized` en la prueba de conexión | El token de `config.txt` está mal copiado, o lo revocaste en BotFather. Copialo entero, incluyendo la parte antes de los dos puntos. |
| Chrome se abre y no pasa nada | Ver el recuadro del Paso 5: `Ctrl+C` y correrlo de nuevo. |
| Telegram Web queda en blanco | La PC estaba bloqueada. Con la sesión de Windows bloqueada, Chrome no dibuja las páginas. |
| `no encontré el chat «...»` | El nombre del chat no coincide exacto, o no es un chat tuyo. Por seguridad, el robot solo elige entre tus chats: nunca entre los resultados de la búsqueda global. |
| (Linux) errores raros de PHP | Falta instalar `php-cli`. Ver el Paso 1. |
| (Linux) `externally-managed-environment` al instalar | Ver el Paso 1: agregar `--user --break-system-packages` al `pip install`. |
| (Linux) `Permission denied` al correr `iniciar_bot.sh` | El archivo perdió el permiso de ejecución. Corré `chmod +x Ejecutables/iniciar_bot.sh`, o prendelo con `sh Ejecutables/iniciar_bot.sh`. |

# Instructivo de Instalación - Bot Cursos Telegram (RPA)

## 1. Requisitos del sistema
- Windows 10/11
- Google Chrome instalado (recomendado)
- Python 3.x instalado y accesible desde PATH (`python --version`)
- Java JRE/JDK 64-bit.

## 2. Instalación de TagUI v6.114
1. Descargar TagUI v6.114 (versión utilizada en el proyecto).
2. Descomprimir en `C:\tagui\` (ruta recomendada). Verificar que `C:\tagui\src\tagui.cmd` exista.
3. Incorporar `C:\tagui\src` a la variable de entorno PATH del sistema (opcional) para permitir la invocación global del binario tagui.

## 3. Aprovisionamiento y Clonación del Repositorio
Para garantizar la integridad del código fuente, el entorno debe aprovisionarse mediante la clonación del repositorio central alojado en GitHub hacia el almacenamiento local.

## 4. Configuración inicial
1. Abrir Telegram Web A (`https://web.telegram.org/a/`) en Chrome y dejar la sesión iniciada. TagUI abre su propia ventana de Chrome en modo automatización, pero se necesita una cuenta ya autenticada.
2. Verificar que Python lee/escribe correctamente: el script `procesar_consulta.py` calcula sus rutas absolutas desde su propia ubicación, por lo que funciona en cualquier carpeta.

## 5. Ejecución
Desde la raíz del proyecto:
```cmd
tagui src/bot_telegram.tag
```
El bot queda monitoreando la barra lateral en un ciclo infinito. Para detenerlo, cerrar la ventana de Chrome o finalizar el proceso con `Ctrl+C` en la terminal.

## 6. Verificación
- Al recibir mensajes con badge, el bot responde al **chat con el mensaje más antiguo** (FIFO por tiempo real: compara la hora visible de cada chat; si no hay hora, toma el más abajo de la barra lateral).
- Las respuestas incluyen menú, búsqueda de cursos (coincidencia directa + fuzzy) y detección de despedidas.
- Los archivos de intercambio `in.txt`, `out.txt` y `bot.log` se generan en la raíz del proyecto durante la ejecución y están ignorados por Git.
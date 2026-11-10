# Instructivo de Instalación - Bot Cursos Telegram (RPA)

## 1. Requisitos del sistema
- Windows 10/11
- Google Chrome instalado.
- Python 3.x instalado y accesible desde PATH. Verificar con `python --version` en una terminal nueva: si se abre la Microsoft Store, Python no está instalado o el acceso directo de la Store tiene prioridad en el PATH.
- **Microsoft Excel** instalado: TagUI lo usa para leer y escribir la planilla de inscripciones.
- Java **no** es necesario: TagUI solo lo usa para la automatización visual (SikuliX), que este bot no utiliza.

## 2. Instalación de TagUI v6.114
La versión 6.114 no se descarga directamente: se instala la 6.110 y se actualiza.
1. Descargar `TagUI_Windows.zip` de la versión 6.110 desde la página oficial: <https://github.com/aisingapore/TagUI/releases/tag/v6.110.0>.
2. Descomprimirlo en `C:\` con el Explorador de Windows, de modo que quede la carpeta `C:\tagui`. Verificar que exista `C:\tagui\src\tagui.cmd`.
3. Actualizar a la versión 6.114 (requiere conexión a internet):
   ```cmd
   C:\tagui\src\tagui update
   ```
4. Agregar `C:\tagui\src` a la variable de entorno PATH del usuario, para poder ejecutar `tagui` desde cualquier carpeta. Las terminales que ya estaban abiertas (incluida la de VS Code) deben cerrarse y abrirse de nuevo para tomar el cambio.

## 3. Obtención del proyecto
- **Desde el ZIP de la entrega:** descomprimir la carpeta `Bot Cursos-Telegram` en cualquier ubicación, por ejemplo `C:\RPA\Bot Cursos-Telegram`.
- **Desde GitHub:** clonar el repositorio de la materia; el proyecto está en `projects/2026/TagUI/team_4`. La versión con la inscripción estará ahí cuando la mejora se incorpore al repositorio; hasta entonces, usar el ZIP de la entrega.
  ```cmd
  git clone https://github.com/jaime-piperno/frcu-tagui.git
  ```

Verificar la estructura:
- `src/bot_telegram.tag`: flujo principal de TagUI.
- `src/flujos/`: pasos de TagUI para llamar a Python y para leer y escribir la planilla.
- `src/tagui_local.js`: funciones auxiliares de TagUI (TagUI lo incorpora automáticamente).
- `src/procesar_consulta.py`, `src/preinscripcion.py`, `src/cursos.py`, `src/texto.py`: lógica de las respuestas y de la inscripción.
- `data/cursos.csv`: oferta de cursos, con la columna `cupo`.
- `tests/`: pruebas automáticas.

## 4. Configuración inicial
1. **Cuenta de Telegram:** usar una cuenta dedicada al bot. El bot responde a **cualquier** chat con mensajes sin leer, incluidos grupos y conversaciones personales. Para probarlo hace falta una segunda cuenta que le envíe mensajes.
2. **Cupos:** cada curso tiene su cupo en la columna `cupo` de `data/cursos.csv`. Python lee el archivo en cada mensaje, así que los cambios se aplican sin reiniciar el bot.
3. **Planilla de inscripciones:** por defecto se crea en el Escritorio del usuario como `preinscripciones.xlsx`, con la hoja `Preinscripciones`. Para usar otra carpeta, modificar la línea `js carpeta_planilla = ...` al principio de `src/bot_telegram.tag`.
4. **Mostrar la planilla al registrar:** con `js mostrar_planilla_al_registrar = true` (valor por defecto), al confirmar una inscripción el bot minimiza Telegram, muestra la planilla con la fila nueva unos segundos y restaura Telegram. Con `false`, la planilla se actualiza sin mostrarse. Los tiempos de espera están en `src/flujos/registrar_en_planilla.tag` (`wait 2` antes de escribir y `wait 3` después).

## 5. Ejecución
1. **Cerrar Excel.** TagUI usa el Excel que encuentre abierto: si hay una planilla abierta, puede ocultarla o cerrarla.
2. Desde la raíz del proyecto:
   ```cmd
   tagui src\bot_telegram.tag
   ```
3. TagUI abre Chrome con un **perfil propio** (no el del usuario). Mientras la ventana está en blanco, **no tocarla**: TagUI necesita esa pestaña vacía para conectarse.
4. La primera vez, Telegram Web muestra un código QR. Escanearlo desde el celular: **Telegram → Ajustes → Dispositivos → Vincular un dispositivo de escritorio**. La sesión queda guardada para las próximas ejecuciones.
5. El bot queda monitoreando la barra lateral en un ciclo infinito. Mientras no haya mensajes nuevos, la terminal muestra «En espera: Sin mensajes pendientes».
6. Para detenerlo: `Ctrl+C` en la terminal (responder `S` si pregunta «¿Desea terminar el trabajo por lotes?»), y cerrar la ventana de Chrome y la ventana minimizada «Python Engine».

## 6. Verificación
1. **Pruebas automáticas** (no necesitan Telegram ni Excel), desde la raíz del proyecto:
   ```cmd
   python -m unittest discover tests
   ```
2. **Prueba con Telegram**, enviando desde la otra cuenta:

   | Mensaje | Respuesta esperada |
   |---|---|
   | `hola` | Menú con los cursos de `cursos.csv` |
   | `yoga` | Datos del curso y cupos disponibles |
   | `INSCRIBIRME` | Pide nombre y apellido, DNI, email y teléfono (cada dato se valida) |
   | `SÍ` (en el resumen) | Muestra la planilla con la fila nueva y confirma la inscripción con su número |
   | `CANCELAR` | Sale de la inscripción en cualquier paso |

3. En la terminal, la línea «Mensaje recibido en el chat ___» debe mostrar un número (el identificador del chat).
4. Durante la ejecución se generan en la raíz del proyecto `bot.log`, `entrada.json`, `salida.json` y `data/sesiones.json`. Están ignorados por Git (`.gitignore`) y **no deben compartirse**, porque contienen los datos de los usuarios.

## 7. Problemas frecuentes
| Problema | Causa y solución |
|---|---|
| El bot no arranca y solo aparece «[tagui] START - listening for inputs» | Esa ventana es el motor de Python y es normal. Si el bot no avanza, probablemente se tocó Chrome mientras estaba en blanco: detenerlo, cerrar Chrome y volver a ejecutarlo sin tocar la ventana. |
| `python` abre la Microsoft Store | Instalar Python 3 (agregándolo al PATH) y abrir una terminal nueva. |
| `tagui` no se reconoce como comando | Agregar `C:\tagui\src` al PATH y abrir una terminal nueva, o ejecutar `C:\tagui\src\tagui src\bot_telegram.tag`. |
| La planilla queda detrás de Telegram | Verificar que `mostrar_planilla_al_registrar` esté en `true` y que el bot se haya reiniciado después de cualquier cambio en los archivos `.tag`. |
| Aparece un libro nuevo («Libro1», «Libro2») o la planilla se cierra sola | Había un Excel abierto mientras corría el bot. Cerrarlo y volver a ejecutar el bot. |

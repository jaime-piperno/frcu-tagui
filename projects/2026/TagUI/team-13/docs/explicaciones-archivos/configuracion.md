# IDEA GENERAL #
configuracion.py es el archivo que lee *config.txt* y devuelve sus valores para que los usen los demás archivos. Es chico, pero es importante: sin él, el bot no sabe cuál es su token, a qué chat tiene que hacerle caso ni a qué grupo mandarle la lista.

config.txt no se sube al repositorio (está en el *.gitignore*) porque tiene el token del bot, que es como su contraseña. Cada integrante se arma el suyo copiando *config.ejemplo.txt* y completándolo con sus datos:

TELEGRAM_TOKEN=1234567890:AAxxxxxxxx
TELEGRAM_CHAT_ID=1234567890
GRUPO_TELEGRAM=Lista de Compras

Lo usan dos archivos: *bot.py*, que necesita los tres valores, y *prueba_conexion.py*, que solo necesita el token. La lectura está escrita una sola vez acá y los demás la importan con *from configuracion import leer_config*.

# BLOQUE 1 - RUTAS Y CLAVES #
**rutas**
*RAIZ* es la carpeta raíz del proyecto. Como configuracion.py está dentro de Ejecutables/, el primer *.parent* da Ejecutables/ y el segundo sube a la raíz. *ARCHIVO_CONFIG* es la ruta completa de config.txt. Gracias a esto encuentra el archivo aunque ejecutemos el programa desde otra carpeta.

**CLAVES_OBLIGATORIAS**
Es la lista de los tres valores que tienen que estar sí o sí en config.txt: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID y GRUPO_TELEGRAM.

# BLOQUE 2 - LEER LA CONFIGURACIÓN #
**leer_config(obligatorias=CLAVES_OBLIGATORIAS)**
Es la única función del archivo. Lee config.txt y devuelve un diccionario, por ejemplo {"TELEGRAM_TOKEN": "123...", "TELEGRAM_CHAT_ID": "123...", "GRUPO_TELEGRAM": "Lista de Compras"}.

El parámetro *obligatorias* dice qué claves tienen que estar. Por defecto son las tres, pero se puede pedir menos: por ejemplo *prueba_conexion.py* llama a *leer_config(obligatorias=["TELEGRAM_TOKEN"])* porque solo necesita el token.

Paso a paso:
1. *Verifica que exista config.txt.* Si no existe, corta el programa con un mensaje que explica qué hacer: copiar config.ejemplo.txt como config.txt. Usa *SystemExit* en vez de un error común para que el usuario vea solo el mensaje y no un error largo de Python.
2. *Lee el archivo línea por línea.* Usa *encoding="utf-8-sig"* por la misma razón que en compras.py: si el archivo se guardó con el Bloc de notas o con Excel, puede tener al principio un carácter invisible (BOM), y con -sig Python lo saca.
3. *Saltea las líneas que no sirven.* Las que empiezan con # son comentarios (config.ejemplo.txt tiene varias con instrucciones), y las que no tienen = no son valores.
4. *Separa clave y valor.* *linea.split("=", 1)* corta solo en el primer =. Esto es importante porque el valor podría tener otro = adentro, y así no se rompe. Con *strip()* saca los espacios sobrantes, entonces "TELEGRAM_TOKEN = 123" también funciona.
5. *Verifica que no falte nada.* Arma la lista *faltantes* con las claves obligatorias que no están o que están vacías. Si falta alguna, corta con un mensaje que dice cuáles faltan.
6. *Devuelve el diccionario* con todos los valores.

# POR QUÉ ESTÁ SEPARADO EN SU PROPIO ARCHIVO #
Como lo usan dos archivos, si la lectura estuviera escrita dentro de cada uno habría que mantenerla dos veces. Así, si mañana se agrega una clave nueva a config.txt, se cambia en un solo lugar.

Además, que los datos estén en config.txt y no dentro del código permite que cada integrante del grupo use su propio bot sin pisarle la configuración a los demás, y que el token nunca quede guardado en el historial de git.

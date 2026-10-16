# IDEA GENERAL #
robot_telegram_web.py es LA PARTE RPA del proyecto. Es el robot que hace lo que haría una persona: abre Chrome, entra a Telegram Web, busca el grupo por su nombre, pega la lista y la envía. Al final saca una captura como comprobante.

Usa la librería *rpa* (RPA for Python), que por dentro maneja TagUI. La primera vez que se usa, descarga TagUI sola (unos 200 MB) con su propio Chrome, separado del Chrome de todos los días. Todas las funciones de la librería se llaman con *r.* adelante (*r.click*, *r.type*, etc.) porque la importamos como *import rpa as r*.

Algo importante: el mensaje sale desde la cuenta de Telegram de la persona que inició sesión en ese Chrome, no desde el bot. El bot solo recibe el pedido y avisa cómo salió.

El archivo se puede usar de dos formas:
1. *Lo llama bot.py* como un programa aparte (modo --enviar), cada vez que hay que mandar una lista.
2. *Lo corremos a mano* para iniciar sesión en Telegram Web la primera vez (escaneando el QR) o para probar un envío.

Para que funcione, la PC tiene que estar desbloqueada. Con la sesión de Windows bloqueada, Chrome deja de dibujar las páginas y el robot no encuentra nada, igual que le pasaría a una persona que no ve la pantalla.

# BLOQUE 1 - IMPORTS Y CONSTANTES #
**imports**
1. *os*: para ejecutar el script que cierra los procesos de TagUI si quedaron colgados.
2. *platform*: para saber si estamos en Windows o en Linux, porque TagUI se instala en carpetas distintas en cada uno.
3. *sys*: para leer los parámetros con los que se ejecutó el archivo y para escribir los errores.
4. *urllib.parse*: para codificar el mensaje antes de pegarlo (se explica en *_pegar_mensaje*).
5. *Path*: para el manejo de rutas.
6. *rpa*: la librería que maneja TagUI.

**CAPTURA**
Es la ruta donde se guarda la captura de pantalla: captura.png, en la raíz del proyecto. bot.py la lee de acá para mandarla por Telegram.

**LOS SELECTORES**
Todo lo que depende del diseño de la página de Telegram está junto arriba de todo, a propósito. Si Telegram cambia su web y el robot deja de encontrar algo, se corrige en este lugar y en ningún otro.
Los selectores están escritos en *XPath*, que es una forma de describir dónde está un elemento dentro de la página. Por ejemplo *//input[@id="telegram-search-input"]* significa "el campo de texto cuyo id es telegram-search-input", que es el buscador.
- *URL_TELEGRAM*: la dirección de Telegram Web.
- *BUSCADOR*: el campo de búsqueda de chats.
- *CAJA_DE_MENSAJE*: donde se escribe el mensaje.
- *BOTON_ENVIAR*: el botón de enviar.
- *COLUMNA_DEL_CHAT*: la parte de la pantalla con el chat abierto. La captura se recorta a esto para no mostrar la lista de chats de la persona (nombres de contactos y vistas previas de otros mensajes).

**MAYUSCULAS / MINUSCULAS**
Son dos textos con el abecedario, incluyendo tildes y ñ. Se usan para comparar nombres sin importar mayúsculas, porque XPath no tiene una función para pasar a minúsculas y hay que hacerlo con *translate*, letra por letra.

# BLOQUE 2 - BUSCAR EL CHAT CORRECTO #
**_resultado_de_busqueda(nombre_chat)**
Arma el selector del resultado de búsqueda que coincide con el nombre del grupo. Es una de las partes más importantes de seguridad del robot.

Cuando buscás algo en Telegram, aparecen dos secciones: tus chats ("Chats and Contacts") y la búsqueda global, con canales y bots públicos de desconocidos que pueden llamarse igual que tu grupo. Cuando lo probamos, al buscar "Mensajes guardados" aparecieron canales públicos con ese nombre. Si el robot eligiera uno de esos, le mandaría la lista a un extraño.
Por eso el selector solo acepta resultados de una sección cuyo título NO diga "global". Además compara el nombre sin importar mayúsculas ("lista de compras" es lo mismo que "Lista de Compras") y sin espacios de más.

**class ErrorDelRobot**
Es un tipo de error propio, igual que *ErrorDeDatos* en compras.py. Sirve para distinguir cuando el robot no pudo completar un paso en Telegram Web (no hay sesión, no encuentra el grupo, etc.). bot.py atrapa este error y activa el plan B.

# BLOQUE 3 - LOS PASOS DEL ROBOT #
**_esperar(elemento, segundos)**
Se fija una vez por segundo si el elemento ya apareció en la página, hasta que pase el tiempo indicado. Devuelve True si apareció y False si no.
La hicimos a mano con *r.present()* (que mira una sola vez) porque la espera que trae la librería (*exist()*) no resultó confiable en las pruebas: decía que algo no estaba aunque la página ya había cargado.

**_abrir_telegram(segundos_para_iniciar_sesion)**
Abre Telegram Web y espera hasta 15 segundos a que aparezca el buscador. Si aparece, significa que hay sesión iniciada: espera 3 segundos más para que terminen de cargar los chats y sigue.
Si no aparece, es porque no hay sesión: muestra en la terminal que hay que escanear el QR con el celular (Telegram > Ajustes > Dispositivos > Vincular dispositivo) y espera el tiempo que le pasamos. Si en ese tiempo no se inició sesión, lanza *ErrorDelRobot*.
Cuando lo llama el bot, el tiempo es corto (20 segundos), porque no hay nadie mirando para escanear. Cuando lo corremos a mano, son 3 minutos.

**_renglones(texto)**
Separa un texto en renglones y descarta los vacíos. Se usa para comparar la lista que queríamos pegar con la que quedó escrita.

**_abrir_chat(nombre_chat)**
Busca el grupo y lo abre, en dos partes:
1. *Buscar:* hace click en el buscador, borra lo que hubiera (*[clear]*) y escribe el nombre del grupo. Espera hasta 8 segundos a que aparezca el resultado. Lo intenta hasta 3 veces, porque Telegram Web a veces redibuja el panel mientras termina de cargar y se pierde lo tipeado. Si en los 3 intentos no aparece, lanza un error que dice que revisemos el nombre en config.txt.
El *for ... else* es una estructura de Python: el *else* se ejecuta solo si el for terminó sin hacer *break*, o sea si ningún intento funcionó.
2. *Abrir:* espera 1 segundo a que termine la animación de la lista y hace click en el resultado. Después espera a que aparezca la caja de mensaje. Lo intenta 2 veces. Si no aparece, puede ser que la cuenta no tenga permiso para escribir en ese grupo.

**_pegar_mensaje(mensaje)**
Pega la lista en la caja de mensaje. Este fue uno de los contratiempos del proyecto: TagUI convierte cada salto de línea en la tecla Enter, y en Telegram Enter envía. Si escribíamos la lista letra por letra, salía un mensaje por cada renglón (14 mensajes).
La solución fue *pegarla* entera, como haría una persona con Ctrl+V. Para eso usamos *r.dom()*, que ejecuta un pedacito de JavaScript dentro de la página: pone el foco en la caja e inserta el texto de una sola vez.
Antes de pegarlo, el mensaje se codifica con *urllib.parse.quote* (los espacios pasan a ser %20, los saltos de línea %0A, etc.) y dentro de la página se decodifica. Así ningún carácter (tildes, ñ, comillas) se rompe en el camino de Python a TagUI y a Chrome.
Al final lee lo que quedó escrito en la caja y lo compara renglón por renglón con la lista original. Si no coincide, lanza un error. Es uno de los controles del proceso: el robot no da por hecho que pegó bien, lo verifica.

**_enviar()**
Hace click en el botón de enviar y verifica que el mensaje salió: cuando un mensaje se envía, la caja de mensaje queda vacía. Revisa una vez por segundo durante 10 segundos. Si la caja nunca se vacía, lanza un error.

**_escribir_y_enviar(mensaje)**
Junta los dos pasos anteriores: pega y envía. Después espera 2 segundos para que la captura muestre el mensaje ya enviado.

**_sacar_captura()**
Saca la captura recortada a la columna del chat y la guarda en captura.png. Si no encuentra la columna, no saca nada: preferimos no mandar foto antes que mandar la pantalla entera con los chats de la persona. El bot confirma igual, solo que sin foto.

# BLOQUE 4 - LAS FUNCIONES PRINCIPALES #
**enviar_por_telegram_web(nombre_chat, mensaje, segundos_para_iniciar_sesion=20)**
Es la función que hace todo el trabajo cuando la llama el bot. Arranca TagUI con *r.init()* (si no puede, lanza error), y después en orden: abre Telegram, abre el chat, escribe y envía, saca la captura y devuelve la ruta de la captura.
Todo está dentro de un *try / finally*: el *finally* se ejecuta siempre, salga bien o mal, y ahí se cierra TagUI con *r.close()*. Así nunca queda un Chrome abierto colgado.

**_iniciar_sesion_y_probar(nombre_chat=None)**
Es la función que se usa cuando corremos el archivo a mano. Abre Telegram Web con 3 minutos de espera para escanear el QR, y si hay sesión muestra *OK - hay sesión iniciada en Telegram Web.*
Si le pasamos el nombre de un chat, además manda un mensaje de prueba de 3 renglones. Conviene probar con "Saved Messages" ("Mensajes guardados" si Telegram Web está en castellano), que es un chat con uno mismo y no molesta a nadie. Si algo falla, muestra el motivo en vez de un error largo.

**terminar_procesos_tagui()**
Cierra TagUI y su Chrome si quedaron colgados. La usa bot.py cuando el robot tarda más de 3 minutos y hay que cortarlo. Ejecuta un script que trae el propio TagUI (*end_processes*), que está en una carpeta distinta según el sistema: *tagui* en Windows y *.tagui* en Linux. Por eso se usa *platform*.

# BLOQUE 5 - CÓMO SE EJECUTA #
**if __name__ == "__main__":**
Esta parte decide qué hacer según cómo se ejecutó el archivo:

1. *py robot_telegram_web.py --enviar "Lista de Compras"*: es el modo que usa bot.py. El nombre del chat viene como parámetro y el mensaje llega por la *entrada estándar* (stdin), que es como bot.py le pasa el texto al otro programa. Se configura en UTF-8 para que las tildes y la ñ lleguen bien. Si el robot falla, escribe el motivo en la *salida de errores* (stderr) y termina con código 2. bot.py lee ese código y ese mensaje para saber que falló y por qué.
2. *py robot_telegram_web.py*: abre Telegram Web y verifica que haya sesión (si no, muestra el QR).
3. *py robot_telegram_web.py "Saved Messages"*: igual que el anterior, pero además manda un mensaje de prueba a ese chat.

**¿Por qué bot.py lo ejecuta como otro programa y no llama directamente a la función?**
Por el tiempo máximo. Si Chrome o TagUI se cuelgan (por ejemplo, con la PC bloqueada), una función normal dejaría al bot trabado para siempre. Como es otro programa, bot.py lo puede cortar a los 3 minutos, cerrar TagUI con *terminar_procesos_tagui* y seguir atendiendo.

# EJEMPLO DE RECORRIDO #
1. bot.py ejecuta *robot_telegram_web.py --enviar "Lista de Compras"* y le pasa la lista.
2. *r.init()* arranca TagUI y abre su Chrome.
3. *_abrir_telegram* entra a Telegram Web y ve que el buscador aparece: hay sesión.
4. *_abrir_chat* escribe "Lista de Compras" en el buscador, encuentra el grupo entre los chats propios y lo abre.
5. *_pegar_mensaje* pega la lista y verifica que quedó igual.
6. *_enviar* toca enviar y espera a que la caja quede vacía.
7. *_sacar_captura* guarda captura.png recortada al chat.
8. *r.close()* cierra TagUI, y bot.py le manda la captura al usuario con "Lista enviada".

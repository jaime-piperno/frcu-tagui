# IDEA GENERAL
La idea general es que es un bot de telegram que corre en nuestra pc, queda esperando mensajes y cada cierto tiempo hace consulta mediante la API de telegram para ver si hay un mensaje nuevo.

# BLOQUE 1 - IMPORTS Y CONFIGS #
En la primer parte podemos ver que tenemos ciertos imports, la idea es que utilizamos:
1. *Random*: para sortear un menú semanal al azar.
2. *subprocess*: para correr el robot como otro programa parte.
3. *sys*: esto lo usamos por que al momento de ejecutar el iniciar_bot esta corriendo ese archivo python, entonces con esto tenemos la misma ruta.
4. *time*: lo usamos para el time.sleep para cuando no hay internet o se corta.
5. *path*: Esto lo usamos para el manejo de rutas de archivos mas facilmente.
6. *request*: esto es para hacer llamadas HTTP a la Api de Telgram.
7. *compras*: este es el otro archivo donde trabajamos con las recetas, stock y calculos.
8. *robot_telegram_web*: este es el modulo que maneja la parte de RPA donde se abre chrome y todo eso.

**CONSTANTES GLOBALES**
En esta siguiente parte traemos todo del archivo de configuracion, la idea es que este se modifica segun el usuario ya que no todos tenemos el mismo bot, entonces segun el usuario este tiene que cambiar estos datos para que el robot funcione, osea el telegramid, token y demas.
El Robot = Path lo que hace es que el bot puedan encontrar esta carpeta por mas que lo ejecutemos desde otra.

**ESTADO EN MEMORIA**
Vemos que definimos menu = {}, el proposito de esto es un diccionario que guarda el chat y el mensaje del mismo entonces se guarda el estado en el que esta el chat, en caso de que se reinicie, como esta en memoria, se borraria.

# BLOQUE 2 - LLAMADAS A LA BOT API #
Esta capa es la que hace la base de comunicacion con telegram. El primer metodo es el *llamar*, esta es la funcion base, todas las demas la usan.

**llamar(metodo, archivos=None, **datos)**
el *metodo* es el nombre del metodo de la API que se utiliza para *sendMessage*,*editMessageText*,etc.
Dentro de esto tambien tenemos el  **datos, el cual junta todo lo que se mande de informacion, EJ:
*llamar("sendMessage", chat_id=1, text="hola") hace datos = {"chat_id": 1, "text": "hola"}*
En caso de que tengamos algun archivo, como una foto, manda la peticion como formulario(data=files=).Sino, lo manda como JSON.
Si telegram responde *"ok":false*, imprime el motivo en consola pero no corta el programa, dando continuidad.

**responder(chat_id, texto, botones=None)**
esta funcion se usa para mandar un mensaje nuevo, si les pasamos botones los agrega como inline_keyboard que son los botones que aparecen pegados abajo del mensaje.

**editar(chat_id, message_id, texto, botones=None)**
este modifica un mensaje que ya existe, por eso podemos ver la navegacion entre pantallas, no se manda un mensaje nuevo por cada toque, se reescribe el mensaje, en caso de no pasarle botones pone [] y los botones desaparecen.

**mandar_foto(chat_id, ruta, texto)**
esto se usa para poder capturar la pantalla final, se abre la imagen en modo binario y se la manda con el sendPhoto del API metodo.

# BLOQUE 3 - CONSTRUCCION DE MENUS Y TEXTO #
Estas funciones en si no mandan nada, solo arman botones y texto para desacoplar y separar funcionalidades, los cuales seran enviados en ciertos momentos determinados. Lo que dice *text* es lo que va a ver el usuario, lo que dice *callback_data* es lo que le llega al bot cuando se toca el boton.
La estructura que usamos es una lista de filas donde cada fila es una lista de botones

**botones principales()**
Esta devuelve el menu inicial.

**botones_de_comidas**
Esta funcion es la que se llama para generar un boton por comida, vemos que le cargamos prefijos, eso es por que al momento de generar los botones tenemos todos esos que son distintas formas de escribir o de accionar.
Usamos el numero de comida como el indice debido a que telegram limita los callback a 64 bytes.
En el caso de que queramos seleccionar varias comidas agrega el boton de *listo* y el de *borrar*, ademas de que siempre esta el boton de *volver* el cual vuelve  a la pagina anterior en la que estaba.

**resumen**
esta funcion se usa mas que nada para cuando seleccionamos varias y por ejemplo elegimos 2 veces asado, en vez de que aparezca como [asado, asado] aparece como [asado x2]. El dict ahi lo que hace es que saca los repetidos pero mantiene el orden.

**texto_varias**
Esto arma el texto de la pantalla varias comidas con lo que se eligio hasta el momento.

**texto_semana** 
Esto arma el texto del menú semanal. Si una comida del menu no tiene receta, le agrega *sin receta* que es la perturbacio exogena que marcamos ahi.

**texto_receta** 
Esto lo que hace es armar el texto con los ingredientes de una comida con nombre, cantidad y unidad lo cual lo busca con la funcion *ingredientes_de* definida en compras.

**abrir_menu**
Esta funcion abre el menu principal que vemos cuando mandamos start. Ademas guarda el estado del menu y responde segun lo que se elija.

# BLOQUE 4 - LOGICA MENU #
**atender_boton**
Esta funcion es la que responde en base a los mensajes que se toquen en el menu principal actualizando el estado de lo que se ve y respondiendo en base a lo que se elija.

Esta funcion se ejecuta cada vez que alguien toca un boton donde telegram manda un callback_query con los datos de la consulta, nosotros mandamos mediante el metodo llamar un mensaje a telegram para avisarle que nos llego. 

Luego de aca primero tenemos los casos especiales como carga donde se llama a ciertos metodos ya que no pertenecen a menu, osea si queremos ver la alacena o cargar una receta.

Luego tenemos todos los if con los elif segun el dato. Primero verificamos que tengamos el menu activo, sino pedimos un start de nuevo.

Una cosa importante es que en los sorteo de los menus semanal, si los dias son mayores a los elementos, usamos sample pero si hay menos usamos choise asi puede repetir.

# BLOQUE 5 - CARGAR UNA NUEVA RECETA #
Primero definimos cargas que es donde vamos a guardar lo que vamos a cargar, Luego definimos las instrucciones que se dan cuando le vamos a decir a una persona como cargar los ingredientes de la nueva receta.

**botones_carga**
Esto devuelve los botones de guardar o cancelar que se utilizan cuando cargamos una receta

**empezar_carga**
El .pop lo que hace es que cancelemos una edicion de alacena si habia una, osea se hace una a la vez, la idea del none es evitar el error si no existia, luego con el estado vacio pregunta el nombre en el editar mensaje.

**atender_texto_de_carga**
Este es el que se utiliza para cuando estamos escribiendo algo al mismo tiempo que cargamos una receta.
Basicamente primero lo que se escriba se toma como nombre sin espacios y verifica si ya existe para de ultima pedir otro.
Luego empieza a pedir los ingrediente y manda las intrucciones que definimos arriba
Ahora entra en el for en el cual la persona empieza a cargar los ingredientes y va guardando los problemas para no cortar la carga, luego los muestra a todos.

**atender_boton_de_carga**
esto lo que hace es ir atendiendo los botones que se tocan, segun si tiene todavia el estado, si la persona toca cargar, si no cargo ingredientes, cosas asi. En caso de que tengamos ingredientes lo que hace es que trata de guardarlos y si no hay error, ejecutamos el else y avisa que se guardo.

# BLOQUE 6 - MI ALACENA #
Se utiliza la misma logica para cargar pero en este caso para el stock *alacenas_en_edicion = {chat_id: message_id_del_último_resumen}*.

**texto_alacena**
Lista lo que tengamos en stock o vacio en caso de que nada.

**empezar_edicion_alacena**
Cancela una carga de receta si habia una, marca el chat como "editado" y explica el formato.

**atender_texto_de_alacena**
Esta funcion atiende los mensajes durante el proceso de edicion de la alacena, interpreta cada renglon para saber que si es 0 tiene que sacarlo, guarda en el momento para guardar el estado y no esperar al listo.
Ademas verifica  si tipeaste mal o cosas asi y quita lo sbotones del resumen anterior y manda uno nuevo, osea de lo que cargaste hasta el momento.

**terminar_edicion_alacena**
Esta funcion verifica que sea el ultimo resumen, borra el estado y confirma la carga.

# BLOQUE 7 - PROCESO PRINCIPAL [CALCULAR Y ENVIAR] #
**ejecutar_robot**
Este proceso es la parte mas tecnica, corre el bot como un proceso separado evitando que se cuelgue.

En el primer try vemos que usamos el proceso aparte y no llamamos a una funcion directamente por el timeout, si chrome por ejemplo se cuelga, supongamos que bloqueamos la pc, una funcion normal dejaria el bot trabado, con *subprocess* se puede cortar luego de cierto tiempo.

Antes de correr lo que hace es que borra la captura vieja para no mandar una foto anterior, si se pasa del tiempo mata los procesos en caso de que el robot termine con error toma la ultima linea de lo que hizo que suele ser el mensaje del error y devuelve un ErrorDelRobot. Si sale bien, devuelve la ruta de la captura.

**cerrar_menu_y_procesa**
esta función cierra el menú de botones y procesa las comidas seleccionadas, calculando la lista de compras, guardando la evidencia y ejecutando el robot para enviar la lista al grupo de Telegram. 

Primero borra el menu de menus, osea que ya se usom luego edita el mensaje mediante la funcion resumen y la editar.
Hace un try para comprobar errores de datos o faltantes., en caso de que tengamos, lo muestra, en caso de que no tengamos nada, avisa y termina.

Luego arma el mensaje y guarda la evidencia en un archivo, avisa que abre telegram y ejecuta el bot.
En caso de que falla, hay un plan B que es que el robot manda por la API el mensaje asi no se pierde pero avisa del error en un comentario.

En caso de que pudo enviarlo avisa de que se envio y adjunta la captura de lo mismo.

# BLOQUE 8 - BUCLE PRINCIPAL #
**descargar_pendientes**
Nosotros podemos enviar mensajes al bot mientras esta 
apagado, lo cual puede causar problema si no se eliminan, esta funcion resuelve eso, al prender ignora los mensajes que llegaron mientas estaba apagado, mediente el *offset=-1* le pide la ultima actualizacion a telegram y devuelve *update_id + 1* para empezar a leer desde ahi.

**es_el_chat_permitido**
Esto es mas que nada de seguridad, solo acepta mensajes del chat que este configurado y puede venir de 2 formas, de mensaje de texto o de boton, por eso usa or, para cubrir ambos casos.

**atender**
esta funcion es la que administra/distribuye los eventos que vimos antes, primero verifica si es el chat permitido, si es un boton acciona el *atender_boton*, si es texto, extra el comando y lo convierte del estar con el @ del bot a el /start.

Si llega un start, menu o cancelar borra cualquier edicion amedias y abre el menu. Si hay una carga en curso el texto va a *atender_texto_de_carga*, si hay una edicion de alacena el texto va a *atender_texto_de_alacena* y sino ignora.

**main**
este es el punto de entrada del programa, verifica el token del bot, descarta los pedidos pendientes y entra en un bucle para recibir actualizaciones de telegram.

*get me* verifica que el token sea valido, si no es sale error. Luego descarta los pendientes y ahi entra en el bucle infinito de *long polling*, donde cada cierto tiempo se puede un update, se pregunta a telegram, hay alguno nuevo desde siguiente?, telegram retiene la respuesta hasta 30 segundos esperando a que llegue algo. El timeout es para darle mas margen a telegram.

offset=siguiente confirma a telegram que ya procesaste lo anterior, asi no vuelve a mandar. Si se corta internet espera 5 segundos y reintenta.

Cada actualizacion se atiende dentro de un try/except Exception, si un pedido falla, el bot sigue funcionando.

if __name__ == "__main__": solo se ejecuta si se corre el archivo directamente, sino, no importa. El Keyboardnterrupt es para el ctrl + c.

# EJEMPLO DE RECORRIDO #
1. Escribís /start → main lo recibe → atender → abrir_menu → aparece el menú y se guarda en menus.
2. Tocás "🛒 Varias comidas" → atender_boton con dato="modo:varias" → se edita el mensaje con la lista de comidas.
3. Tocás "Asado" dos veces → sumar:0 dos veces → elegidas = ["Asado", "Asado"].
4. Tocás "✅ Listo" → cerrar_menu_y_procesar(["Asado", "Asado"]).
5. compras.calcular_lista → faltan 2 kg de carne → armar_mensaje → ejecutar_robot.
6. El robot abre Chrome, escribe en el grupo y saca una captura → el bot te la manda con "✅ Lista enviada".

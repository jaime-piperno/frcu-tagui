# IDEA GENERAL #
Bot.py es la parte que habla con el usuario, el compras.py es la parte que piensa y maneja los datos, no sabe nada de telegram ni chrome, solo lee y escribe los CSV y hace cuentas.

Trabaja con los archivos de la carpeta data, como La base de datos que tiene las recetas, el stock y el menu semanal. Si analizamos cada CSV vemos que la primer fila tiene encabezado de como se escriben las cosas, por eso el codigo saltea al leer.

# BLOQUE 1 - CONFIGURACION Y UTILIDADES INTERNAS #
**imports**
en este caso importamos csv para leer y escribir en los archivos, math para redondear, unicodedata para sacar tildes y path para manejar rutas.

**rutas**
Primero asignamos las rutas de los archivos, tanto del raiz como de la carpeta de datos.

**class ErrorDeDatos**
es un tipo de error, no agrega nada nuevo, hereda de *exception*, sirve para poder distinguir errores de datos del resto de errores. Asi en bot.py, un error como *la cantidad dos es un numero*, se le muestra al usuario, en cambio un error de programacion (un bug) no se tiene en cuenta aca y termina en la consola.

**_leer_csv**
es la funcion base para la lectura. Todas las demas funciones que leen datos utilizan esta. La idea del _ al inicio es para decir que es una funcion interna, por eso bot.py nunca llama a esta funcion.

*newline* se usa esto por que el modulo de csv pide esto para manejar mejor los saltos de linea.
*[1:]* saltea el encabezado
*if any (fila)* descarta las filas vacias
*campo.strip* saca espacios sobrantes

Esto devuelve una lista de listas de textos:
[["Milanesas con pure", "Carne nalga", "0.5", "kg"],
 ["Milanesas con pure", "Papa", "1", "kg"], ...]
Vemos que aca el 0.5 sigue siendo numero, para eso esta la proxima funcion.

**_a_numero**
Convierte texto a número (float). Si no puede, por ejemplo con "medio" o "0,5", lanza ErrorDeDatos con un mensaje que dice en qué archivo y en qué fila está el problema. Recibe el archivo y la fila solo para armar ese mensaje.

# BLOQUE 2 - CONSULTAS SIMPLES #
Son funciones de lectura que usa el bot para armar los menus

**comidas_disponibles**
Recorre BaseDatos.csv y junta los nombres de comida sin repetir, en el orden del archivo. Como cada comida ocupa varias filas (una por ingrediente), hay que evitar los duplicados.
Usa una lista con if not in en vez de un set porque el orden importa: los índices de esta lista son los números de los botones del bot (sumar:0, sumar:1…)

**comidas_del_menu**
Devuelve solo las comidas de Menu.csv (la columna 1): ["Bife con ensalada", "Choripanes", ...]. Se usa en "Comprar para la semana".

**menu_semanal**
Devuelve el menú como pares (dia, comida): [("Lunes", "Bife con ensalada"), ...]. Se usa para mostrarlo y para cambiar un día.

**guardar_menu**
Reescribe Menu.csv con los pares que le pasan

**ingredientes_de**
Devuelve los ingredientes de una comida como (ingrediente, cantidad, unidad). lo del *if len* es una protección, si alguna fila vieja no tiene la columna Unidad, asume "unidad". Este patrón se repite en todo el archivo.

# BLOQUE 3 - CARGA DE RECETAS NUEVAS #
Esta parte valida lo que escribe el usuario en telegram antes de guardarlo.

**_escribir_csv**
Es la función base de escritura. Abre el archivo en modo "w", que borra todo y lo escribe de nuevo. Primero escribe el encabezado y después todas las filas.

*lineterminator="\n"* por defecto csv usa \r\n (estilo Windows). Esto lo unifica.
Reescribir el archivo entero es más simple y seguro que "agregar al final", así no importa si el archivo original terminaba o no con un salto de línea.

**normalizar**
Es clave para comparar nombres. Convierte " Milanesas con Puré " en "milanesas con pure".
*NFKD* separa cada letra con tilde en dos caracteres: "é" pasa a ser "e" + "´" la tilde como carácter aparte, llamada "combinante"
Luego se queda con todo menos con esos caracteres combinantes y asi desaparecen los tildes.
Luego pasa a minusculas y borra los espacios.

**comida_existente**
Busca si ya existe una comida con ese nombre, comparando normalizado. Si la encuentra, la devuelve tal como está escrita en el CSV. Por eso el bot puede decir "Ya existe «Milanesas con pure»" aunque hayamos escrito "milanesas con puré". Si no la encuentra, devuelve None.

**ingredientes_conocidos**
Arma un diccionario con todos los ingredientes que ya existen en recetas y stock:
{"papa": ("Papa", "kg"), "huevo": ("Huevo", "unidad"), ...}  *↑ clave normalizada   ↑ (nombre como está escrito, unidad)*

Sirve para mantener la coherencia de los datos. Si en las recetas figura Papa en kg y alguien carga una receta nueva con papa, 500, unidad el nombre en minúscula haría que el stock no se descuente, porque "papa" ≠ "Papa" y ademas
la unidad distinta haría que la resta no tenga sentido, porque no se pueden restar unidades de kilos.

Lee primero el stock y después las recetas. Si un ingrediente está en los dos, ganan las recetas, porque la segunda escritura en el diccionario pisa a la primera.

**interpretar ingrediente**
Es la función de validación más importante. Convierte un renglón escrito por el usuario en datos limpios, o explica qué está mal.

Paso a paso con "Papa, 0,5, kg":

1. Separa por comas: ["Papa", "0", "5", "kg"], o sea 4 partes.
2. Arregla la coma decimal: si hay 4 partes, asume que la coma del medio era la de los decimales y las une: ["Papa", "0.5", "kg"]. Así funciona aunque el usuario escriba al estilo argentino.
3. Verifica el formato: tienen que ser exactamente 3 partes y ninguna vacía (all(partes) da False si alguna es "").
4. Convierte la cantidad a número. Si no puede, lanza error.
5. Verifica que sea positiva. La condición cantidad < 0 or (cantidad == 0 and not permitir_cero) significa:
    negativo: siempre es error
    cero: es error en recetas, pero en la alacena está permitido, porque ahí 0 significa "ya no tengo"
6. Verifica la unidad contra UNIDADES. Antes la pasa a minúsculas, así "KG" sirve.
7. Unifica con lo conocido: si el ingrediente ya existe, reemplaza el nombre por el oficial ("papa" pasa a ser "Papa") y exige la misma unidad.
8. Devuelve ("Papa", 0.5, "kg").

Este es un buen ejemplo de validar la entrada en el borde: después de pasar por esta función, el resto del código puede confiar en que los datos son correctos.

**agregar_receta**
Vuelve a verificar que la comida no exista. Es una doble protección, porque el bot ya lo había verificado al pedir el nombre.
Lee todas las filas actuales.
Agrega una fila por ingrediente, con la cantidad formateada (1.0 se guarda como "1").
Reescribe el archivo completo.

# BLOQUE 4 - LA ALACENA #
Esta parte maneja el archivo StockActual.csv, que es lo que hay en la casa de la persona que usa el bot. El bot no puede saber qué se compró o qué se usó, por eso la alacena la actualiza la persona desde el botón *Mi alacena*.

**stock_actual**
Devuelve lo que hay en la alacena como (ingrediente, cantidad, unidad), igual que *ingredientes_de*. Tiene la misma protección: si una fila no tiene la columna Unidad, asume "unidad".

**se_usa_en_recetas**
Devuelve True si alguna receta usa ese ingrediente, comparando normalizado. El bot la usa para avisar posibles errores de tipeo, por ejemplo si alguien carga "Papas" en vez de "Papa", porque ese stock nunca se descontaría de ninguna receta.
*any(...)* devuelve True apenas encuentra una coincidencia y no sigue recorriendo el resto.

**actualizar_stock**
Aplica los cambios que mandó el usuario. Primero pasa el stock a un diccionario donde la clave es el nombre normalizado, así si el usuario manda "huevo, 12, unidad" reemplaza la fila Huevo que ya existe en vez de agregar otra repetida.
Si la cantidad es 0, saca el ingrediente de la alacena (el *pop* con *None* es para que no falle si no estaba).
Si no, pisa el valor. Es importante que no suma: la cantidad que mandás es la que hay.
Al final reescribe el CSV entero con *stock.values()*. Como los diccionarios de Python mantienen el orden en el que se cargaron, los ingredientes que ya estaban quedan en su lugar y los nuevos van al final.

# BLOQUE 5 - CALCULAR LA LISTA (EL CORAZÓN DEL SISTEMA) #
**calcular_lista**
Esta es la lógica central del proyecto: recibe las comidas elegidas y devuelve qué hay que comprar. Devuelve dos cosas: *faltantes*, que es la lista de lo que hay que comprar, y *advertencias*, que son las comidas elegidas que no tienen receta cargada.

Lo hace en 4 fases:

*Fase 1 - preparar:* arma dos diccionarios, *necesario* (cuánto hace falta de cada ingrediente) y *unidad_de* (en qué unidad se mide cada uno). Con *setdefault(ingrediente, 0)* todos los ingredientes de todas las recetas arrancan en 0. setdefault significa "si la clave no existe, creala con 0; si ya existe, no la toques".

*Fase 2 - sumar lo necesario:* por cada comida elegida busca sus filas en las recetas y va sumando las cantidades. Como recorre la lista de elegidas, si una comida está repetida se suma dos veces, por eso "Milanesas x2" pide el doble de papa. El *enumerate(..., start=1)* es solo para saber el número de fila y usarlo en el mensaje de error.
Si una comida no se encontró en ninguna fila, va a *advertencias*. Esta es la *perturbación exógena* que marcamos en el código: el menú pide algo que no tiene receta, y el error viene de los datos de entrada, no del bot.

*Fase 3 - leer el stock:* arma el diccionario *disponible* con lo que hay en la alacena, por ejemplo {"Huevo": 6.0, "Cebolla": 2.0}. Acá está la *retroalimentación negativa*: el sistema mide el estado actual (lo que hay) antes de decidir la salida (lo que se compra).

*Fase 4 - calcular qué falta:* para cada ingrediente hace *necesario - disponible*. Si en la alacena no está, cuenta 0. Si lo que falta da 0 o menos, alcanza con lo que hay y lo saltea.
Antes de comparar redondea a 6 decimales. Esto es porque las computadoras guardan mal algunos decimales (0.1 + 0.2 da 0.30000000000000004), y sin redondear podría pedir comprar una cantidad absurda como 0.00000000000000004.
Después redondea según la unidad: lo que se mide en *unidad* se redondea para arriba con *math.ceil* (1.5 huevos pasan a ser 2), porque no se puede comprar media lechuga y redondear para abajo te dejaría corto. Lo que va en kg o lt se redondea a 2 decimales.

Ejemplo: si pedimos 2 veces "Milanesas con pure":

| Ingrediente | Por receta | x2 = Necesario | En alacena | Falta |
|---|---|---|---|---|
| Carne nalga | 0.5 kg | 1 kg | 0 | 1 kg |
| Papa | 1 kg | 2 kg | 0 | 2 kg |
| Pan rallado | 0.2 kg | 0.4 kg | 0.1 kg | 0.3 kg |
| Huevo | 2 unidad | 4 unidad | 6 | nada, alcanza |

# BLOQUE 6 - LA SALIDA #
**formatear_cantidad**
Si el número es redondo lo muestra sin decimales (1.0 pasa a ser "1"), si no, lo deja como está ("0.5"). Así la lista dice "2 kg" y no "2.0 kg". Se usa también al guardar en los CSV.

**armar_mensaje**
Arma el texto final que el robot escribe en el grupo:
Lista de compras:
- Carne nalga: 1 kg
- Papa: 2 kg

**guardar_evidencia**
Guarda la última lista en *mensaje.txt*, en la raíz del proyecto. Sirve como registro de lo que se calculó: si el robot falla, igual queda la evidencia local de que el cálculo se hizo.

# QUÉ FUNCIÓN USA BOT.PY Y DÓNDE #
| Función de compras.py | La usa bot.py en... |
|---|---|
| comidas_disponibles | los botones de comidas |
| menu_semanal, comidas_del_menu, guardar_menu | el menú de la semana |
| ingredientes_de | Ver recetas |
| comida_existente, interpretar_ingrediente, normalizar, agregar_receta, UNIDADES | Cargar receta |
| stock_actual, se_usa_en_recetas, actualizar_stock | Mi alacena |
| calcular_lista, armar_mensaje, guardar_evidencia, formatear_cantidad | cerrar_menu_y_procesar |
| ErrorDeDatos | todos los try/except |

# A TENER EN CUENTA #
*calcular_lista* compara los nombres exactos, no normalizados. Si alguien edita a mano StockActual.csv y pone "papa" en vez de "Papa", ese stock no se descuenta. Desde el bot esto no pasa, porque *interpretar_ingrediente* corrige los nombres, pero hay que tenerlo en cuenta si se editan los CSV a mano.

# Instructivo de uso

Cómo usar el bot una vez instalado. Si todavía no lo instalaste, empezá por el
[instructivo de instalación](instructivo-instalacion.md).

---

## Prender el bot

- **Windows:** doble click en `Ejecutables\iniciar_bot.cmd`
- **Linux / macOS:** `./Ejecutables/iniciar_bot.sh`

Se abre una ventana de terminal que dice:

```
Bot @ComprasGrupo13_bot escuchando. Escribile /start en Telegram. (Ctrl+C para cortar)
```

**Mientras esa ventana esté abierta, el bot atiende.** Para apagarlo, `Ctrl+C` o cerrar
la ventana.

> ⚠️ **La PC tiene que estar prendida y desbloqueada.** El robot maneja Chrome como lo
> haría una persona, y con la sesión de Windows bloqueada Chrome no dibuja las páginas.
> Tampoco toques la ventana de Chrome mientras el robot está escribiendo.

Los pedidos que se hagan con el bot apagado se descartan al prenderlo, para que no se
disparen solos.

---

## Hacer un pedido desde Telegram

En tu chat con el bot (el del `TELEGRAM_CHAT_ID` de `config.txt`), mandá `/start`.
Aparece el menú principal:

```
¿Qué querés hacer?
[ 🍽 Una comida ]  [ 🛒 Varias comidas ]
[ 📅 Menú de la semana ]
[ 📖 Ver recetas ]  [ ➕ Cargar receta ]
[ 🥫 Mi alacena ]
```

Los tres primeros botones arman una lista de compras. Los de abajo sirven para
consultar y ampliar la base de recetas, y para mantener al día lo que tenés en casa.

### 🍽 Una comida

Aparece un botón por cada comida cargada. Tocás una y listo.

### 🛒 Varias comidas

Tocás las comidas que quieras y el mensaje va mostrando lo que llevás elegido:

```
Elegidas: Milanesas con pure x2, Asado
```

**Podés tocar la misma comida más de una vez a propósito**: si elegís una comida dos
veces, las cantidades se suman, igual que cuando una comida aparece dos veces en el menú
de la semana. Cuando termines, **✅ Listo**. **🗑 Borrar** vacía la selección y
**⬅ Volver** te lleva al menú anterior.

### 📅 Menú de la semana

Muestra qué se come cada día (lo que dice `data/Menu.csv`) y te da tres opciones:

```
[ 🛒 Comprar para la semana ]
[ ✏ Cambiar un día ]  [ 🎲 Sortear otro ]
[ ⬅ Volver ]
```

- **🛒 Comprar para la semana**: calcula los ingredientes de toda la semana de una. Es
  el modo original del proyecto.
- **✏ Cambiar un día**: elegís el día y después la comida. Queda guardado en
  `Menu.csv`, así que la semana que viene sigue igual hasta que lo cambies de nuevo.
- **🎲 Sortear otro**: arma un menú nuevo al azar con las recetas cargadas, sin repetir
  comidas. Si no te gusta algún día, lo cambiás con ✏.

Si en el menú hay una comida que no tiene receta (porque alguien editó `Menu.csv` a
mano), aparece marcada con `⚠ sin receta`.

### 📖 Ver recetas

Muestra un botón por cada comida cargada. Tocás una y ves sus ingredientes con las
cantidades. Sirve, por ejemplo, para fijarte si una comida ya existe antes de cargarla.

### ➕ Cargar receta

El bot te pide dos cosas, cada una en un mensaje:

1. **El nombre de la comida.** Si ya existe una con ese nombre, te avisa y te pide
   otro. Para comparar no importan las mayúsculas, las tildes ni los espacios de más:
   `milanesas con puré` cuenta como la misma que `Milanesas con pure`.
2. **Los ingredientes**, uno por renglón, con el formato
   `Ingrediente, cantidad, unidad`:
   ```
   Pollo, 1, kg
   Huevo, 2, unidad
   Leche, 0.5, lt
   ```
   Podés mandarlos todos juntos o en varios mensajes. Después de cada mensaje, el bot
   te muestra cómo va la receta.

Cuando esté completa, tocás **✅ Guardar** y la comida se agrega a `BaseDatos.csv`.
Desde ese momento aparece en todos los botones. **❌ Cancelar** (o mandar `/cancelar`)
la descarta sin guardar nada.

El bot rechaza los renglones que no están bien y te dice por qué:

- la unidad tiene que ser `kg`, `lt` o `unidad`;
- la cantidad tiene que ser un número mayor que cero (se acepta `0.5` y también `0,5`);
- el mismo ingrediente no puede estar dos veces en la receta;
- **si el ingrediente ya existe** en otra receta o en el stock, tiene que ir en **la
  misma unidad**, porque si no, no se podría descontar del stock. El nombre se corrige
  solo: si escribís `huevo`, se guarda como `Huevo`, igual que en el resto de la base.

### 🥫 Mi alacena

Muestra lo que hay en casa según `StockActual.csv`. Con **✏ Actualizar** le mandás lo
que tenés ahora, uno por renglón, con el mismo formato que las recetas:

```
Papa, 3, kg
Huevo, 12, unidad
Leche, 0, lt
```

- La cantidad que ponés **pasa a ser la que hay**: no se suma. Si tenías 1 kg de papa
  y mandás `Papa, 3, kg`, quedan 3 kg.
- Con **`0`**, el ingrediente se saca de la alacena.
- Cada mensaje se guarda en el momento. Cuando termines, tocá **✅ Listo**.
- Tiene las mismas verificaciones que la carga de recetas (unidad válida, número, y la
  misma unidad que ese ingrediente tiene en las recetas).
- Si cargás algo que **ninguna receta usa** (por ejemplo `Papas` en vez de `Papa`), lo
  guarda igual pero te avisa, porque así no se descontaría de nada.

**El bot no actualiza la alacena solo:** no sabe qué compraste ni qué cocinaste. Lo
tiene que mantener la persona que lo usa, por ejemplo después de ir al súper.

### Qué pasa después de elegir

1. El bot calcula qué falta comprar (recetas menos lo que hay en la alacena).
2. Te avisa: `🤖 Abro Telegram Web y le escribo la lista al grupo «...»`
3. **El robot se pone a trabajar en la PC:** abre Chrome, entra a Telegram Web, busca
   el grupo, escribe la lista y la envía. La lista sale **desde tu cuenta**, no desde el
   bot.
4. El bot te confirma con una captura de pantalla: `✅ Lista enviada al grupo «...»`

Por ejemplo, con los datos de ejemplo y "Milanesas con pure", al grupo le llega:

```
Lista de compras:
- Carne nalga: 0.5 kg
- Papa: 1 kg
- Pan rallado: 0.1 kg
```

Fijate que el Huevo que llevan las milanesas **no aparece**, y que de pan rallado pide
0.1 kg en vez de los 0.2 kg que lleva la receta: es porque `StockActual.csv` dice que
en casa ya hay 6 huevos (alcanzan para los 2 de la receta) y 0.1 kg de pan rallado.

Si el robot no puede mandar la lista por Telegram Web (no hay sesión, no encuentra el
grupo, se colgó), **el bot te la manda él mismo** junto con el motivo, así la lista no
se pierde.

---

## Cargar tus propias comidas y tu stock

Los tres archivos de `data/` son **archivos `.csv` comunes**. Los podés editar con
Excel, LibreOffice, o cualquier editor de texto. No hace falta reiniciar el bot: los lee
de nuevo en cada pedido.

> ⚠️ **Los datos que vienen cargados son de ejemplo.** Hay que reemplazarlos por las
> recetas y el stock reales del grupo.

### `data/BaseDatos.csv` — las recetas

Es el archivo principal. **Una fila por cada ingrediente de cada comida**, así que una
comida ocupa varias filas seguidas:

```csv
Comida,Ingrediente,Cantidad,Unidad
Milanesas con pure,Carne nalga,0.5,kg
Milanesas con pure,Papa,1,kg
Milanesas con pure,Pan rallado,0.2,kg
Milanesas con pure,Huevo,2,unidad
Fideos con tuco,Fideos,0.5,kg
```

- **Comida**: tiene que escribirse **exactamente igual** en todas sus filas, y también
  igual a como figure en `Menu.csv`. Si en un lado dice `Milanesas con pure` y en otro
  `Milanesas con puré`, el bot los toma como dos comidas distintas.
- **Cantidad**: usá **punto** para los decimales (`0.5`), no coma. La coma separa
  columnas y rompería el archivo.
- **Unidad**: `kg`, `lt` o `unidad` (son las que acepta la carga desde el bot). Ver más abajo cómo afecta al redondeo.
- **No uses comas dentro de los nombres** de comidas ni de ingredientes.

Los botones de comidas salen **de este archivo**: apenas agregás una comida acá, aparece
sola en Telegram.

### `data/Menu.csv` — el menú de la semana

Lo usa el botón **📅 Menú de la semana**. Se puede editar desde el bot (✏ Cambiar un
día / 🎲 Sortear otro) o a mano.

```csv
Dia,Comida
Lunes,Milanesas con pure
Martes,Fideos con tuco
```

Cada comida tiene que existir en `BaseDatos.csv`. Si no existe, el bot **no se rompe**:
calcula el resto y te avisa:

```
⚠ No tienen receta cargada en BaseDatos.csv (no se cuentan): Guiso de mondongo
```

(Para mostrar esto en la demo, cambiá a mano en `Menu.csv` una comida por otra que no
exista, por ejemplo `Domingo,Guiso de mondongo`.)

### `data/StockActual.csv` — lo que ya tenés en casa

Se actualiza desde el bot con **🥫 Mi alacena**, o a mano.

```csv
Ingrediente,CantidadDisponible,Unidad
Papa,1,kg
Huevo,6,unidad
```

- El nombre del ingrediente tiene que coincidir exactamente con el de `BaseDatos.csv`.
- Lo que no figure acá se toma como que **no tenés nada** de eso.
- Si tenés más de lo que hace falta, el ingrediente directamente no aparece en la lista.

---

## Cómo se redondean las cantidades

- Lo que se mide en **`unidad`** (huevos, lechugas) se redondea **para arriba**: si el
  cálculo da 0.5 lechugas, la lista dice `1 unidad`. No tiene sentido ir al súper a
  comprar media lechuga.
- Lo que se mide en **kg / lt** se redondea a 2 decimales. Esto es para que la suma de
  números decimales no escriba cosas como `0.30000000000000004`.

> **Limitación conocida:** el bot puede pedirte `0.2 kg de pan rallado`, que tampoco es
> algo que se compre así (comprás un paquete). Resolverlo bien requeriría agregar una
> columna de presentación/envase a `BaseDatos.csv`.
---

## Las pruebas

Sirven para verificar partes sueltas sin tener que usar todo el bot. Se corren parado en
la carpeta `Ejecutables` (en Linux, `python3` en lugar de `py`).

### `prueba_conexion.py`

```
py prueba_conexion.py
```

Comprueba que el token de `config.txt` sea válido. **No le manda un mensaje a nadie.**
Es la primera prueba a correr cuando algo falla, porque descarta de una si el problema
es la configuración o es otra cosa.

### `robot_telegram_web.py`

```
py robot_telegram_web.py
py robot_telegram_web.py "Saved Messages"
```

Sin nada más, abre Telegram Web y verifica que haya sesión iniciada (si no, muestra el
QR para escanear). Con el nombre de un chat, además le manda un mensaje de prueba de 3
líneas. Usá tus mensajes guardados (`"Saved Messages"`, o `"Mensajes guardados"` si
Telegram Web está en castellano) para no molestar a nadie.

---

## Qué hacer cuando algo falla

| Qué ves | Qué pasa |
|---|---|
| El bot no contesta el `/start` | La ventana del bot no está abierta, o le estás escribiendo desde un chat distinto al `TELEGRAM_CHAT_ID` de `config.txt` (los demás se ignoran). |
| `Esta edición ya terminó` | Tocaste ✅ Listo en un resumen viejo de la alacena. Los cambios ya estaban guardados. |
| `Esta carga ya no está activa` | Tocaste ✅ Guardar en un resumen viejo de una carga de receta. Solo sirven los botones del último resumen. |
| `Este menú ya no está activo` | Tocaste un menú viejo (ya usado, o de antes de reiniciar el bot). Mandá `/start` de nuevo. |
| `⚠ No tienen receta cargada...` | Esa comida está en `Menu.csv` pero no en `BaseDatos.csv`. No es grave: el resto de la lista se calcula igual. |
| `⚠ No pude leer los datos: ...` | Un CSV tiene algo mal (por ejemplo, una cantidad con coma o con letras). El mensaje dice qué archivo y qué fila. |
| Un ingrediente no aparece y debería | Fijate que el nombre esté escrito **exactamente igual** en `BaseDatos.csv` y `StockActual.csv` (tildes, mayúsculas y espacios cuentan). O puede ser que el stock ya lo cubra. |
| `No hay nada para comprar` | El stock cubre todo lo que elegiste. |
| `no hay sesión iniciada en Telegram Web` | Corré `py robot_telegram_web.py` y escaneá el QR (ver el instructivo de instalación, Paso 5). |
| `no encontré el chat «...»` | `GRUPO_TELEGRAM` en `config.txt` no coincide exacto con el nombre del grupo, o tu cuenta no está en ese grupo. |
| `tardó más de 3 minutos y lo corté` | Casi seguro la PC estaba bloqueada. Desbloqueala y pedí de nuevo. |

# 📌 UTN FRCU – Tecnologías para la Automatización 2026

## 👥 Grupo

- **Número de equipo:** 12
- **Integrantes:**
    - Cassânego, Jesica
    - Geist, Ileana
    - Perez, Manuel
    - Tournoud, Marcos
    - Villaverde, Lara

---

## 🤖 Descripción del Bot

- **Nombre:** ComparaSuple · Comparador RPA de suplementos. Proyecto Integrador, primera etapa: Automatización Robótica de Procesos (RPA).
- **Descripción:** El sistema consulta precios y disponibilidad de suplementos deportivos en seis tiendas, a partir de un catálogo Excel. Busca productos equivalentes, verifica sus fichas y genera una planilla comparativa con enlaces y evidencias de las consultas. Su objetivo es reducir las búsquedas repetitivas y los errores de transcripción del relevamiento manual. La comparación permite evaluar costos de reposición y decidir un precio de venta. **El precio de venta se carga en el catálogo; el programa calcula el menor precio confirmado entre los resultados consultados, no un precio de venta sugerido.**
- **Tecnologías utilizadas:** TagUI v6.110 con Google Chrome (protocolo de depuración), Python 3 con `openpyxl`, JavaScript, y el PHP y PhantomJS incluidos en TagUI.
- **Video de demostración:** 

https://github.com/user-attachments/assets/25678622-a70c-4f6d-8ba1-699c8cf27540



### Funcionamiento

Las tiendas configuradas son [CB Deportes](https://cbdeportes.com), [Morashop](https://www.morashop.ar), [Disfit](https://www.disfit.com.ar), [ProteViking](https://www.proteviking.com.ar), [Ultimax](https://ultimaxsuplementos.com) y [Mercado Libre](https://www.mercadolibre.com.ar).

El proceso sigue estos pasos:

1. Lee los productos activos del Excel y valida sus datos.
2. Comprueba la presencia de cada marca en el buscador de la tienda antes de consultar sus productos.
3. Busca el producto y recorre los resultados. En algunas tiendas usa una consulta abreviada para adaptarse a su buscador y, si el nombre completo no da resultados, prueba con marca y línea (por ejemplo, `ENA creatina`). La validación conserva los datos completos del catálogo.
4. Compara marca, línea, sabor, peso, presentación, cantidad y SKU cuando están disponibles. Descarta presentaciones incompatibles y verifica los candidatos en sus fichas.
5. Registra disponibilidad y el menor precio válido publicado para la presentación buscada, incluida la alternativa de efectivo o transferencia cuando corresponda.
6. Guarda el avance y las evidencias en JSON por proveedor. Otro módulo valida esos archivos y genera el Excel final.

En modo visible utiliza una misma ventana del comparador para las tiendas y procesa Mercado Libre al final. En este sitio vuelve a aplicar el filtro de menor precio en cada búsqueda, pero compara los resultados porque el orden mostrado puede incluir anuncios u ofertas fuera de orden.

El alcance termina en el relevamiento y la comparación. El robot no compra productos ni modifica publicaciones.

### Estructura del repositorio

Se eligió **TagUI** porque permite expresar los pasos de navegación en archivos `.tag` legibles y reutilizables, trabajar con Chrome e integrar JavaScript y Python. Esto permite separar el recorrido del navegador de las reglas de comparación y del formato de salida. Los flujos `.tag` forman parte del código del proyecto y se conservan como fuente permanente.

| Tecnología | Responsabilidad |
| --- | --- |
| TagUI | Ejecutar los flujos de acceso, búsqueda, clic, desplazamiento, paginación y lectura de fichas. |
| Python | Leer el catálogo, coordinar consultas, comparar productos, guardar resultados y generar Excel con `openpyxl`. En modo visible también controla mouse y teclado mediante Windows. |
| JavaScript | Localizar elementos en el DOM mediante selectores, atributos y texto; extraer publicaciones, variantes, stock y precios. |
| PHP | Comunicar TagUI con Chrome mediante el protocolo de depuración y conservar la conexión autorizada con el navegador habitual. |
| PowerShell y API de Windows | Reconocer y cerrar avisos nativos de Chrome mediante UI Automation. |
| CMD | Iniciar el programa en Windows y comprobar Python y sus dependencias. |

El lanzador `tagui/INICIAR ComparaSuple.cmd` y los archivos del proyecto están dentro de [tagui/ComparaSuple](tagui/ComparaSuple):

| Ruta | Responsabilidad |
| --- | --- |
| `codigo/main.py` | Catálogo, menú, orden de tiendas y reanudación. |
| `codigo/engine.py`, `codigo/runtime_tagui.py`, `codigo/chrome_actual.php` | Ubicación y preparación de TagUI, ejecución de los flujos y conexión con Chrome. |
| `codigo/human_input.py` | Entrada real de mouse y teclado, geometría, foco y avisos nativos. |
| `flujos/*.tag`, `flujos/comun/`, `flujos/apoyo.js` | Flujo de cada tienda y acciones de navegación compartidas. |
| `codigo/parsers/` | Extracción por plataforma: Tiendanube, Mercado Libre y Ultimax. |
| `codigo/busqueda.py`, `codigo/matching.py` | Búsquedas, candidatos, fichas y comparación con el producto solicitado. |
| `codigo/capturas.py`, `codigo/procesar.py` | Guardado independiente por tienda y validación posterior de los JSON. |
| `codigo/workbook_portable.py` | Presentación y escritura del Excel. |
| `codigo/proveedores.py`, `codigo/iniciar_sesion.py` | Configuración de tiendas, destinos permitidos y comprobación de sesión. |
| `config.json` | Tiendas, adaptadores, consultas, acceso de Ultimax y límite de páginas. |
| `entrada/Productos.xlsx` | Catálogo de productos a consultar. |

---

## 🛠️ Instrucciones de uso

### 1. Requisitos

- Windows 10 u 11 para ejecutar las consultas web, tanto visibles como en segundo plano.
- [Google Chrome](https://www.google.com/chrome/) estable, versión 144 o superior para conectar el Chrome habitual en modo visible. En segundo plano también sirve Microsoft Edge.
- [Python](https://www.python.org/downloads/windows/) 3.10 o superior, con el lanzador `py` o el comando `python` disponible.
- TagUI para Windows v6.110.0, la última versión publicada (también funciona después de `tagui update`), y `openpyxl==3.1.5`.
- Conexión a Internet y permisos de escritura en la carpeta del proyecto y en la carpeta temporal de Windows.
- Una sesión de Mercado Libre iniciada en el navegador utilizado, si se desea consultar esa tienda.

No hace falta instalar Microsoft Excel para generar el archivo. Se necesita una aplicación compatible con `.xlsx` para verlo y recalcular sus fórmulas.

La navegación de esta distribución depende de Windows y sus componentes de TagUI. En Linux se puede usar Python para regenerar el Excel desde una captura guardada mediante `--procesar`; no se ofrece la navegación completa en Linux.

### 2. Instalación

#### 2.1. Instalar las herramientas

Instalar Python y Google Chrome. Si el instalador de Python ofrece agregarlo a `PATH`, activar esa opción.

Descargar **TagUI v6.110 para Windows** desde su [guía oficial de instalación](https://tagui.readthedocs.io/en/latest/setup.html). Se necesita el paquete `TagUI_Windows.zip`, que incluye los ejecutables; el ZIP de código fuente de GitHub no lo reemplaza. Extraerlo de modo que exista `C:\tagui\src`. Si no se puede escribir en `C:\`, la guía oficial indica extraerlo en el Escritorio; el programa también lo encuentra allí.

El proyecto utiliza Google Chrome instalado en el equipo y los componentes incluidos en TagUI. Conservar completo el paquete de TagUI; no hace falta instalar por separado OCR, Sikuli ni los complementos de Word o Excel. Tampoco hace falta agregar TagUI a `PATH` para este proyecto.

#### 2.2. Copiar el proyecto

Descargar el ZIP de este repositorio o recibir el paquete de entrega y extraerlo. El [repositorio de la materia](https://github.com/jaime-piperno/frcu-tagui) no se puede clonar completo en Windows por la longitud de algunas rutas de otros equipos; de allí se descarga sólo esta carpeta con:

```powershell
git clone --filter=blob:none --sparse https://github.com/jaime-piperno/frcu-tagui.git
cd frcu-tagui
git sparse-checkout set projects/2026/TagUI/team_12
```

Lo más simple es copiar **el contenido de su carpeta `tagui`** dentro de `C:\tagui`, junto a la carpeta `src` de TagUI ya instalada.

El proyecto también puede quedar en otra carpeta. El programa busca TagUI, en este orden, junto al proyecto, en el comando `tagui` del `PATH`, en `C:\tagui`, en el Escritorio, en la carpeta del usuario y en `%APPDATA%\tagui`. Si TagUI está en otro lugar, indicar su carpeta en la variable de entorno `COMPARASUPLE_TAGUI` y abrir una consola nueva:

```powershell
setx COMPARASUPLE_TAGUI "D:\herramientas\tagui"
```

Con la opción recomendada, la estructura debe quedar así, sin una segunda carpeta `tagui` dentro de la primera:

```text
C:\tagui\
├── src\                         Ejecutables de TagUI instalados por separado
├── INICIAR ComparaSuple.cmd
└── ComparaSuple\
    ├── codigo\
    │   └── parsers\
    ├── entrada\
    │   └── Productos.xlsx
    ├── flujos\
    │   └── comun\
    ├── config.json
    └── requirements.txt
```

#### 2.3. Instalar la dependencia de Python

Abrir PowerShell o una consola y ejecutar:

```powershell
py -3 -m pip install -r "C:\tagui\ComparaSuple\requirements.txt"
```

Si se utiliza `python` en lugar de `py`, ejecutar:

```powershell
python -m pip install -r "C:\tagui\ComparaSuple\requirements.txt"
```

La instalación y la ejecución deben usar el mismo Python. El archivo `.cmd` comprueba la versión y la disponibilidad de `openpyxl` antes de abrir el menú; si falta, ofrece instalarlo con `pip` en ese mismo Python.

### 3. Primera ejecución y permisos de Chrome

1. Abrir `INICIAR ComparaSuple.cmd` (por ejemplo, `C:\tagui\INICIAR ComparaSuple.cmd`) y elegir **1. Demo visible**.
2. Si la conexión con el Chrome habitual no está habilitada, el programa abre ese navegador maximizado en `chrome://inspect/#remote-debugging`. Activar allí la opción de depuración remota. Esta configuración se hace manualmente y no requiere copiar una sesión ni contraseñas.
3. Cuando Chrome solicite conectar el programa, aceptar **Permitir**. Habilitar la opción y aceptar la conexión son dos pasos distintos. Seguir también los mensajes de la consola.
4. El programa comprueba la conexión antes de comenzar las consultas. Si no se habilita o autoriza dentro del tiempo indicado, no inicia el relevamiento. Después de corregirlo, volver a elegir la opción del menú.
5. Al llegar a Mercado Libre, comprueba si hay una cuenta conectada. Si solicita ingresar, iniciar sesión manualmente y seguir la indicación de la consola para continuar. Si se decide omitir el ingreso, deja Mercado Libre como **Omitido sin sesión** y conserva lo obtenido en las otras tiendas.

La sesión iniciada se conserva en el Chrome habitual para futuras ejecuciones, mientras siga siendo válida. El permiso de conexión puede mantenerse mientras el menú siga abierto y conectado; una nueva conexión puede volver a pedir **Permitir**. Los permisos, el ingreso a la cuenta y los CAPTCHA requieren intervención de la persona.

Ultimax utiliza una clave de acceso a la tienda. Se incluye en `config.json` a propósito, para mostrar que el sistema también trabaja con tiendas protegidas con clave y no pedirla en cada ejecución. La variable de entorno `COMPARASUPLE_ULTIMAX_CLAVE` permite reemplazarla sin editar el archivo.

### 4. Ejecución

El menú principal ofrece:

| Opción | Acción |
| --- | --- |
| **1** | Demo visible: consulta `N001`, Gold CREATINA MONOHIDRATO 300 GRAMOS, en las seis tiendas configuradas. |
| **2** | Consulta todos los productos activos en modo visible. |
| **3** | Consulta el catálogo en segundo plano, sin ocupar el escritorio. Mercado Libre usa un perfil dedicado. |
| **4** | Genera nuevamente el Excel desde una captura guardada, sin consultar las páginas. |
| **5** | Reanuda una captura interrumpida y permite elegir el modo de ejecución. |
| **0** | Sale del menú y libera la conexión. |

Con el catálogo incluido, 3 productos en 6 tiendas, cada corrida tarda unos 20 minutos, tanto visible como en segundo plano. La demo de un producto tarda unos 6 minutos.

**En modo visible, dejar libres mouse y teclado y mantener el navegador en primer plano.** El robot mueve el cursor, escribe, hace clic y desplaza la página. `Escape` o cambiar de ventana detiene la ejecución y conserva el avance. Al finalizar normalmente cierra la ventana que creó para el comparador y mantiene las ventanas personales y la sesión de Chrome.

En segundo plano, el perfil dedicado de Mercado Libre **no hereda la sesión del Chrome habitual**. Si ese perfil no tiene sesión válida, la tienda se omite. Para iniciarla una vez, ejecutar `py -3 ComparaSuple\codigo\iniciar_sesion.py` desde la carpeta del lanzador: abre Chrome con ese perfil y espera el ingreso manual. Para una demo con Mercado Libre se recomienda el modo visible; un CAPTCHA en segundo plano impide continuar automáticamente esa consulta.

#### Ejecución por consola

Desde la carpeta que contiene `INICIAR ComparaSuple.cmd` (por ejemplo, `C:\tagui`) se pueden ejecutar consultas acotadas o procesar capturas:

```powershell
# Un producto, en Mercado Libre, con navegador visible
py -3 ComparaSuple\codigo\main.py --visible --producto N001 --proveedor mercadolibre

# Volver a generar el Excel; reemplazar <captura> por la carpeta real
py -3 ComparaSuple\codigo\main.py --procesar "ComparaSuple\salidas\<captura>"

# Reanudar esa captura en modo visible
py -3 ComparaSuple\codigo\main.py --reanudar "ComparaSuple\salidas\<captura>" --visible
```

Para reanudar, mantener el catálogo y los proveedores de la ejecución original. Para hacer una consulta nueva después de cambiar esos datos, iniciar otra ejecución.

| Opción de `main.py` | Uso |
| --- | --- |
| `--menu` | Abre el menú; es lo que usa el lanzador. |
| `--demo` | Consulta sólo `N001`, como la opción 1. |
| `--visible` o `--segundo-plano` | Elige el modo. Sin ninguna de las dos, la demo es visible y el resto se ejecuta en segundo plano. |
| `--producto ID` | Limita la consulta a ese producto. Se puede repetir. |
| `--proveedor ID` | Limita la consulta a esa tienda: `mercadolibre`, `cbdeportes`, `morashop`, `disfit`, `proteviking` o `ultimax`. Se puede repetir. |
| `--excel RUTA` | Usa otro catálogo en lugar de `entrada\Productos.xlsx`. |
| `--procesar CARPETA` | Genera el Excel desde una captura, sin navegar, como la opción 4. |
| `--reanudar CARPETA` | Retoma una captura interrumpida, como la opción 5. |
| `--solo-capturar` | Guarda los JSON sin generar el Excel. |
| `--espera-intervencion SEGUNDOS` | Tiempo para resolver un CAPTCHA o un ingreso en modo visible. Por defecto, 300; con 0 se omite la tienda. |
| `--chrome-actual` | Usa el Chrome habitual aunque no se consulte Mercado Libre. |
| `--iniciar-sesion` | Sólo comprueba o inicia la sesión de Mercado Libre en el Chrome habitual. |

Variables de entorno opcionales:

| Variable | Uso |
| --- | --- |
| `COMPARASUPLE_TAGUI` | Carpeta de TagUI, si no está en una de las ubicaciones habituales. |
| `COMPARASUPLE_PYTHON` | Python que usa el lanzador, en lugar de `py -3` o `python`. |
| `COMPARASUPLE_BROWSER` | Ruta del navegador, si Chrome o Edge no están instalados en la ubicación habitual. |
| `COMPARASUPLE_ULTIMAX_CLAVE` | Reemplaza la clave de Ultimax de `config.json`. |

### 5. Catálogo de entrada

El archivo [Productos.xlsx](tagui/ComparaSuple/entrada/Productos.xlsx) contiene 3 productos activos en la hoja `Productos`, elegidos porque se publican en todas las tiendas configuradas: dos creatinas de 300 g (Gold Nutrition y ENA) y la Whey Protein de Gold Nutrition de 2 lb, sabor chocolate. Sirven para mostrar la comparación sin una corrida larga; se pueden agregar más filas con el mismo formato.

| Columna | Uso |
| --- | --- |
| `ID` | Identificador del producto. Conviene conservarlo; los duplicados se rechazan. |
| `CATEGORIA` | Agrupa los productos en el Excel final. |
| `MARCA` | Marca solicitada, obligatoria para una fila activa. |
| `PRODUCTO` | Nombre con tamaño, sabor y presentación cuando correspondan. Las filas sin nombre se ignoran. |
| `COSTO` | Costo de referencia aportado por el usuario. |
| `PRECIO DE VENTA` | Precio de venta aportado por el usuario. También se admite el encabezado `PRECIO`. |
| `ACTIVO` | `no`, `false` o `0` excluyen el producto de la consulta. |

Se pueden agregar las columnas `PESO G`, `UNIDADES POR PACK`, `SKU`, `LINEA`, `SABOR` y `PRESENTACION` para precisar la comparación. Si no están, el sistema intenta obtener esos atributos del nombre del producto. Una descripción más precisa ayuda a descartar coincidencias incorrectas.

### 6. Resultado esperado

Cada ejecución crea una carpeta en `ComparaSuple\salidas`, identificada por fecha, hora y un sufijo para evitar colisiones. La consola muestra su ruta bajo `CAPTURA` y la del Excel bajo `RESULTADO`.

```text
salidas\<captura>\
├── Comparación de precios.xlsx
├── proveedores\                 JSON independiente de cada tienda
└── evidencia\                   Datos capturados en búsquedas y fichas
```

Cuando corresponde, también se conservan diagnósticos y registros del error en esa carpeta.

El archivo **Comparación de precios.xlsx** tiene dos hojas:

- **Comparación:** productos agrupados por categoría, costo, precio de venta, menor precio confirmado, tienda de referencia y resultados por tienda. Los enlaces permiten abrir las publicaciones.
- **Detalle:** estado de cada consulta, precio en ARS, forma de pago, variante encontrada, publicación, fecha de consulta, observación y evidencia asociada.

Los resultados distinguen **Con stock + precio**, **Sin stock**, **No encontrado en buscador**, **Marca no encontrada en buscador**, **Revisar variante** y **Sin precio**. También muestran errores de consulta, búsquedas incompletas, intervención requerida y tiendas omitidas. Un producto no encontrado o una consulta fallida no demuestra que la tienda no lo venda.

Sólo los precios confirmados participan del mínimo. Los importes no incluyen envío y pueden depender de la forma de pago indicada. La fecha de consulta importa: las publicaciones pueden cambiar después de generar el archivo.

Corrida del 13/10/2026 en modo visible, con el catálogo incluido y sesión iniciada en Mercado Libre. Importes en ARS:

| Producto | Menor precio | Mercado Libre | CB Deportes | Morashop | Disfit | ProteViking | Ultimax |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Gold Creatina 300 g | **17.404,02** (Disfit) | 28.161 | 25.200 | 18.025,10 | 17.404,02 | 23.900,52 | 22.528,80 |
| ENA Creatina 300 g Neutro | **21.732,71** (Disfit) | 30.000 | Revisar variante | 21.906,20 | 21.732,71 | 27.899,76 | No encontrado |
| Gold Whey 2 lb Chocolate | **67.896,05** (Disfit) | 89.511 | 76.223,25 | 73.871,80 | 67.896,05 | No encontrado | 72.414 |

Los tres casos sin precio muestran los controles de calidad. CB Deportes no indica el sabor de la creatina ENA, por lo que queda para revisar. Ultimax sólo publica la creatina ENA sabor Fruit Punch, que no es la presentación pedida. ProteViking no publica esa proteína.

### 7. Solución de problemas

| Problema | Qué hacer |
| --- | --- |
| No encuentra Python u `openpyxl` | Revisar la instalación y ejecutar el comando de dependencias con el mismo Python que usa el lanzador. |
| No encuentra TagUI | El mensaje indica las carpetas revisadas. Verificar que exista `src\tagui_parse.php` dentro de TagUI y que se descargó el paquete de Windows, no sólo el código fuente. Si TagUI está en otra carpeta, definir `COMPARASUPLE_TAGUI`. |
| Falta `MSVCR110.dll` | El programa lo detecta al comprobar TagUI. Instalar `vcredist_x86.exe` desde la [solución oficial de TagUI para Windows](https://tagui.readthedocs.io/en/latest/setup_troubleshooting.html) y volver a elegir la opción. |
| Aviso de versión distinta de TagUI | El programa continúa sin algunas mejoras del puente. Si aparecen errores de conexión, instalar el `TagUI_Windows.zip` oficial v6.110. |
| Chrome no conecta | Comprobar la versión, habilitar la opción en `chrome://inspect/#remote-debugging` y aceptar **Permitir** cuando se solicite. Si la opción no existe o está bloqueada por políticas del equipo, no se puede iniciar ese modo hasta resolverlo. |
| Mercado Libre pide ingreso o CAPTCHA | Completarlo manualmente en el navegador cuando el programa lo indique, o elegir omitir la tienda. Tener sesión no garantiza que nunca aparezca un CAPTCHA. |
| Se detuvo por foco o por `Escape` | Mantener Chrome maximizado y en primer plano. Reanudar desde la opción 5. |
| Se detuvo sin que nadie usara el equipo | Otra ventana tomó el foco; por ejemplo, una tarea programada que abre una consola. `error.log` registra `focus_lost` con la clase de esa ventana. Desactivar esa tarea durante la demostración y reanudar desde la opción 5. |
| Falló una tienda o cambió su página | Revisar el estado y la observación en `Detalle`, los JSON y los diagnósticos de la captura. Conservar las últimas líneas de consola para identificar el punto del fallo. |
| No puede escribir el Excel | Cerrar el archivo si está abierto y revisar permisos de la carpeta. Después usar la opción 4 sobre esa captura. |

Los avisos promocionales que tapan la página se cierran con su botón de cerrar o de rechazo, como «×» o «No en este momento». El robot nunca acepta ofertas ni suscripciones. Si un aviso no ofrece una opción segura, `error.log` lo registra como `aviso_sin_cierre` con su estructura; en ese caso, detener con `Escape`, cerrar el aviso y reanudar. No borrar la captura para intentar recuperarla.

Si el fallo ocurre al conectar Chrome, antes de que exista una captura, los diagnósticos de arranque se guardan en `ComparaSuple\salidas\inicio`.

---

## 📝 Información Adicional

### Desafíos y decisiones técnicas

El desarrollo comenzó con un catálogo común y las tiendas basadas en Tiendanube. Luego se separaron los flujos de navegación, los parsers y el procesamiento de JSON, y se incorporaron Ultimax y Mercado Libre. Las pruebas mostraron diferencias entre buscadores, banners que aparecían durante una acción y problemas de sesión y foco. Se añadieron consultas adaptadas, comprobaciones antes de avanzar, manejo de avisos y reanudación desde el avance guardado.

Los elementos de las páginas se identifican desde su estructura HTML; el modo visible usa su posición para actuar con mouse y teclado. Los avisos propios de Chrome se identifican por la interfaz de accesibilidad de Windows. No se utilizan capturas de botones ni OCR para identificar los productos.

Para añadir una tienda se agrega su configuración, su archivo `flujos/<id>.tag` y se selecciona un parser existente o se implementa uno nuevo en `codigo/parsers`. El parser debe devolver la misma estructura de captura para que la comparación y el Excel puedan reutilizarse. Una web distinta requiere adaptar y probar esa extracción; no basta con agregar su URL.

Tres conceptos de automatización aplicados al sistema:

| Concepto | Aplicación en este RPA |
| --- | --- |
| **Retroalimentación** | Después de escribir o navegar, el sistema observa el texto, la URL y el estado de la página. Compara lo observado con lo esperado y corrige o reintenta antes de avanzar. Por ejemplo, una búsqueda incompleta no debe aceptarse como una consulta válida. |
| **Perturbaciones exógenas** | Un banner, una demora de red o un CAPTCHA altera el proceso desde fuera del robot. El programa intenta cerrar avisos reconocidos, esperar la carga o pedir intervención; si no puede continuar, guarda el avance y registra el impedimento. |
| **Control de calidad del proceso** | Antes de incorporar un precio, compara la presentación con el catálogo y verifica la ficha. Una creatina de 150 g no se acepta para una solicitud de 300 g, aunque sea más barata. Los estados de revisión y las evidencias permiten detectar y revisar resultados dudosos. |

### Controles y limitaciones actuales

| Control | Qué verifica |
| --- | --- |
| Catálogo | Datos obligatorios, IDs y selección de productos. |
| Navegación | Texto ingresado, destino esperado, elementos visibles y respuesta de la página antes de avanzar. |
| Identidad del producto | Marca y atributos de la presentación, para no comparar un envase o pack diferente. |
| Ficha y precio | Confirma candidatos en sus fichas y separa precios válidos, stock y variantes dudosas. |
| Recuperación | Reintentos limitados, cierre de avisos con su botón de cerrar o de rechazo, nunca de aceptar, y guardado progresivo. |
| Evidencia | Archivos por consulta y hashes de integridad antes de consolidar el resultado. |

- Si faltan datos para confirmar una variante, se informa **Revisar**. Un fallo técnico se registra como tal y no se convierte en “Sin stock”. Los controles reducen errores, pero no garantizan reconocer todas las publicaciones o todos los diseños posibles.
- Las restricciones iniciales son disponer de las herramientas, autorizar Chrome, mantener una conexión estable y dejar el escritorio libre durante el modo visible. A largo plazo, los cambios de diseño, los avisos nuevos y las restricciones de los sitios pueden requerir actualizar selectores o parsers. Los CAPTCHA y controles de acceso no se resuelven automáticamente.
- El alcance de búsqueda es limitado: `max_pages` está configurado en **2**. Además existen límites de candidatos y fichas para acotar el tiempo. Por eso **“menor precio” significa menor precio confirmado entre los resultados examinados**, no el mínimo de todas las publicaciones de Internet o de Mercado Libre. No se garantiza completar todos los productos si una tienda bloquea las consultas.
- La automatización reduce la carga de trabajo manual, pero una comparación errónea podría llevar a una mala decisión de compra o venta. La revisión de variantes dudosas, la separación de errores y los enlaces a las fuentes permiten controlar ese riesgo. Las credenciales personales permanecen en el navegador; no deben incluirse perfiles, cookies ni sesiones en una entrega del proyecto.

### Mejora propuesta para la segunda etapa

Se propone incorporar **notificaciones por Telegram**, tanto del cierre de una ejecución como de variaciones relevantes de precio. Esta función todavía no está implementada.

El módulo de notificaciones podría consumir los resultados consolidados, comparar capturas del mismo producto y proveedor y avisar cuando un precio confirmado cambie por encima de un umbral configurable. También podría informar errores que requieran intervención, adjuntando la tienda y el motivo sin enviar credenciales ni información de la cuenta.

La mejora necesitaría definir destinatarios, umbrales y un mecanismo para evitar avisos duplicados. El token se configuraría fuera del código. Para comprobarla, se deberían probar una variación válida, una ejecución sin cambios y un error de consulta, verificando que sólo se emita la notificación correspondiente. Esto extendería la retroalimentación del proceso al usuario y facilitaría el seguimiento entre ejecuciones. Su alcance deberá validarse con los docentes antes de implementarlo en la segunda etapa.

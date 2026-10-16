@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul
title RPA Comparador de Precios - UTN FRCU 2026

:: ==============================================================================
:: VERIFICACIONES PREVIAS DEL ENTORNO DE EJECUCIÓN
:: ==============================================================================

:: 1. Verificar TagUI en PATH o ubicaciones estándar conocidas
where tagui >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%USERPROFILE%\tagui\src\tagui.cmd" (
        set "PATH=%USERPROFILE%\tagui\src;!PATH!"
    ) else if exist "C:\tagui\src\tagui.cmd" (
        set "PATH=C:\tagui\src;!PATH!"
    ) else if exist "%LOCALAPPDATA%\tagui\src\tagui.cmd" (
        set "PATH=%LOCALAPPDATA%\tagui\src;!PATH!"
    )
)

where tagui >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ==============================================================================
    echo [ERROR] No se encontró TagUI instalado en el sistema ni en el PATH.
    echo ==============================================================================
    echo Ubicaciones revisadas:
    echo   - Variable PATH del sistema
    echo   - %USERPROFILE%\tagui\src\tagui.cmd
    echo   - C:\tagui\src\tagui.cmd
    echo   - %LOCALAPPDATA%\tagui\src\tagui.cmd
    echo.
    echo Consulta el archivo README.md para la guía rápida de instalación de TagUI.
    echo ==============================================================================
    echo.
    pause
    exit /b 1
)

:: 2. Verificar disponibilidad de Node.js
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ==============================================================================
    echo [ERROR] Node.js no está instalado o no se encuentra en el PATH.
    echo ==============================================================================
    echo Por favor descárgalo e instálalo desde https://nodejs.org
    echo Luego reinicia esta ventana de comandos.
    echo ==============================================================================
    echo.
    pause
    exit /b 1
)

:: 3. Verificar dependencias de Node.js (ExcelJS)
node -e "require('exceljs')" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Módulo exceljs no detectado. Instalando dependencias necesarias...
    call npm install
    node -e "require('exceljs')" >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] No se pudo cargar exceljs luego de npm install.
        echo Intenta ejecutar 'npm install' manualmente en esta carpeta.
        echo.
        pause
        exit /b 1
)
    echo [OK] Dependencias instaladas exitosamente.
)

:: 4. Verificar integridad de archivos esenciales del proyecto
if not exist "supermercados.tag" (
    echo [ERROR] Falta el archivo esencial 'supermercados.tag'.
    echo Asegúrate de ejecutar este archivo dentro de la carpeta del proyecto.
    echo.
    pause
    exit /b 1
)
if not exist "validador.js" (
    echo [ERROR] Falta el archivo esencial 'validador.js'.
    echo.
    pause
    exit /b 1
)
if not exist "generar_excel.js" (
    echo [ERROR] Falta el archivo esencial 'generar_excel.js'.
    echo.
    pause
    exit /b 1
)
if not exist "input.csv" (
    echo [AVISO] No se encontró input.csv. Creando canasta básica mensual por defecto...
    (echo producto,cantidad,unidad& echo Lavandina Ayudín,1,L& echo Leche La Serenísima,1,L& echo Coca Cola,2.25,L& echo Manaos Naranja,2.25,L& echo Manaos Lima Limón,2.25,L& echo Manaos Cola,2.25,L& echo Galletitas Criollitas,300,g) > input.csv
)

:: 5. Argumentos directos por línea de comandos (ej: ejecutar.bat "manaos cola 2.25l")
if not "%~1"=="" (
    set "ARG1=%~1"
    goto :evaluar_arg
)

:menu
cls
echo ==============================================================================
echo       UTN FRCU - Tecnologías para la Automatización (Año 2026)
echo          Trabajo Práctico Integrador: Bot RPA de Supermercados
echo ==============================================================================
echo.
echo Selecciona una opción:
echo   [1] Procesar compra del mes (desde input.csv)
echo   [2] Buscar producto individual (consulta interactiva)
echo   [3] Abrir reporte Excel (reporte_supermercados.xlsx)
echo   [4] Editar lista de compra del mes (input.csv)
echo   [5] Ver catálogo cerrado de productos disponibles
echo   [6] Limpiar resultados / historial (sin alterar input.csv)
echo   [7] Diagnóstico del sistema y pruebas unitarias
echo   [8] Salir
echo.
echo (Tip: También podés ingresar directamente el número [1-20] o nombre de un producto del catálogo)
echo.
set "OPCION=1"
set /p "OPCION=Elige opción [1-8] o producto del catálogo [1]: "

set "OPCION_FIRST="
for /f "tokens=1" %%a in ("!OPCION!") do set "OPCION_FIRST=%%a"

if "!OPCION_FIRST!"=="1" goto :ejecutar_mes
if "!OPCION_FIRST!"=="2" goto :pedir_individual
if "!OPCION_FIRST!"=="3" goto :abrir_excel
if "!OPCION_FIRST!"=="4" goto :editar_input
if "!OPCION_FIRST!"=="5" goto :ver_catalogo
if "!OPCION_FIRST!"=="6" goto :menu_limpieza
if "!OPCION_FIRST!"=="7" goto :ejecutar_diagnostico
if "!OPCION_FIRST!"=="8" goto :salir
if /i "!OPCION_FIRST!"=="catalogo" goto :ver_catalogo
if /i "!OPCION_FIRST!"=="cat" goto :ver_catalogo
if /i "!OPCION_FIRST!"=="editar" goto :editar_input
if /i "!OPCION_FIRST!"=="edit" goto :editar_input
if /i "!OPCION_FIRST!"=="input" goto :editar_input
if /i "!OPCION_FIRST!"=="salir" goto :salir
if /i "!OPCION_FIRST!"=="exit" goto :salir

:: Si el usuario escribió un número [1-20] o producto del catálogo
set "PROD_RESOLVED="
for /f "usebackq delims=" %%i in (`node catalogo.js --obtener-producto "!OPCION!" 2^>nul`) do set "PROD_RESOLVED=%%i"
if not "!PROD_RESOLVED!"=="" (
    set "PROD_MANUAL=!PROD_RESOLVED!"
    goto :ejecutar_individual
)

echo.
echo [ERROR] Opción o producto no válido en el catálogo: "!OPCION!"
ping 127.0.0.1 -n 3 >nul 2>&1
goto :menu

:evaluar_arg
if "%ARG1:~0,1%"=="-" (
    goto :ejecutar_mes_con_args
) else (
    set "ARG_STR=%*"
    set "PROD_MANUAL="
    for /f "usebackq delims=" %%i in (`node catalogo.js --obtener-producto "!ARG_STR!" 2^>nul`) do set "PROD_MANUAL=%%i"
    if "!PROD_MANUAL!"=="" (
        echo.
        echo ==============================================================================
        echo [RECHAZADO] El producto ingresado "!ARG_STR!" no pertenece al catálogo cerrado.
        echo             Ejecuta 'ejecutar.bat' para ver las opciones disponibles.
        echo ==============================================================================
        echo.
        exit /b 1
    )
    goto :ejecutar_individual
)

:editar_input
echo.
echo ==============================================================================
echo [INFO] Abriendo input.csv en el Bloc de Notas para su edición...
echo ==============================================================================
echo   - Agrega, quita o modifica los productos respetando el formato.
echo   - Ejemplo de línea: Arroz Gallo Largo Fino 1 kg,1,kg
echo   - Guarda los cambios con Ctrl+G (o Archivo - Guardar).
echo   - Regresa a esta consola y presiona una tecla cuando hayas terminado.
echo ==============================================================================
echo.
start notepad.exe "input.csv"
pause
goto :menu

:pedir_individual
cls
call node catalogo.js --menu-individual
echo.
set "PROD_INPUT="
set /p "PROD_INPUT=Selecciona el número [1-20] o escribe el nombre del producto del catálogo: "
if "!PROD_INPUT!"=="" (
    echo [ERROR] No se ingresó ningún producto.
    ping 127.0.0.1 -n 3 >nul 2>&1
    goto :menu
)

set "PROD_MANUAL="
for /f "usebackq delims=" %%i in (`node catalogo.js --obtener-producto "!PROD_INPUT!" 2^>nul`) do set "PROD_MANUAL=%%i"

if "!PROD_MANUAL!"=="" (
    echo.
    echo ==============================================================================
    echo [RECHAZADO] La búsqueda rápida individual requiere seleccionar un producto
    echo             del catálogo cerrado. "!PROD_INPUT!" no pertenece al catálogo.
    echo ==============================================================================
    echo.
    pause
    goto :menu
)
goto :ejecutar_individual

:ver_catalogo
cls
call node catalogo.js --listar
echo.
pause
goto :menu

:ejecutar_individual
echo.
echo ==============================================================================
echo [INFO] Validando consulta contra el CATÁLOGO CERRADO...
echo ==============================================================================
call node catalogo.js --validar "!PROD_MANUAL!"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ==============================================================================
    echo [RECHAZADO] La búsqueda no puede ejecutarse porque el producto no está
    echo             en el catálogo cerrado definido para este proyecto.
    echo ==============================================================================
    echo.
    pause
    goto :menu
)

echo.
echo ==============================================================================
echo [INFO] Iniciando BÚSQUEDA INDIVIDUAL para: "!PROD_MANUAL!"
echo [INFO] Se consultará Carrefour, COTO y Día %% sin modificar input.csv...
echo ==============================================================================
echo.

:: Cerrar Excel si estuviera abierto para evitar bloqueos de archivo
taskkill /F /IM EXCEL.EXE >nul 2>&1

:: Limpiar consulta individual anterior para que el reporte se enfoque en la nueva
call node validador.js --limpiar 2 >nul 2>&1

:: Crear temp_input.csv de forma 100%% segura usando validador.js (maneja comas, comillas y acentos RFC-4180)
call node validador.js --crear-temp "!PROD_MANUAL!"

:: Búsqueda rápida individual ejecutada exclusivamente con TagUI
call tagui supermercados.tag temp_input.csv
if exist "temp_input.csv" del "temp_input.csv" >nul 2>&1

:: Cerrar únicamente el navegador Chrome de TagUI al finalizar las búsquedas
call node validador.js --cerrar-tagui >nul 2>&1

:: Validación inteligente y reporte comparativo en vivo por consola
echo.
call node validador.js --reporte-individual "!PROD_MANUAL!"

:: Actualización del reporte Excel
echo [INFO] Actualizando reporte_supermercados.xlsx con la nueva consulta...
call node generar_excel.js

if exist "reporte_supermercados.xlsx" (
    echo [INFO] Abriendo reporte_supermercados.xlsx...
    start "" "reporte_supermercados.xlsx"
)

echo.
pause
goto :menu

:ejecutar_mes
if not exist "input.csv" (
    echo [ERROR] No se encontró el archivo input.csv con los productos.
    pause
    goto :menu
)

echo.
echo ==============================================================================
echo [INFO] Validando canasta mensual contra el CATÁLOGO CERRADO...
echo ==============================================================================
call node catalogo.js --validar-csv input.csv
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ==============================================================================
    echo [ERROR] input.csv contiene productos que no pertenecen al catálogo cerrado.
    echo         Edita el archivo con la opción [4] para incluir sólo ítems válidos.
    echo ==============================================================================
    echo.
    pause
    goto :menu
)

echo.
echo ==============================================================================
echo [INFO] Iniciando MODO COMPRA DEL MES
echo [INFO] Leyendo canasta mensual predefinida desde input.csv...
echo ==============================================================================
echo.

:: Cerrar Excel si estuviera abierto para evitar bloqueos de archivo
taskkill /F /IM EXCEL.EXE >nul 2>&1

:: Limpiar registros anteriores de compra del mes para iniciar búsqueda limpia
call node validador.js --limpiar 1 >nul 2>&1

call node -e "const fs = require('fs'); const lines = fs.readFileSync('input.csv','utf8').split('\n').slice(1).map(l => l.trim()).filter(l => l).map(l => { const p = l.split(','); return { producto: p[0], cantidad: parseFloat(p[1])||1, unidad: p[2]||'', unidades: parseInt(p[3],10)||1 }; }); require('./rpa_runner.js').runRPA({ modo: 'compra_mes', items: lines, demoMode: true, onStatus: (s) => console.log(s.message || s) })"

echo.
echo [INFO] Procesando datos y generando reporte Excel con 5 hojas...
call node generar_excel.js

if exist "reporte_supermercados.xlsx" (
    echo [INFO] Abriendo reporte_supermercados.xlsx...
    start "" "reporte_supermercados.xlsx"
)

echo.
echo ==============================================================================
echo [FIN] Compra del mes procesada exitosamente!
echo ==============================================================================
echo.
pause
goto :menu

:ejecutar_mes_con_args
goto :ejecutar_mes

:abrir_excel
echo.
if exist "reporte_supermercados.xlsx" (
    echo [INFO] Abriendo reporte_supermercados.xlsx en Microsoft Excel...
    start "" "reporte_supermercados.xlsx"
) else (
    echo [AVISO] Aún no se ha generado el reporte Excel.
    echo Por favor ejecuta primero la opción [1] o [2].
)
ping 127.0.0.1 -n 3 >nul 2>&1
goto :menu

:menu_limpieza
cls
echo ==============================================================================
echo                       GESTIÓN Y LIMPIEZA DE RESULTADOS
echo ==============================================================================
echo.
echo   [1] Limpiar registros de Compra del Mes actual (reiniciar canasta)
echo   [2] Limpiar historial de Consultas Individuales
echo   [3] Limpiar TODO el historial de resultados
echo   [4] Volver al menú principal
echo.
echo (Nota: Tu archivo input.csv NUNCA será borrado ni modificado)
echo.
set "OPC_LIMPIAR=4"
set /p "OPC_LIMPIAR=Selecciona opción [4]: "

set "OPC_LIMPIAR_FIRST="
for /f "tokens=1" %%a in ("!OPC_LIMPIAR!") do set "OPC_LIMPIAR_FIRST=%%a"

if "!OPC_LIMPIAR_FIRST!"=="1" (
    call node validador.js --limpiar 1
    call node generar_excel.js
    pause
    goto :menu
)
if "!OPC_LIMPIAR_FIRST!"=="2" (
    call node validador.js --limpiar 2
    call node generar_excel.js
    pause
    goto :menu
)
if "!OPC_LIMPIAR_FIRST!"=="3" (
    call node validador.js --limpiar 3
    call node generar_excel.js
    pause
    goto :menu
)
goto :menu

:ejecutar_diagnostico
cls
echo ==============================================================================
echo              DIAGNÓSTICO DEL SISTEMA - BOT RPA SUPERMERCADOS
echo ==============================================================================
echo.
echo [1/8] Verificando Sistema Operativo y Directorio...
echo   Directorio actual : %CD%
echo.
echo [2/8] Verificando Node.js...
call node -v
if %ERRORLEVEL% NEQ 0 (echo   [FALLO] Node.js no funciona correctamente) else (echo   [OK] Node.js operativo)
echo.
echo [3/8] Verificando npm...
call npm -v
if %ERRORLEVEL% NEQ 0 (echo   [FALLO] npm no funciona correctamente) else (echo   [OK] npm operativo)
echo.
echo [4/8] Verificando TagUI en PATH...
where tagui
if %ERRORLEVEL% NEQ 0 (echo   [FALLO] TagUI no disponible en PATH) else (echo   [OK] TagUI operativo)
echo.
echo [5/8] Verificando dependencia ExcelJS...
node -e "const x = require('exceljs'); console.log('  [OK] ExcelJS cargado correctamente.');"
if %ERRORLEVEL% NEQ 0 (echo   [FALLO] No se pudo cargar exceljs)
echo.
echo [6/8] Verificando archivos del repositorio...
for %%f in (supermercados.tag validador.js generar_excel.js input.csv package.json) do (
    if exist "%%f" (
        echo   [OK] Archivo presente: %%f
    ) else (
        echo   [ERROR] Archivo faltante: %%f
    )
)
echo.
echo [7/8] Verificando permisos de escritura en la carpeta...
echo test_perm > __test_perm.tmp
if exist "__test_perm.tmp" (
    del __test_perm.tmp
    echo   [OK] Permiso de escritura confirmado.
) else (
    echo   [ERROR] Sin permiso de escritura.
)
echo.
echo [8/8] Ejecutando batería completa de pruebas unitarias (validador.js)...
call node validador.js --test
echo.
echo ==============================================================================
echo Diagnóstico finalizado con éxito.
echo ==============================================================================
echo.
pause
goto :menu

:salir
echo.
echo ==============================================================================
echo Gracias por utilizar el Comparador RPA de Supermercados - UTN FRCU 2026.
echo ==============================================================================
echo.
exit /b 0

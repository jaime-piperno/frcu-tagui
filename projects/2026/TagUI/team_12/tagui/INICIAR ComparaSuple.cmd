@echo off
setlocal
set "PYTHONUTF8=1"
if defined COMPARASUPLE_PYTHON goto python_configurado
call :probar_python py -3
if not errorlevel 1 goto ejecutar
call :probar_python python
if not errorlevel 1 goto ejecutar
echo No se encontro Python 3.10 o superior. Instalalo y habilita su acceso desde la terminal.
set "COMPARASUPLE_EXIT=1"
goto terminar

:python_configurado
call :probar_python "%COMPARASUPLE_PYTHON%"
if not errorlevel 1 goto ejecutar
echo COMPARASUPLE_PYTHON no apunta a un Python 3.10 o superior. Corregi la ruta configurada.
set "COMPARASUPLE_EXIT=1"
goto terminar

:ejecutar
if not exist "%~dp0ComparaSuple\codigo\main.py" (
  echo Falta ComparaSuple\codigo\main.py junto a este archivo. Copia el proyecto completo.
  set "COMPARASUPLE_EXIT=1"
  goto terminar
)
call :probar_openpyxl
if not errorlevel 1 goto iniciar
echo Falta instalar o actualizar openpyxl en el Python seleccionado.
choice /c SN /m "Instalarlo ahora con pip"
if errorlevel 2 goto sin_openpyxl
"%COMPARASUPLE_EXE%" %COMPARASUPLE_FLAGS% -m pip install -r "%~dp0ComparaSuple\requirements.txt"
call :probar_openpyxl
if not errorlevel 1 goto iniciar

:sin_openpyxl
echo No se pudo usar openpyxl. Instalalo manualmente con:
echo "%COMPARASUPLE_EXE%" %COMPARASUPLE_FLAGS% -m pip install -r "%~dp0ComparaSuple\requirements.txt"
set "COMPARASUPLE_EXIT=1"
goto terminar

:iniciar
"%COMPARASUPLE_EXE%" %COMPARASUPLE_FLAGS% -B "%~dp0ComparaSuple\codigo\main.py" --menu
set "COMPARASUPLE_EXIT=%ERRORLEVEL%"
if not "%COMPARASUPLE_EXIT%"=="0" if not "%COMPARASUPLE_EXIT%"=="130" echo No se pudo completar la ejecucion. Revisar el mensaje anterior.

:terminar
pause
exit /b %COMPARASUPLE_EXIT%

:probar_python
"%~1" %~2 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 exit /b 1
set "COMPARASUPLE_EXE=%~1"
set "COMPARASUPLE_FLAGS=%~2"
exit /b 0

:probar_openpyxl
"%COMPARASUPLE_EXE%" %COMPARASUPLE_FLAGS% -c "import openpyxl; from openpyxl.workbook.properties import CalcProperties" >nul 2>&1
exit /b %ERRORLEVEL%

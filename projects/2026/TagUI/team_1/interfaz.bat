@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul
title RPA Web Dashboard - UTN FRCU

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

if not exist "node_modules\express" (
    echo [INFO] Instalando dependencias de la interfaz web...
    call npm install
)

echo ==============================================================================
echo Iniciando Servidor del Bot RPA (Web UI)...
echo Por favor, no cierres esta ventana mientras uses el sistema.
echo ==============================================================================

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

start /B node server.js
ping 127.0.0.1 -n 3 >nul 2>&1
start http://localhost:3000

echo.
echo La interfaz se ha abierto en tu navegador.
echo (http://localhost:3000)
echo.
echo Presiona cualquier tecla para detener el servidor y salir...
pause >nul

taskkill /F /IM node.exe >nul 2>&1
exit /b 0
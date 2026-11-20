@echo off
setlocal
title Conciliador RPA Mercado Pago
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo   Conciliador RPA Mercado Pago - Web + Bot de Telegram
echo ============================================================
echo.

docker info >nul 2>&1
if %ERRORLEVEL% equ 0 goto :docker
goto :local

:docker
echo [OK] Docker detectado. Levantando la web y el bot de Telegram...
docker compose up -d --build
if errorlevel 1 goto :error_docker
echo.
echo [OK] Abriendo el navegador en http://localhost:8000 ...
timeout /t 3 /nobreak >nul
start "" http://localhost:8000
echo.
echo Servicios activos en segundo plano: web y bot de Telegram.
echo Para detenerlos, ejecuta detener.bat o "docker compose down".
goto :fin

:error_docker
echo [ERROR] No se pudieron levantar los contenedores. Revisa el mensaje anterior.
goto :fin

:local
echo [INFO] Docker no esta en ejecucion. Iniciando en modo local con Python...
where python >nul 2>&1
if errorlevel 1 goto :sin_python

echo [..] Instalando dependencias, puede tardar la primera vez...
python -m pip install -q -r requirements.txt
if errorlevel 1 goto :error_pip

findstr /r /c:"^TELEGRAM_TOKEN=[0-9]" .env >nul 2>&1
if errorlevel 1 goto :sin_bot
echo [OK] Iniciando el bot de Telegram en otra ventana...
start "Bot Telegram - Conciliador" cmd /k python bot.py
goto :web_local

:sin_bot
echo [INFO] No hay TELEGRAM_TOKEN en .env: se inicia solo la web, sin el bot de Telegram.

:web_local
echo [OK] Iniciando la web en http://localhost:8000
echo      Para detener todo: Ctrl+C en esta ventana y cerrar la ventana del bot, o ejecutar detener.bat.
start "" /min cmd /c "timeout /t 5 /nobreak >nul & start http://localhost:8000"
python -m uvicorn app:app --host 127.0.0.1 --port 8000
goto :fin

:sin_python
echo [ERROR] No se encontro Python. Abri Docker Desktop o instala Python 3.11 o superior.
goto :fin

:error_pip
echo [ERROR] Fallo la instalacion de dependencias. Revisa el mensaje anterior.
goto :fin

:fin
echo.
pause

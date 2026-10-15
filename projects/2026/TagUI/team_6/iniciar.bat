@echo off
title Conciliador RPA Mercado Pago
chcp 65001 >nul

echo ============================================================
echo   Iniciando Servidor Web - RPA Conciliador Mercado Pago
echo ============================================================
echo.

docker info >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [OK] Docker detectado. Levantando contenedor...
    docker compose up -d --build
    echo.
    echo [OK] Abriendo navegador en http://localhost:8000 ...
    timeout /t 2 >nul
    start http://localhost:8000
    echo.
    echo El servicio está activo en segundo plano.
    echo Para detenerlo, ejecuta detener.bat o 'docker compose down'.
) else (
    echo [INFO] Docker no está en ejecución. Iniciando en modo local con Python...
    pip install -r requirements.txt >nul 2>&1
    echo [OK] Abriendo navegador en http://localhost:8000 ...
    start http://localhost:8000
    python -m uvicorn app:app --host 0.0.0.0 --port 8000
)

echo.
pause

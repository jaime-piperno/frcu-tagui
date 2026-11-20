@echo off
title Detener RPA Mercado Pago
chcp 65001 >nul
cd /d "%~dp0"

docker info >nul 2>&1
if %ERRORLEVEL% neq 0 goto :local
echo Deteniendo los contenedores de Docker...
docker compose down

:local
taskkill /fi "WINDOWTITLE eq Bot Telegram - Conciliador*" /t /f >nul 2>&1
if %ERRORLEVEL% equ 0 echo [OK] Bot de Telegram local detenido.
taskkill /fi "WINDOWTITLE eq Conciliador RPA Mercado Pago*" /t /f >nul 2>&1
if %ERRORLEVEL% equ 0 echo [OK] Servidor web local detenido.

echo [OK] Servicios detenidos.
timeout /t 2 >nul

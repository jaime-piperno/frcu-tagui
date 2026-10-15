@echo off
title Detener RPA Mercado Pago
chcp 65001 >nul

echo Deteniendo contenedor de Docker...
docker compose down
echo [OK] Contenedor detenido correctamente.
timeout /t 2 >nul

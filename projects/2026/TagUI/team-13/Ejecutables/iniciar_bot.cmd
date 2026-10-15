@echo off
rem Lanzador para Windows. Doble click para prender el bot de compras.
rem Mientras esta ventana este abierta, el bot atiende en Telegram.
rem Usa "py" (el lanzador de Python para Windows) y si no existe, "python".
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py bot.py) else (python bot.py)
echo.
pause

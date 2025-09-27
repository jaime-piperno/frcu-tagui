@echo off
REM PapperNewsWhatsapp.bat - Script principal para envío a WhatsApp en Windows

echo ====================================================================
echo PAPER NEWS WHATSAPP - Procesamiento automatizado para Windows
echo ====================================================================

echo [1/3] Extrayendo papers de arXiv...
start "Extraccion Papers" /wait cmd /c "tagui AutoPapper.tag IN\xpaths.csv -t"
if %errorlevel% neq 0 (
    echo ❌ ERROR: Falló la extracción de papers de arXiv
    pause
    exit /b 1
)

echo [2/3] Generando prompts para IA...
python generar_prompts.py OUT\AutoPapper.csv OUT\Prompts.csv
if %errorlevel% neq 0 (
    echo ❌ ERROR: Falló la generación de prompts
    pause
    exit /b 1
)

echo [3/3] Procesando con IA y enviando a WhatsApp...
echo ⚠️  NOTA: Asegúrate de tener WhatsApp Web abierto y logueado en el perfil de TagUI
start "Procesamiento IA y WhatsApp" /wait cmd /c "tagui AIOverview.tag -t"
if %errorlevel% neq 0 (
    echo ❌ ERROR: Falló el procesamiento y envío a WhatsApp
    pause
    exit /b 1
)

echo Limpiando archivos temporales...
del OUT\Prompts.csv OUT\AutoPapper.csv 2>nul

echo ====================================================================
echo ✅ PROCESAMIENTO Y ENVÍO COMPLETADO
echo ====================================================================
echo Papers enviados al grupo WhatsApp configurado
echo ====================================================================
pause
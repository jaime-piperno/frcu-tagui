@echo off
REM PapperNewsHTML.bat - Script principal para generar portal HTML en Windows

echo ====================================================================
echo PAPER NEWS HTML - Procesamiento automatizado para Windows
echo ====================================================================

echo [1/4] Extrayendo papers de arXiv...
start "Extraccion Papers" /wait cmd /c "tagui AutoPapper.tag IN\xpaths.csv -t"
if %errorlevel% neq 0 (
    echo ❌ ERROR: Falló la extracción de papers
    pause
    exit /b 1
)

echo [2/4] Generando prompts para IA...
python generar_prompts.py OUT\AutoPapper.csv OUT\Prompts.csv
if %errorlevel% neq 0 (
    echo ❌ ERROR: Falló la generación de prompts
    pause
    exit /b 1
)

echo [3/4] Procesando con IA y generando CSV...
start "Procesamiento IA y CSV" /wait cmd /c "tagui AICSV.tag -t"
if %errorlevel% neq 0 (
    echo ❌ ERROR: Falló el procesamiento con IA
    pause
    exit /b 1
)

echo [4/4] Creando portal HTML...
python generar_portal.py OUT\ProcessedPapers.csv portal_noticias.html
if %errorlevel% neq 0 (
    echo ❌ ERROR: Falló la generación del portal
    pause
    exit /b 1
)

echo Limpiando archivos temporales...
del OUT\Prompts.csv OUT\AutoPapper.csv OUT\ProcessedPapers.csv 2>nul

echo ====================================================================
echo ✅ PROCESAMIENTO COMPLETADO
echo ====================================================================
echo Portal generado: portal_noticias.html
echo ====================================================================
pause
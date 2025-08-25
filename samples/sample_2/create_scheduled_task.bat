@echo off
REM Get the current script's directory
set "SCRIPT_DIR=%~dp0"

REM Create scheduled task to run every 1 minute
schtasks /create ^
 /tn "TagUI FRCU Sample 2" ^
 /tr "\"cmd.exe\" /c \"\"%SCRIPT_DIR%run_tagui.bat\"\"" ^
 /sc minute ^
 /mo 1 ^
 /f

echo Scheduled task created successfully.
echo It is recommended to disable option "Start the task only if the computer is on AC power" in the task properties.
pause

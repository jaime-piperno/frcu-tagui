@echo off
call tagui resumen_diario.tag
call python send_resumen.py
pause

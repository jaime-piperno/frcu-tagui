@echo off
REM Runs sample_2.tag with TagUI
REM Make sure tagui is in the PATH env variables
REM Optional parameter -headless

REM Set current directory to script location so relative paths are resolved properly
cd /d "%~dp0"
tagui sample_2.tag -chrome

REM This is an alternative way with absolute path
REM tagui "C:/Users/UTN FRCU/Desktop/dev/samples/sample_2/sample_2.tag" -chrome
@echo off
setlocal

REM Ejecuta checks diarios de confiabilidad
cd /d "%~dp0"
python jobs_operativos.py --mode daily
exit /b %errorlevel%

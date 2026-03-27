@echo off
setlocal

REM Ejecuta restore test semanal de backups
cd /d "%~dp0"
python jobs_operativos.py --mode weekly-restore
exit /b %errorlevel%

@echo off
REM ===================================================================
REM BACKUP AUTOMÁTICO - North Chrome
REM Ejecutar con: powershell -ExecutionPolicy Bypass -File backup_automatico.ps1
REM O configurar en Task Scheduler para ejecutar diariamente
REM ===================================================================

setlocal enabledelayedexpansion

REM Configurar rutas
set SOURCE_DB=C:\Users\bodega.NORTHCHROME\Downloads\north_chrome2\north_chrome\system\system.db
set BACKUP_DIR=C:\Users\bodega.NORTHCHROME\Downloads\north_chrome2\north_chrome\system\backups
set LOG_FILE=%BACKUP_DIR%\backup.log

REM Crear carpeta de backups si no existe
if not exist "%BACKUP_DIR%" (
    mkdir "%BACKUP_DIR%"
    echo [%DATE% %TIME%] Carpeta de backups creada >> "%LOG_FILE%"
)

REM Crear nombre de archivo con timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set BACKUP_FILE=%BACKUP_DIR%\system_%mydate%_%mytime%.db.backup

REM Copiar base de datos
echo [%DATE% %TIME%] Iniciando backup... >> "%LOG_FILE%"
copy "%SOURCE_DB%" "%BACKUP_FILE%" 1>nul 2>>"%LOG_FILE%"

if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR al copiar BD >> "%LOG_FILE%"
    exit /b 1
) else (
    echo [%DATE% %TIME%] Backup creado exitosamente: %BACKUP_FILE% >> "%LOG_FILE%"
)

REM Limpiar backups antiguos (mantener últimos 30 días)
echo [%DATE% %TIME%] Limpiando backups antiguos... >> "%LOG_FILE%"
for /f %%a in ('powershell Get-Date ^(Get-Date^).AddDays^(-30^) -Format yyyyMMdd') do set DELETE_DATE=%%a

for /f "delims=" %%f in ('dir /b "%BACKUP_DIR%\system_*.db.backup" ^| findstr /v nul') do (
    for /f "tokens=2 delims=_" %%d in ("%%f") do (
        if %%d LSS !DELETE_DATE! (
            del "%BACKUP_DIR%\%%f" 2>>"%LOG_FILE%"
            echo [%DATE% %TIME%] Backup antiguo eliminado: %%f >> "%LOG_FILE%"
        )
    )
)

echo [%DATE% %TIME%] Backup completado >> "%LOG_FILE%"
echo.
echo ===== BACKUP COMPLETADO =====
echo Archivo: %BACKUP_FILE%
echo Log: %LOG_FILE%
echo.
pause

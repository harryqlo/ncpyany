@echo off
echo ============================================
echo   North Chrome - Instalacion Automatica
echo ============================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado.
    echo.
    echo Descargalo desde: https://www.python.org/downloads/
    echo IMPORTANTE: Marca la casilla "Add Python to PATH" al instalar.
    echo.
    pause
    exit /b
)

echo [OK] Python encontrado
echo.
echo Instalando Flask (libreria del servidor web)...
pip install flask
echo.

if not exist "system" mkdir system

if exist "system\system.db" (
    echo [OK] Base de datos encontrada en system\system.db
) else (
    echo [AVISO] No se encontro system\system.db
    echo Copia tu archivo system.db dentro de la carpeta "system"
)

echo.
echo ============================================
echo   Instalacion completada!
echo.
echo   Para iniciar el sistema ejecuta:
echo   iniciar.bat
echo ============================================
echo.
pause

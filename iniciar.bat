@echo off
setlocal

set "PYTHON_EXE=.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
	where python >nul 2>nul
	if errorlevel 1 (
		echo.
		echo [ERROR] No se encontro Python ni el entorno .venv.
		echo Ejecuta primero instalar.bat
		echo.
		pause
		exit /b 1
	)
	set "PYTHON_EXE=python"
)

echo.
echo   ========================================
echo     North Chrome - Sistema de Bodega
echo   ========================================
echo.
echo   Iniciando servidor...
echo   Abre tu navegador en: http://localhost:5000
echo.
echo   Para detener: presiona Ctrl+C
echo   ========================================
echo.
start http://localhost:5000
%PYTHON_EXE% run.py
if errorlevel 1 (
	echo.
	echo [ERROR] El servidor se detuvo con error.
)
pause

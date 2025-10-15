@echo off
REM Wrapper para ejecutar el orquestador desde un doble click en Windows.
set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..\
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%setup_windows.ps1" %*
if %errorlevel% neq 0 (
    echo PowerShell devolvió un error. Si ves un mensaje de politica de ejecucion, ejecuta: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
)
pause

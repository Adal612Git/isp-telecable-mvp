@echo off
setlocal
REM Wrapper de nivel raiz para facilitar la ejecucion de setup en Windows.
set SCRIPT_DIR=%~dp0
if not defined SCRIPT_DIR set SCRIPT_DIR=.

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\setup_windows.ps1" %*
set EXITCODE=%ERRORLEVEL%

if %EXITCODE% neq 0 (
    echo PowerShell devolvio el codigo %EXITCODE%. Revisa el resultado mostrado arriba o logs\setup.log.
)

endlocal & exit /b %EXITCODE%


@echo off
setlocal EnableExtensions EnableDelayedExpansion

for %%i in ("%~dp0..") do set "REPO_ROOT=%%~fi"
if not exist "%REPO_ROOT%" (
    echo [FAIL ] No se pudo ubicar el directorio del proyecto.
    exit /b 1
)
cd /d "%REPO_ROOT%"
set "LOG_DIR=%REPO_ROOT%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "REPORT=%LOG_DIR%\setup_report.txt"

echo [INFO ] Iniciando Telecable MVP (Windows)...

where docker >nul 2>nul || (
    echo [FAIL ] Docker no esta instalado.
    exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
    echo [FAIL ] Docker Desktop no esta en ejecucion. Inicia Docker Desktop y vuelve a intentarlo.
    exit /b 1
)
where "docker compose" >nul 2>nul
if errorlevel 1 (
    where docker-compose >nul 2>nul || (
        echo [FAIL ] No se encontro docker compose.
        exit /b 1
    )
    set "COMPOSE=docker-compose"
) else (
    set "COMPOSE=docker compose"
)

where bash >nul 2>nul || (
    echo [FAIL ] Se requiere Git Bash para ejecutar scripts auxiliares.
    exit /b 1
)

echo [INFO ] Liberando puertos base...
for %%P in (5173 5174 8091 3000 9090) do (
    set "PORT_FOUND="
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr /R /C:":%%P "') do (
        set "PID=%%a"
        if defined PID (
            if "!PID!"=="0" (
                echo [INFO ] Puerto %%P asociado a PID 0 ^(se omite^).
            ) else (
                echo [WARN ] Puerto %%P ocupado. Terminando PID !PID!
                taskkill /PID !PID! /F >nul 2>&1
            )
            set "PORT_FOUND=1"
        )
    )
    if "!PORT_FOUND!"=="" (
        echo [INFO ] Puerto %%P libre.
    )
)

if not exist .env (
    if exist .env.example (
        echo [INFO ] Generando .env desde .env.example
        copy /y .env.example .env >nul
    ) else (
        echo [FAIL ] No existe .env ni .env.example.
        exit /b 1
    )
) else (
    echo [INFO ] .env detectado. Se reutiliza.
)

if exist .env.ports (
    echo [INFO ] Deteniendo stack previo ^(docker compose down^)...
    %COMPOSE% --env-file .env.ports -f infra/docker-compose.yml -f docker-compose.yml down --remove-orphans >nul 2>&1
)

echo [INFO ] Asignando puertos (.env.ports)...
bash scripts/allocate_ports.sh --write .env.ports --force --quiet
if errorlevel 1 (
    echo [FAIL ] No se pudo generar .env.ports
    exit /b 1
)

echo [INFO ] Levantando contenedores...
%COMPOSE% --env-file .env.ports -f infra/docker-compose.yml -f docker-compose.yml up -d --build
if errorlevel 1 (
    echo [FAIL ] docker compose up fallo
    exit /b 1
)

%COMPOSE% --env-file .env.ports -f infra/docker-compose.yml -f docker-compose.yml ps > "%LOG_DIR%\compose_status.txt"

for %%V in (HOST_PORTAL_CLIENTE_PORT HOST_PORTAL_TECNICO_PORT HOST_PORTAL_FACTURACION_PORT HOST_BACKOFFICE_PORT HOST_GRAFANA_PORT HOST_PROMETHEUS_PORT) do set "%%V="
for /f "tokens=1,2 delims==" %%A in (.env.ports) do (
    if /I "%%A"=="HOST_PORTAL_CLIENTE_PORT" set "HOST_PORTAL_CLIENTE_PORT=%%B"
    if /I "%%A"=="HOST_PORTAL_TECNICO_PORT" set "HOST_PORTAL_TECNICO_PORT=%%B"
    if /I "%%A"=="HOST_PORTAL_FACTURACION_PORT" set "HOST_PORTAL_FACTURACION_PORT=%%B"
    if /I "%%A"=="HOST_BACKOFFICE_PORT" set "HOST_BACKOFFICE_PORT=%%B"
    if /I "%%A"=="HOST_GRAFANA_PORT" set "HOST_GRAFANA_PORT=%%B"
    if /I "%%A"=="HOST_PROMETHEUS_PORT" set "HOST_PROMETHEUS_PORT=%%B"
)

set "HOST_PORTAL_CLIENTE_PORT=%HOST_PORTAL_CLIENTE_PORT: =%"
set "HOST_PORTAL_TECNICO_PORT=%HOST_PORTAL_TECNICO_PORT: =%"
set "HOST_PORTAL_FACTURACION_PORT=%HOST_PORTAL_FACTURACION_PORT: =%"
set "HOST_BACKOFFICE_PORT=%HOST_BACKOFFICE_PORT: =%"
set "HOST_GRAFANA_PORT=%HOST_GRAFANA_PORT: =%"
set "HOST_PROMETHEUS_PORT=%HOST_PROMETHEUS_PORT: =%"

echo ============================================== > "%REPORT%"
echo Telecable MVP - Resumen setup (Windows) >> "%REPORT%"
for /f "tokens=1,2 delims==" %%A in ('wmic os get localdatetime /value ^| find "LocalDateTime"') do set "LDT=%%B"
if defined LDT (
    set "DATE_STR=%LDT:~0,4%-%LDT:~4,2%-%LDT:~6,2% %LDT:~8,2%:%LDT:~10,2%:%LDT:~12,2%"
) else (
    set "DATE_STR=%date% %time%"
)
echo Finalizado: %DATE_STR% >> "%REPORT%"
echo. >> "%REPORT%"
echo Contenedores: >> "%REPORT%"
type "%LOG_DIR%\compose_status.txt" >> "%REPORT%"
echo. >> "%REPORT%"
echo Puertos asignados (.env.ports): >> "%REPORT%"
type .env.ports >> "%REPORT%"
echo. >> "%REPORT%"
echo Accesos: >> "%REPORT%"
echo  - Portal Cliente:      http://localhost:%HOST_PORTAL_CLIENTE_PORT% >> "%REPORT%"
echo  - Portal Tecnico:      http://localhost:%HOST_PORTAL_TECNICO_PORT% >> "%REPORT%"
echo  - Portal Facturacion:  http://localhost:%HOST_PORTAL_FACTURACION_PORT% >> "%REPORT%"
echo  - Backoffice:          http://localhost:%HOST_BACKOFFICE_PORT% >> "%REPORT%"
echo  - Grafana:             http://localhost:%HOST_GRAFANA_PORT% >> "%REPORT%"
echo  - Prometheus:          http://localhost:%HOST_PROMETHEUS_PORT% >> "%REPORT%"
echo ============================================== >> "%REPORT%"

echo [INFO ] Resumen guardado en %REPORT%
echo [INFO ] Mostrando logs combinados (Ctrl+C para detener)...
%COMPOSE% --env-file .env.ports -f infra/docker-compose.yml -f docker-compose.yml logs -f --tail=200

endlocal

@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "NOPAUSE=0"
if not "%~1"=="" goto parse_args
goto args_done

:parse_args
if /i "%~1"=="--no-pause" (
    set "NOPAUSE=1"
    shift
    goto parse_args
)
if /i "%~1"=="--help" (
    call :usage
    exit /b 0
)
echo Uso: %~nx0 [--no-pause]
exit /b 1

:args_done

set "EXIT_CODE=0"
set "PUSHED=0"
set "SCRIPT_DIR=%~dp0"

for %%i in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fi"
if exist "%REPO_ROOT%\docker-compose.yml" (
    pushd "%REPO_ROOT%"
    set "PUSHED=1"
) else (
    if exist "%REPO_ROOT%\isp-telecable-mvp\docker-compose.yml" (
        set "REPO_ROOT=%REPO_ROOT%\isp-telecable-mvp"
        pushd "!REPO_ROOT!"
        set "PUSHED=1"
    ) else (
        call :error No se encontro docker-compose.yml. Ejecuta este script desde la carpeta scripts del proyecto.
        goto fatal
    )
)
for %%i in (.) do set "REPO_ROOT=%%~fi"

call :banner
call :info Directorio detectado: %REPO_ROOT%

REM --- Verificar requisitos ---
call :require_cmd docker "No se encontro Docker en PATH. Instala Docker Desktop y vuelve a ejecutar este script."
if errorlevel 1 goto fatal

docker info >nul 2>&1
if errorlevel 1 (
    call :error Docker Desktop no responde. Asegurate de que Docker este en ejecucion.
    goto fatal
)
call :ok Docker responde correctamente.

docker compose version >nul 2>&1
if errorlevel 1 (
    call :error No se encontro 'docker compose'. Actualiza Docker Desktop o habilita el plugin de Compose.
    goto fatal
)
call :ok Docker Compose disponible.

where bash >nul 2>&1
if errorlevel 1 (
    call :error No se encontro 'bash'. Instala Git Bash o habilita WSL para ejecutar los scripts auxiliares.
    goto fatal
)
call :ok Bash disponible (Git Bash o WSL).

REM --- Preparar archivos de entorno ---
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        if errorlevel 1 (
            call :error No se pudo copiar .env.example a .env. Revisa permisos del directorio.
            goto fatal
        )
        call :ok Archivo .env generado desde .env.example.
    ) else (
        call :error No existe .env ni .env.example. Agrega uno manualmente y vuelve a ejecutar.
        goto fatal
    )
) else (
    call :info .env ya existe, se reutilizara.
)

call :info Levantando infraestructura con scripts\up.ps1 (puede tardar)...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\up.ps1" -EnvFile ".env.ports"
if errorlevel 1 (
    call :error scripts\up.ps1 fallo. Revisa la salida anterior para más detalle.
    goto fatal
)
call :ok Servicios levantados correctamente.

if not exist ".env.ports" (
    call :error No se encontro .env.ports tras ejecutar scripts\up.ps1.
    goto fatal
)

REM Cargar variables principales desde .env.ports para mensajes finales
for /f "usebackq tokens=1,2 delims==" %%A in (".env.ports") do (
    set "line=%%A"
    if defined line (
        if not "!line:~0,1!"=="#" (
            set "%%A=%%B"
        )
    )
)

set "WSLENV_PORT_VARS=HOST_CLIENTES_PORT:HOST_CATALOGO_PORT:HOST_FACTURACION_PORT:HOST_PAGOS_PORT:HOST_WHATSAPP_PORT:HOST_ORQ_PORT:HOST_PORTAL_PORT:HOST_BACKOFFICE_PORT:HOST_POSTGRES_PORT:HOST_REDIS_PORT:HOST_ZOOKEEPER_PORT:HOST_KAFKA_PORT_1:HOST_KAFKA_PORT_2:HOST_KEYCLOAK_PORT:HOST_JAEGER_UI_PORT:HOST_JAEGER_THRIFT_PORT:HOST_OTLP_GRPC_PORT:HOST_OTLP_HTTP_PORT:HOST_PROMETHEUS_PORT:HOST_GRAFANA_PORT:HOST_LOKI_PORT:HOST_TEMPO_PORT:HOST_MINIO_API_PORT:HOST_MINIO_CONSOLE_PORT"
if defined WSLENV (
    set "WSLENV=%WSLENV_PORT_VARS%:!WSLENV!"
) else (
    set "WSLENV=%WSLENV_PORT_VARS%"
)
set "WSLENV_PORT_VARS="

REM --- Seed de datos ---
call :info Ejecutando seed de datos de prueba...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\seed.ps1" -EnvFile ".env.ports"
if errorlevel 1 (
    call :error scripts\seed.ps1 fallo. Revisa el contenedor infra-postgres y la salida anterior.
    goto fatal
)
call :ok Seed completado.

REM --- Resumen final ---
call :info Resumen de contenedores activos:
docker compose --env-file ".env.ports" -f "infra/docker-compose.yml" -f "docker-compose.yml" ps
if errorlevel 1 (
    call :warn No se pudo obtener el listado de contenedores. Ejecuta 'docker compose ps' manualmente.
)

call :success Proceso finalizado.
call :info Portal Cliente: http://localhost:!HOST_PORTAL_PORT!
call :info Backoffice: http://localhost:!HOST_BACKOFFICE_PORT!
goto end

:fatal
set "EXIT_CODE=1"
call :fail Setup interrumpido. Corrige el error anterior y vuelve a ejecutar scripts\setup_windows.bat.
goto end

:end
set "__EXIT_CODE=%EXIT_CODE%"
if "%PUSHED%"=="1" popd
if "%NOPAUSE%"=="0" call :pause_if_needed %__EXIT_CODE%
endlocal & exit /b %__EXIT_CODE%

REM ===========================
REM  Funciones auxiliares
REM ===========================
:usage
echo.
echo Uso: %~nx0 [--no-pause]
echo    --no-pause    Omite la pausa final (para terminales ya abiertas).
goto :eof

:banner
echo ============================================================
echo    ISP Telecable MVP - Setup Automatizado para Windows
echo ============================================================
goto :eof

:info
echo [INFO ] %*
goto :eof

:ok
echo [ OK  ] %*
goto :eof

:warn
echo [WARN ] %*
goto :eof

:error
echo [ERROR] %*
goto :eof

:success
echo [DONE ] %*
goto :eof

:fail
echo [FAIL ] %*
goto :eof

:pause_if_needed
echo.
if "%~1"=="0" (
    echo Presiona una tecla para cerrar esta ventana...
) else (
    echo Presiona una tecla para revisar el error...
)
pause >nul
goto :eof

:require_cmd
where %~1 >nul 2>&1
if errorlevel 1 (
    call :error %~2
    exit /b 1
)
exit /b 0

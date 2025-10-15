[CmdletBinding()]
param(
    [string]$EnvFile = '.env.ports',
    [switch]$ForcePorts
)

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) {
    $EnvFile
} else {
    Join-Path $root $EnvFile
}

& "$PSScriptRoot/allocate_ports.ps1" -OutFile $envPath -Force:$ForcePorts -Quiet
$envMap = Read-EnvFile -Path $envPath -UpdateProcessEnv

$reportDir = Join-Path $root 'Tests/reports'
Ensure-ReportLayout -Root $reportDir

& "$PSScriptRoot/db_reset.ps1" | Out-Null

Push-Location $root
try {
    Invoke-DockerCompose -EnvFile $envPath -ExtraArgs @('restart', 'clientes', 'catalogo', 'facturacion', 'pagos', 'orquestador') | Out-Null
} catch {
    # Restart es mejor-esfuerzo; continuamos aunque falle.
}
Pop-Location

Start-Sleep -Seconds 3

$clientesPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_CLIENTES_PORT' -Default '8000')
$catalogoPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_CATALOGO_PORT' -Default '8001')
$factPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_FACTURACION_PORT' -Default '8002')
$pagosPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_PAGOS_PORT' -Default '8003')
$orqPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_ORQ_PORT' -Default '8010')
$waPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_WHATSAPP_PORT' -Default '8011')

Write-Status -Level 'RUN' -Message 'Esperando servicios principales (clientes, catalogo, facturacion, pagos, orquestador, whatsapp)...'
$healthUrls = @(
    "http://localhost:$clientesPort/health",
    "http://localhost:$catalogoPort/health",
    "http://localhost:$factPort/health",
    "http://localhost:$pagosPort/health",
    "http://localhost:$orqPort/health",
    "http://localhost:$waPort/health"
)

foreach ($url in $healthUrls) {
    if (-not (Wait-ForEndpoint -Url $url -Retries 30 -DelaySeconds 2)) {
        throw "Timeout esperando $url"
    }
}

Write-Status -Level 'RUN' -Message 'Pytest (integration) contra servicios docker...'
$dockerVolume = "$root:/work"
$envArgs = @(
    '-e', "HOST_CLIENTES_PORT=$clientesPort",
    '-e', "HOST_CATALOGO_PORT=$catalogoPort",
    '-e', "HOST_FACTURACION_PORT=$factPort",
    '-e', "HOST_PAGOS_PORT=$pagosPort",
    '-e', "HOST_ORQ_PORT=$orqPort",
    '-e', "HOST_WHATSAPP_PORT=$waPort"
)
$pytestCmd = @'
pip install -r requirements-test.txt && \
pytest -q --junitxml=Tests/reports/junit-int.xml --html=Tests/reports/integration.html --self-contained-html Tests/integration
'@

& docker run --rm --network=host @envArgs -v $dockerVolume -w /work python:3.11-slim bash -lc $pytestCmd

Write-Status -Level 'OK' -Message 'Integration tests OK.'

# HAR-style resumen
Write-Status -Level 'RUN' -Message 'Generando métricas adicionales (HAR/CSV)...'
$harEntries = @()
$csvEntries = @()
$targets = @(
    @{ Url = "http://localhost:$clientesPort/health"; Label = '/clientes/health' },
    @{ Url = "http://localhost:$catalogoPort/planes"; Label = '/catalogo/planes' },
    @{ Url = "http://localhost:$factPort/health"; Label = '/facturacion/health' }
)

foreach ($target in $targets) {
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
    $statusCode = 0
    try {
        $response = Invoke-WebRequest -Uri $target.Url -UseBasicParsing -TimeoutSec 10
        $statusCode = [int]$response.StatusCode
    } catch {
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode.value__
        } else {
            $statusCode = 0
        }
    }
    $stopwatch.Stop()
    $elapsed = [Math]::Round($stopwatch.Elapsed.TotalSeconds, 3)
    $harEntries += [pscustomobject]@{
        url = $target.Url
        code = $statusCode
        time_total = $elapsed
    }
    $csvEntries += [pscustomobject]@{
        endpoint = $target.Label
        time_total = $elapsed
    }
}

$harPath = Join-Path $reportDir 'har/integration.har'
$harObject = @{ entries = $harEntries }
$harObject | ConvertTo-Json -Depth 5 | Set-Content -Path $harPath -Encoding utf8

$csvPath = Join-Path $reportDir 'csv/times.csv'
$csvLines = @('endpoint,time_total')
$csvLines += ($csvEntries | ForEach-Object { '{0},{1}' -f $_.endpoint, $_.time_total })
Set-Content -Path $csvPath -Value $csvLines -Encoding ascii

# CFDIs masivos
Write-Status -Level 'RUN' -Message 'Generando CSV de 100 CFDIs...'
$cfdiPayload = for ($i = 0; $i -lt 100; $i++) {
    @{ cliente_id = 1; total = 100.0 }
}
$cfdiPath = Join-Path $reportDir 'csv/cfdis_100.csv'
Invoke-WebRequest -Uri "http://localhost:$factPort/facturacion/generar-masiva?csv=1" `
    -Method Post `
    -ContentType 'application/json' `
    -Body (ConvertTo-Json -InputObject $cfdiPayload -Depth 3) `
    -OutFile $cfdiPath

# Conciliación a CSV
Write-Status -Level 'RUN' -Message 'Generando conciliación CSV...'
$concResponse = Invoke-RestMethod -Uri "http://localhost:$pagosPort/pagos/conciliar" -Method Get
if ($concResponse.csv) {
    $concPath = Join-Path $reportDir 'csv/conciliacion.csv'
    Set-Content -Path $concPath -Value $concResponse.csv -Encoding utf8
}

Write-Status -Level 'DONE' -Message 'Integration suite completada.'

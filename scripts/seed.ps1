[CmdletBinding()]
param(
    [string]$EnvFile = '.env.ports'
)

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) {
    $EnvFile
} else {
    Join-Path $root $EnvFile
}

$envMap = Read-EnvFile -Path $envPath -UpdateProcessEnv
$reportDir = Join-Path $root 'Tests/reports'
Ensure-Directory -Path (Join-Path $reportDir 'json')

$clientesPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_CLIENTES_PORT' -Default '8000')
$catalogoPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_CATALOGO_PORT' -Default '8001')
$factPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_FACTURACION_PORT' -Default '8002')
$orqPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_ORQ_PORT' -Default '8010')

Write-Status -Level 'RUN' -Message 'Esperando servicios (catalogo, clientes, facturacion, orquestador)...'
$healthUrls = @(
    "http://localhost:$catalogoPort/health",
    "http://localhost:$clientesPort/health",
    "http://localhost:$factPort/health",
    "http://localhost:$orqPort/health"
)

foreach ($url in $healthUrls) {
    if (-not (Wait-ForEndpoint -Url $url -Retries 30 -DelaySeconds 2)) {
        throw "Timeout esperando $url"
    }
}

Write-Status -Level 'RUN' -Message 'Creando cliente de prueba vía orquestador...'
$cid = ([guid]::NewGuid().ToString())
$payload = @{
    nombre = 'Juan Pérez'
    rfc = 'AAA010101AAA'
    email = 'juan@example.com'
    telefono = '5555555555'
    plan_id = 'INT100'
    domicilio = @{
        calle = 'Av. 1'
        numero = '123'
        colonia = 'Centro'
        cp = '01000'
        ciudad = 'CDMX'
        estado = 'CDMX'
        zona = 'NORTE'
    }
    contacto = @{
        nombre = 'Juan Pérez'
        email = 'juan@example.com'
        telefono = '5555555555'
    }
    consentimiento = @{
        marketing = $true
        terminos = $true
    }
    idem = $cid
}

$payloadJson = $payload | ConvertTo-Json -Depth 6
$response = Invoke-RestMethod -Method Post `
    -Uri "http://localhost:$orqPort/saga/alta-cliente" `
    -ContentType 'application/json' `
    -Body $payloadJson

$outputPath = Join-Path $reportDir 'json/seed_alta_cliente.json'
$response | ConvertTo-Json -Depth 8 | Set-Content -Path $outputPath -Encoding utf8

Write-Status -Level 'DONE' -Message 'Seed completado.'


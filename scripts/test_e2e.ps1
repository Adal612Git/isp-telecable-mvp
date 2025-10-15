[CmdletBinding()]
param(
    [string]$EnvFile = '.env.ports',
    [switch]$SkipBuild,
    [switch]$PullImage
)

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) {
    $EnvFile
} else {
    Join-Path $root $EnvFile
}

& "$PSScriptRoot/allocate_ports.ps1" -OutFile $envPath -Quiet
$envMap = Read-EnvFile -Path $envPath -UpdateProcessEnv

$reportDir = Join-Path $root 'Tests/reports'
Ensure-ReportLayout -Root $reportDir

$services = @('postgres', 'catalogo', 'clientes', 'facturacion', 'orquestador', 'portal-cliente')
$composeArgs = @('up', '-d')
if (-not $SkipBuild.IsPresent) {
    $composeArgs += '--build'
}
$composeArgs += $services

Push-Location $root
try {
    Write-Status -Level 'RUN' -Message 'Asegurando servicios base para E2E...'
    Invoke-DockerCompose -EnvFile $envPath -ExtraArgs $composeArgs | Out-Null
} finally {
    Pop-Location
}

$portalPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_PORTAL_CLIENTE_PORT' -Default '5173')
$catalogoPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_CATALOGO_PORT' -Default '8001')
$orqPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_ORQ_PORT' -Default '8010')
$clientesPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_CLIENTES_PORT' -Default '8000')
$factPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_FACTURACION_PORT' -Default '8002')

Write-Status -Level 'RUN' -Message "Esperando portal en http://localhost:$portalPort ..."
if (-not (Wait-ForEndpoint -Url "http://localhost:$portalPort" -Retries 60 -DelaySeconds 1)) {
    throw "Portal no disponible en http://localhost:$portalPort"
}

Write-Status -Level 'RUN' -Message "Esperando catálogo en http://localhost:$catalogoPort/health ..."
if (-not (Wait-ForEndpoint -Url "http://localhost:$catalogoPort/health" -Retries 60 -DelaySeconds 1)) {
    throw "Catálogo no responde en http://localhost:$catalogoPort/health"
}

Write-Status -Level 'RUN' -Message 'Esperando catálogo /zonas...'
for ($i = 0; $i -lt 60; $i++) {
    try {
        $zones = Invoke-RestMethod -Uri "http://localhost:$catalogoPort/zonas" -TimeoutSec 5
        if ($zones) { break }
    } catch {
        Start-Sleep -Seconds 1
    }
    if ($i -eq 59) {
        throw 'No se pudo obtener /zonas de catálogo.'
    }
}

Write-Status -Level 'RUN' -Message "Esperando orquestador en http://localhost:$orqPort/health ..."
if (-not (Wait-ForEndpoint -Url "http://localhost:$orqPort/health" -Retries 60 -DelaySeconds 1)) {
    throw "Orquestador no responde en http://localhost:$orqPort/health"
}

Write-Status -Level 'RUN' -Message "Esperando clientes en http://localhost:$clientesPort/health ..."
if (-not (Wait-ForEndpoint -Url "http://localhost:$clientesPort/health" -Retries 60 -DelaySeconds 1)) {
    throw "Clientes no responde en http://localhost:$clientesPort/health"
}

Write-Status -Level 'RUN' -Message "Esperando facturación en http://localhost:$factPort/health ..."
if (-not (Wait-ForEndpoint -Url "http://localhost:$factPort/health" -Retries 60 -DelaySeconds 1)) {
    throw "Facturación no responde en http://localhost:$factPort/health"
}

# Detectar versión de Playwright
$packagePath = Join-Path $root 'Tests/e2e/package.json'
$pwVersion = $null
if (Test-Path $packagePath) {
    $packageJson = Get-Content -Path $packagePath -Raw | ConvertFrom-Json
    $candidate = $packageJson.devDependencies.'@playwright/test'
    if (-not $candidate) {
        $candidate = $packageJson.dependencies.'@playwright/test'
    }
    if ($candidate) {
        $pwVersion = ($candidate -replace '^[^\d]*', '')
    }
}
if (-not $pwVersion) {
    $pwVersion = '1.56.0'
}

$playImage = "mcr.microsoft.com/playwright:v$pwVersion-jammy"

$imageExists = $false
try {
    & docker image inspect $playImage | Out-Null
    $imageExists = $true
} catch {
    $imageExists = $false
}

if (-not $imageExists) {
    if ($PullImage.IsPresent) {
        Write-Status -Level 'RUN' -Message "Descargando imagen $playImage..."
        & docker pull $playImage | Out-Null
        Write-Status -Level 'OK' -Message "Imagen $playImage descargada."
    } else {
        throw "La imagen $playImage no está disponible localmente. Ejecuta con -PullImage o realiza 'docker pull $playImage' manualmente."
    }
}

Write-Status -Level 'RUN' -Message 'Ejecutando pruebas E2E (Playwright)...'
$e2eVolume = "$(Join-Path $root 'Tests/e2e'):/e2e"
$reportVolume = "$reportDir:/reports"

$playwrightCmd = @"
CURR_VER=`$(node -p "try{require(\"@playwright/test/package.json\").version}catch(e){\"\"}")
if [ ! -d node_modules ] || [ "`$CURR_VER" != "`$PW_VERSION" ]; then npm ci || npm install; fi
npx playwright test
"@

$envArgs = @(
    '-e', "HOST_PORTAL_CLIENTE_PORT=$portalPort",
    '-e', 'PLAYWRIGHT_BROWSERS_PATH=/ms-playwright',
    '-e', 'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1',
    '-e', "PW_VERSION=$pwVersion"
)

& docker run --rm --network=host @envArgs -v $e2eVolume -v $reportVolume -w /e2e $playImage bash -lc $playwrightCmd

Write-Status -Level 'DONE' -Message 'E2E tests OK.'


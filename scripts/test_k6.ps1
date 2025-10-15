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

$orqPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_ORQ_PORT' -Default '8010')

Write-Status -Level 'RUN' -Message 'Ejecutando pruebas de carga k6...'
$dockerVolume = "$root:/work"
$summaryPath = 'Tests/reports/json/k6.json'

$envArgs = @(
    '-e', "HOST_ORQ_PORT=$orqPort",
    '-e', 'K6_ORQ_URL=http://app-orquestador:8010'
)

& docker run --rm --network=telecable-net @envArgs -v $dockerVolume -w /work grafana/k6:0.49.0 `
    run Tests/k6/alta_clientes.js --vus 100 --duration 10s --summary-export=$summaryPath

Write-Status -Level 'DONE' -Message 'k6 tests OK.'


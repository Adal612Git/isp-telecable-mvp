[CmdletBinding()]
param(
    [string]$EnvFile = '.env.ports',
    [switch]$KeepVolumes
)

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) {
    $EnvFile
} else {
    Join-Path $root $EnvFile
}

Push-Location $root
try {
    Write-Status -Level 'RUN' -Message 'Deteniendo y limpiando contenedores (docker compose down)...'
    $extraArgs = @('down', '--remove-orphans')
    if (-not $KeepVolumes.IsPresent) {
        $extraArgs += '-v'
    }
    Invoke-DockerCompose -EnvFile $envPath -ExtraArgs $extraArgs
    Write-Status -Level 'DONE' -Message 'Infraestructura detenida.'
} finally {
    Pop-Location
}


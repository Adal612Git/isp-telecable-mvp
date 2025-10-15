[CmdletBinding()]
param(
    [string]$EnvFile = '.env.ports',
    [switch]$ForcePorts,
    [switch]$NoBuild
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
    Write-Status -Level 'RUN' -Message 'Levantando infraestructura...'

    $networkExists = (& docker network ls --format '{{.Name}}' | Select-String -Quiet 'telecable-net')
    if (-not $networkExists) {
        Write-Status -Level 'INFO' -Message 'Creando red telecable-net...'
        & docker network create telecable-net | Out-Null
    }

    & "$PSScriptRoot/allocate_ports.ps1" -OutFile $envPath -Force:$ForcePorts
    $envMap = Read-EnvFile -Path $envPath -UpdateProcessEnv

    $extraArgs = @('up', '-d')
    if (-not $NoBuild.IsPresent) {
        $extraArgs += '--build'
    }

    Invoke-DockerCompose -EnvFile $envPath -ExtraArgs $extraArgs
    Start-Sleep -Seconds 5
    Write-Status -Level 'OK' -Message 'Infraestructura levantada.'

    $clientesPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_CLIENTES_PORT' -Default '8000')
    $catalogoPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_CATALOGO_PORT' -Default '8001')
    $factPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_FACTURACION_PORT' -Default '8002')
    $pagosPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_PAGOS_PORT' -Default '8003')
    $orqPort = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_ORQ_PORT' -Default '8010')

    Check-Service -Name 'clientes' -Port $clientesPort
    Check-Service -Name 'catalogo' -Port $catalogoPort
    Check-Service -Name 'facturacion' -Port $factPort
    Check-Service -Name 'pagos' -Port $pagosPort
    Check-Service -Name 'orquestador' -Port $orqPort

    $portalPort = Get-EnvValue -EnvMap $envMap -Key 'HOST_PORTAL_CLIENTE_PORT' -Default '5173'
    $backofficePort = Get-EnvValue -EnvMap $envMap -Key 'HOST_BACKOFFICE_PORT' -Default '8089'
    Write-Status -Level 'INFO' -Message ("Portal Cliente: http://localhost:{0}" -f $portalPort)
    Write-Status -Level 'INFO' -Message ("Backoffice: http://localhost:{0}" -f $backofficePort)
} finally {
    Pop-Location
}

[CmdletBinding()]
param(
    [string]$EnvFile = '.env.ports',
    [int]$Tail = 200,
    [switch]$Follow,
    [string]$Service
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
    $args = @('logs', ("--tail=$Tail"))
    if ($Follow.IsPresent) {
        $args += '-f'
    }
    if ($Service) {
        $args += $Service
    }
    Invoke-DockerCompose -EnvFile $envPath -ExtraArgs $args
} finally {
    Pop-Location
}


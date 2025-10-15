[CmdletBinding()]
param()

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$targets = @(
    Join-Path $root 'node_modules',
    Join-Path $root 'Tests/reports',
    Join-Path $root '.venv'
)

foreach ($path in $targets) {
    if (Test-Path $path) {
        Write-Status -Level 'RUN' -Message "Eliminando $path ..."
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Status -Level 'DONE' -Message 'Limpieza completada.'


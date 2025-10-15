<#
  Wrapper de PowerShell para ejecutar el orquestador Python en Windows.
  Detecta gestores de paquetes (winget/choco) y proporciona instrucciones en caso
  de que la ejecución esté bloqueada por la política de scripts.
#>

param(
    [switch]$Auto = $false,
    [switch]$Demo = $false,
    [switch]$CI = $false,
    [switch]$Verbose = $false
)

Write-Host "INICIANDO SETUP INTELIGENTE — ISP TELECABLE MVP (Windows)" -ForegroundColor Cyan

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $repoRoot

function Test-Python310 {
    try {
        $versionOutput = & python -c "import sys;print('.'.join(map(str, sys.version_info[:3])))" 2>$null
        if (-not $versionOutput) {
            return $false
        }
        $parts = $versionOutput.Split('.')
        if ([int]$parts[0] -gt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -ge 10)) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

if (-not (Test-Python310)) {
    Write-Warning "Python 3.10+ no está disponible."
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Puedes instalarlo con: winget install -e --id Python.Python.3.11"
    } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Host "Puedes instalarlo con: choco install python --version=3.11.0"
    } else {
        Write-Host "Descarga el instalador desde https://www.python.org/downloads/windows/"
    }
    Read-Host "Presiona ENTER para cerrar"
    exit 1
}

$arguments = @()
if ($Auto) { $arguments += "--auto" }
if ($Demo) { $arguments += "--demo" }
if ($CI) { $arguments += "--ci" }
if ($Verbose) { $arguments += "--verbose" }

try {
    python scripts/setup_orchestrator.py @arguments
} catch {
    Write-Error "No se pudo ejecutar python scripts/setup_orchestrator.py. $_"
}

Write-Host "Ejecución finalizada. Revisa logs/setup.log para más detalles." -ForegroundColor Green
Read-Host "Presiona ENTER para cerrar"

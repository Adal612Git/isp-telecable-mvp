<#
  Wrapper de PowerShell para ejecutar el orquestador Python en Windows.
  Detecta gestores de paquetes (winget/choco) y proporciona instrucciones en caso
  de que la ejecucion este bloqueada por la politica de scripts.
#>

param(
    [switch]$Auto = $false,
    [switch]$Demo = $false,
    [switch]$CI = $false,
    [switch]$Verbose = $false,
    [switch]$Pause = $false
)

Write-Host "INICIANDO SETUP INTELIGENTE - ISP TELECABLE MVP (Windows)" -ForegroundColor Cyan

$scriptPath = (Resolve-Path -LiteralPath $MyInvocation.MyCommand.Path).ProviderPath
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptPath)

function Normalize-PathValue {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $null
    }

    $trimmed = $Value.Trim()
    return $trimmed.TrimEnd('\').TrimEnd('/').ToLowerInvariant()
}

function Contains-PathEntry {
    param(
        [string[]]$Entries,
        [string]$Candidate
    )

    $normalizedCandidate = Normalize-PathValue -Value $Candidate
    if (-not $normalizedCandidate) {
        return $false
    }

    foreach ($entry in $Entries) {
        $normalizedEntry = Normalize-PathValue -Value $entry
        if ($normalizedEntry -and $normalizedEntry -eq $normalizedCandidate) {
            return $true
        }
    }

    return $false
}

function Ensure-PathEntry {
    param([string]$PathEntry)

    if (-not $PathEntry -or -not (Test-Path -LiteralPath $PathEntry)) {
        return
    }

    $sessionEntries = @()
    if ($env:Path) {
        $sessionEntries = $env:Path -split ';'
    }

    if (-not (Contains-PathEntry -Entries $sessionEntries -Candidate $PathEntry)) {
        $updatedSession = @($sessionEntries + $PathEntry) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        $env:Path = ($updatedSession -join ';')
        Write-Verbose "Se agrego $PathEntry al PATH de la sesion."
    }

    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $userEntries = @()
    if ($userPath) {
        $userEntries = $userPath -split ';'
    }

    if (-not (Contains-PathEntry -Entries $userEntries -Candidate $PathEntry)) {
        try {
            $updatedUser = @($userEntries + $PathEntry) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
            [Environment]::SetEnvironmentVariable("Path", ($updatedUser -join ';'), "User")
            Write-Verbose "Se agrego $PathEntry al PATH persistente del usuario."
        } catch {
            Write-Verbose "No se pudo agregar $PathEntry al PATH persistente del usuario: $_"
        }
    }
}

function Ensure-SetupWindowsShim {
    param(
        [string]$CommandName,
        [string]$TargetScript
    )

    $windowsApps = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps"
    if (-not $windowsApps -or -not (Test-Path -LiteralPath $windowsApps)) {
        return
    }

    Ensure-PathEntry -PathEntry $windowsApps

    $shimPath = Join-Path $windowsApps ("{0}.cmd" -f $CommandName)
    $escaped = $TargetScript.Replace('"', '""')
    $shimContent = '@echo off{0}"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "{1}" %*{0}' -f "`r`n", $escaped

    try {
        $current = ""
        if (Test-Path -LiteralPath $shimPath) {
            $current = Get-Content -LiteralPath $shimPath -Raw
        }
        if ($current -ne $shimContent) {
            Set-Content -LiteralPath $shimPath -Value $shimContent -Encoding ASCII
            Write-Verbose "Se creo o actualizo el shim global en $shimPath."
        }
    } catch {
        Write-Verbose "No se pudo preparar el comando global setup_windows: $_"
    }
}

Ensure-SetupWindowsShim -CommandName "setup_windows" -TargetScript $scriptPath

try {
    Set-Alias -Name setup_windows -Value $scriptPath -Scope Global -ErrorAction SilentlyContinue
} catch {
    Write-Verbose "No se pudo registrar el alias temporal setup_windows: $_"
}

function Get-PythonVersionInfo {
    $candidates = @(
        @{ Command = "python"; Arguments = @("--version"); Runner = @("python") },
        @{ Command = "py"; Arguments = @("-3", "--version"); Runner = @("py", "-3") },
        @{ Command = "py"; Arguments = @("--version"); Runner = @("py") }
    )

    foreach ($candidate in $candidates) {
        try {
            $output = & $candidate.Command @($candidate.Arguments) 2>&1
            if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($output)) {
                continue
            }
            $clean = $output.Trim()
            $match = [regex]::Match($clean, "Python\s+(?<Major>\d+)\.(?<Minor>\d+)\.(?<Patch>\d+)")
            if ($match.Success) {
                return [PSCustomObject]@{
                    Command = $candidate.Command
                    Major = [int]$match.Groups["Major"].Value
                    Minor = [int]$match.Groups["Minor"].Value
                    Patch = [int]$match.Groups["Patch"].Value
                    Text = $clean
                    Runner = $candidate.Runner
                }
            }
        } catch {
            continue
        }
    }

    return $null
}

$script:PythonVersionInfo = $null

function Test-Python310 {
    if (-not $script:PythonVersionInfo) {
        $script:PythonVersionInfo = Get-PythonVersionInfo
    }

    $info = $script:PythonVersionInfo
    if (-not $info) {
        return $false
    }

    if ($info.Major -gt 3) {
        return $true
    }

    if ($info.Major -eq 3 -and $info.Minor -ge 10) {
        return $true
    }

    return $false
}

function Invoke-SetupWindows {
    param(
        [string[]]$CliArguments
    )

    if (-not (Test-Python310)) {
        Write-Warning "Python 3.10+ no esta disponible."
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "Puedes instalarlo con: winget install -e --id Python.Python.3.11"
        } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
            Write-Host "Puedes instalarlo con: choco install python --version=3.11.0"
        } else {
            Write-Host "Descarga el instalador desde https://www.python.org/downloads/windows/"
        }
        if ($script:PythonVersionInfo -and $script:PythonVersionInfo.Text) {
            Write-Host "Se detecto: $($script:PythonVersionInfo.Text)" -ForegroundColor Yellow
            Write-Host "Verifica que el comando python en esta sesion apunte al interprete correcto."
        }
        return 1
    }

    $arguments = @()
    if ($Auto) { $arguments += "--auto" }
    if ($Demo) { $arguments += "--demo" }
    if ($CI) { $arguments += "--ci" }
    if ($Verbose) { $arguments += "--verbose" }
    if ($CliArguments) { $arguments += $CliArguments }

    if (-not $script:PythonVersionInfo) {
        $script:PythonVersionInfo = Get-PythonVersionInfo
    }
    $runner = @("python")
    if ($script:PythonVersionInfo -and $script:PythonVersionInfo.Runner) {
        $runner = $script:PythonVersionInfo.Runner
    }

    if ($script:PythonVersionInfo -and $script:PythonVersionInfo.Text) {
        $source = ($runner -join " ")
        Write-Host "Usando $($script:PythonVersionInfo.Text) via comando '$source'." -ForegroundColor DarkGray
    }

    $runnerCommand = $runner[0]
    $runnerArgs = @()
    if ($runner.Count -gt 1) {
        $runnerArgs = $runner[1..($runner.Count - 1)]
    }

    $previousIoEncoding = $env:PYTHONIOENCODING
    $previousUtf8 = $env:PYTHONUTF8
    $cleanupEncoding = {
        param($ioEncoding, $utf8)
        if ($null -ne $ioEncoding) {
            $env:PYTHONIOENCODING = $ioEncoding
        } else {
            Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
        }

        if ($null -ne $utf8) {
            $env:PYTHONUTF8 = $utf8
        } else {
            Remove-Item Env:PYTHONUTF8 -ErrorAction SilentlyContinue
        }
    }

    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"

    try {
        & $runnerCommand @runnerArgs "scripts/setup_orchestrator.py" @arguments
        return $LASTEXITCODE
    } catch {
        Write-Error "No se pudo ejecutar python scripts/setup_orchestrator.py. $_"
        return 1
    } finally {
        & $cleanupEncoding $previousIoEncoding $previousUtf8
    }
}

Push-Location -Path $repoRoot
$exitCode = 0
try {
    $exitCode = Invoke-SetupWindows -CliArguments $args
} finally {
    Pop-Location
}

if ($exitCode -eq 0) {
    Write-Host "Ejecucion finalizada. Revisa logs/setup.log para mas detalles." -ForegroundColor Green
} else {
    Write-Warning "El proceso se completo con errores. Revisa logs/setup.log para diagnosticar."
}

if ($Pause) {
    Read-Host "Presiona ENTER para cerrar"
}

exit $exitCode

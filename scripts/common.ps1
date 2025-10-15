Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Status {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [ValidateSet('OK','RUN','INFO','WARN','ERROR','DONE')]
        [string]$Level,
        [Parameter(Mandatory)]
        [string]$Message
    )

    $prefix = "[{0}] " -f $Level.ToUpperInvariant()
    Write-Host "$prefix$Message"
}

function Get-RepoRoot {
    [CmdletBinding()]
    param()

    return (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

function Resolve-RepoPath {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$RelativePath
    )

    $root = Get-RepoRoot
    return [System.IO.Path]::GetFullPath((Join-Path $root $RelativePath))
}

function Read-EnvFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path,
        [switch]$UpdateProcessEnv
    )

    $envMap = @{}
    if (-not (Test-Path $Path)) {
        return $envMap
    }

    foreach ($line in Get-Content -Path $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#')) {
            continue
        }
        $parts = $trimmed -split '=', 2
        if ($parts.Length -ne 2) {
            continue
        }
        $key = $parts[0].Trim()
        $value = $parts[1]
        $envMap[$key] = $value
        if ($UpdateProcessEnv) {
            [System.Environment]::SetEnvironmentVariable($key, $value)
        }
    }

    return $envMap
}

function Ensure-Directory {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Force -Path $Path | Out-Null
    }
}

function Ensure-ReportLayout {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Root
    )

    $paths = @($Root,
               (Join-Path $Root 'screenshots'),
               (Join-Path $Root 'har'),
               (Join-Path $Root 'html'),
               (Join-Path $Root 'json'),
               (Join-Path $Root 'csv'))

    foreach ($item in $paths) {
        Ensure-Directory -Path $item
    }
}

function Get-EnvValue {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [hashtable]$EnvMap,
        [Parameter(Mandatory)]
        [string]$Key,
        [Parameter()]
        [string]$Default = ''
    )

    if ($EnvMap.ContainsKey($Key) -and $EnvMap[$Key]) {
        return $EnvMap[$Key]
    }

    return $Default
}

function Wait-ForEndpoint {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Url,
        [int]$Retries = 30,
        [int]$DelaySeconds = 2
    )

    for ($attempt = 0; $attempt -lt $Retries; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        } catch {
            # ignore and retry
        }
        Start-Sleep -Seconds $DelaySeconds
    }

    return $false
}

function Check-Service {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        [Parameter(Mandatory)]
        [int]$Port,
        [string]$Path = '/health',
        [int]$Retries = 20,
        [int]$DelaySeconds = 2,
        [switch]$Optional
    )

    $url = "http://localhost:$Port$Path"
    if (Wait-ForEndpoint -Url $url -Retries $Retries -DelaySeconds $DelaySeconds) {
        Write-Status -Level 'OK' -Message "$Name responde en puerto $Port"
        return $true
    }

    $message = "$Name no responde en puerto $Port"
    if ($Optional.IsPresent) {
        Write-Status -Level 'WARN' -Message $message
        return $false
    }

    Write-Status -Level 'ERROR' -Message $message
    throw $message
}

function Invoke-DockerCompose {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$EnvFile,
        [string[]]$ExtraArgs
    )

    $defaultArgs = @('--env-file', $EnvFile, '-f', 'infra/docker-compose.yml', '-f', 'docker-compose.yml')
    $fullArgs = @($defaultArgs + $ExtraArgs)
    & docker compose @fullArgs
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "docker compose command failed with exit code $exitCode"
    }
}

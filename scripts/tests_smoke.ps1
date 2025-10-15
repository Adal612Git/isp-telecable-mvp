<#
  Prueba de humo en Windows. Requiere que .env.ports haya sido generado y que
  los servicios estén arriba. Usa Invoke-WebRequest para validar los endpoints
  clave.
#>

$envPath = Join-Path (Get-Location) ".env.ports"
if (-not (Test-Path $envPath)) {
    Write-Error ".env.ports no encontrado. Ejecuta scripts/setup_windows.bat primero."
    exit 1
}

Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith('#')) {
        return
    }
    $parts = $line.Split('=')
    if ($parts.Length -eq 2) {
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        Set-Variable -Name $name -Value $value -Scope Script
    }
}

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url
    )
    Write-Host "Consultando $Name -> $Url"
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 10
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
            Write-Host "OK"
        } else {
            throw "Código inesperado: $($response.StatusCode)"
        }
    } catch {
        Write-Error "FALLO: $_"
        throw
    }
}

Test-Endpoint -Name "Clientes API" -Url "http://localhost:$HOST_CLIENTES_API_PORT/health"
Test-Endpoint -Name "Router Simulator" -Url "http://localhost:$HOST_ROUTER_SIM_PORT/health"
Test-Endpoint -Name "Portal Cliente" -Url "http://localhost:$HOST_CLIENTES_PORT/"

Write-Host "Prueba de humo completada" -ForegroundColor Green

Param()

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $Root 'logs'
$EnvFile = Join-Path $Root '.env.ports'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Info($Message) {
  $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  Write-Host "[$stamp] $Message"
}

function Test-PortFree($Port) {
  $result = Test-NetConnection -ComputerName 'localhost' -Port $Port -WarningAction SilentlyContinue
  return -not $result.TcpTestSucceeded
}

$defaults = [ordered]@{
  HOST_CLIENTES_PORT    = 3300
  HOST_TECH_PORT        = 3400
  HOST_SALES_PORT       = 3500
  HOST_ROUTER_SIM_PORT  = 3600
  HOST_CLIENTES_API_PORT = 3700
}

$existing = @{}
if (Test-Path $EnvFile) {
  Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^(HOST_[A-Z_]+)=(\d+)$') {
      $existing[$matches[1]] = [int]$matches[2]
    }
  }
}

$ports = @{}
$used = @{}
foreach ($key in $defaults.Keys) {
  $start = if ($existing.ContainsKey($key)) { $existing[$key] } else { $defaults[$key] }
  $port = $start
  while ($true) {
    if ($used.ContainsKey($port)) { $port++ ; continue }
    if (Test-PortFree $port) {
      $ports[$key] = $port
      $used[$port] = $true
      Write-Info "Asignado $key -> $port"
      break
    }
    $port++
  }
}

"# Generated $(Get-Date)" | Out-File -FilePath $EnvFile
foreach ($key in $defaults.Keys) {
  "$key=$($ports[$key])" | Out-File -FilePath $EnvFile -Append
}

Write-Info "Variables guardadas en $EnvFile"

$python = Get-Command python -ErrorAction SilentlyContinue
$npm = Get-Command npm -ErrorAction SilentlyContinue

if (-not $python) {
  Write-Info "⚠️  Python no encontrado en PATH. Ejecuta el backend manualmente."
} else {
  Write-Info "🐍 Instalando dependencias backend (si es necesario)"
  python -m pip install --quiet -r (Join-Path $Root 'services/clientes/requirements.txt') | Out-Null
  python -m pip install --quiet -r (Join-Path $Root 'services/router_simulator/requirements.txt') | Out-Null

  $routerCmd = "Set-Location '$Root'; `$env:PYTHONPATH='$Root'; `$env:PORTAL_CLIENTE_ORIGIN='http://localhost:$($ports.HOST_CLIENTES_PORT)'; `$env:PORTAL_TECNICO_ORIGIN='http://localhost:$($ports.HOST_TECH_PORT)'; `$env:PORTAL_VENTAS_ORIGIN='http://localhost:$($ports.HOST_SALES_PORT)'; python -m uvicorn services.router_simulator.app.main:app --host 0.0.0.0 --port $($ports.HOST_ROUTER_SIM_PORT)"
  Start-Process powershell -ArgumentList '-NoExit','-Command', $routerCmd -WindowStyle Normal | Out-Null
  Write-Info "Router simulator iniciado (ventana separada)"

  $clientesCmd = "Set-Location '$Root'; `$env:PYTHONPATH='$Root'; `$env:ROUTER_SIMULATOR_URL='http://localhost:$($ports.HOST_ROUTER_SIM_PORT)'; `$env:DATABASE_URL='sqlite:///$($Root.Replace('\','/'))/logs/clientes_demo.db'; python -m uvicorn services.clientes.app.main:app --host 0.0.0.0 --port $($ports.HOST_CLIENTES_API_PORT)"
  Start-Process powershell -ArgumentList '-NoExit','-Command', $clientesCmd -WindowStyle Normal | Out-Null
  Write-Info "Servicio clientes iniciado (ventana separada)"
}

if (-not $npm) {
  Write-Info "⚠️  npm no encontrado en PATH. Ejecuta los frontends manualmente."
} else {
  $apps = @(
    @{ Name = 'portal-cliente'; Dir = 'apps/portal-cliente'; Port = $ports.HOST_CLIENTES_PORT; Extra = "`$env:VITE_API_CLIENTES_URL='http://localhost:$($ports.HOST_CLIENTES_API_PORT)'; `$env:VITE_ROUTER_SIM_URL='http://localhost:$($ports.HOST_ROUTER_SIM_PORT)'" },
    @{ Name = 'portal-tecnico'; Dir = 'apps/portal-tecnico'; Port = $ports.HOST_TECH_PORT; Extra = "`$env:VITE_API_CLIENTES_URL='http://localhost:$($ports.HOST_CLIENTES_API_PORT)'; `$env:VITE_ROUTER_SIM_URL='http://localhost:$($ports.HOST_ROUTER_SIM_PORT)'" },
    @{ Name = 'portal-ventas'; Dir = 'apps/portal-ventas'; Port = $ports.HOST_SALES_PORT; Extra = '' }
  )
  foreach ($app in $apps) {
    $fullDir = Join-Path $Root $app.Dir
    if (-not (Test-Path (Join-Path $fullDir 'node_modules'))) {
      Write-Info "Instalando npm en $($app.Name)"
      npm --prefix $fullDir install | Out-Null
    }
    $cmd = "Set-Location '$fullDir'; $($app.Extra); npm run dev -- --host 0.0.0.0 --port $($app.Port)"
    Start-Process powershell -ArgumentList '-NoExit','-Command', $cmd -WindowStyle Normal | Out-Null
    Write-Info "Iniciado $($app.Name) en puerto $($app.Port)"
  }
}

Write-Host ""
Write-Host "URLs:" -ForegroundColor Cyan
Write-Host "  Cliente : http://localhost:$($ports.HOST_CLIENTES_PORT)/cliente"
Write-Host "  Técnico : http://localhost:$($ports.HOST_TECH_PORT)/tecnico"
Write-Host "  Ventas  : http://localhost:$($ports.HOST_SALES_PORT)/ventas"
Write-Host ""
Write-Host "Si alguna ventana falla, revisa las dependencias y ejecuta los comandos mostrados manualmente." -ForegroundColor Yellow

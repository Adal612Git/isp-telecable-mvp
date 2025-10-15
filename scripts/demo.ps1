[CmdletBinding()]
param(
    [string]$EnvFile = '.env.ports'
)

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$envPath = if ([System.IO.Path]::IsPathRooted($EnvFile)) {
    $EnvFile
} else {
    Join-Path $root $EnvFile
}

$envMap = Read-EnvFile -Path $envPath -UpdateProcessEnv
$reportDir = Join-Path $root 'Tests/reports'
Ensure-ReportLayout -Root $reportDir

$clientesPort   = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_CLIENTES_PORT' -Default '8000')
$catalogoPort   = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_CATALOGO_PORT' -Default '8001')
$factPort       = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_FACTURACION_PORT' -Default '8002')
$pagosPort      = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_PAGOS_PORT' -Default '8003')
$orqPort        = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_ORQ_PORT' -Default '8010')
$waPort         = [int](Get-EnvValue -EnvMap $envMap -Key 'HOST_WHATSAPP_PORT' -Default '8011')
$portalPort     = Get-EnvValue -EnvMap $envMap -Key 'HOST_PORTAL_CLIENTE_PORT' -Default '8088'
$backofficePort = Get-EnvValue -EnvMap $envMap -Key 'HOST_BACKOFFICE_PORT' -Default '8089'

Write-Status -Level 'RUN' -Message 'Validando servicios antes de la demo...'
Check-Service -Name 'clientes' -Port $clientesPort
Check-Service -Name 'catalogo' -Port $catalogoPort
Check-Service -Name 'facturacion' -Port $factPort
Check-Service -Name 'pagos' -Port $pagosPort
Check-Service -Name 'orquestador' -Port $orqPort

$summary = New-Object System.Collections.Generic.List[object]
[int]$clienteId = 0
[string]$clienteNombre = ''

function Add-DemoSummary {
    param(
        [string]$Step,
        [string]$Status,
        [double]$Duration,
        [string]$Detail
    )

    $summary.Add([pscustomobject]@{
        Step     = $Step
        Status   = $Status
        Duration = [Math]::Round($Duration, 2)
        Detail   = $Detail
    })
}

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

Write-Status -Level 'RUN' -Message 'Alta de cliente...'
try {
    $clientePayload = @{
        nombre = 'Cliente Demo'
        rfc = 'AAA010101AAA'
        email = 'demo@example.com'
        telefono = '5555555555'
        plan_id = 'INT100'
        domicilio = @{
            calle = 'Av Demo'
            numero = '100'
            colonia = 'Centro'
            cp = '01000'
            ciudad = 'CDMX'
            estado = 'CDMX'
            zona = 'NORTE'
        }
        contacto = @{
            nombre = 'Cliente Demo'
            email = 'demo@example.com'
            telefono = '5555555555'
        }
        consentimiento = @{
            marketing = $true
            terminos = $true
        }
        idem = [guid]::NewGuid().ToString()
    }

    $alta = Invoke-RestMethod -Uri "http://localhost:$orqPort/saga/alta-cliente" -Method Post -ContentType 'application/json' -Body (ConvertTo-Json -InputObject $clientePayload -Depth 6)
    $stopwatch.Stop()
    $altaPath = Join-Path $reportDir 'json/demo_alta_cliente.json'
    $alta | ConvertTo-Json -Depth 8 | Set-Content -Path $altaPath -Encoding utf8

    $clienteId = $alta.cliente.id
    $clienteNombre = $alta.cliente.nombre

    $message = "Cliente creado: $clienteId"
    Write-Status -Level 'OK' -Message $message
    Add-DemoSummary -Step 'Alta de cliente' -Status 'OK' -Duration $stopwatch.Elapsed.TotalSeconds -Detail $message
} catch {
    $stopwatch.Stop()
    $errorMessage = "Alta de cliente falló: $($_.Exception.Message)"
    Write-Status -Level 'ERROR' -Message $errorMessage
    Add-DemoSummary -Step 'Alta de cliente' -Status 'ERROR' -Duration $stopwatch.Elapsed.TotalSeconds -Detail $errorMessage
    throw
}

$stopwatch.Restart()
Write-Status -Level 'RUN' -Message 'Generando factura...'
try {
    $factPayload = @(
        @{ cliente_id = $clienteId; total = 299.0 }
    )
    $factResp = Invoke-RestMethod -Uri "http://localhost:$factPort/facturacion/generar-masiva" -Method Post -ContentType 'application/json' -Body (ConvertTo-Json -InputObject $factPayload -Depth 4)
    $stopwatch.Stop()
    $factPath = Join-Path $reportDir 'json/demo_facturacion.json'
    $factResp | ConvertTo-Json -Depth 6 | Set-Content -Path $factPath -Encoding utf8

    Write-Status -Level 'OK' -Message 'Factura generada.'
    Add-DemoSummary -Step 'Generar factura' -Status 'OK' -Duration $stopwatch.Elapsed.TotalSeconds -Detail 'Factura generada'
} catch {
    $stopwatch.Stop()
    $errorMessage = "Generar factura falló: $($_.Exception.Message)"
    Write-Status -Level 'ERROR' -Message $errorMessage
    Add-DemoSummary -Step 'Generar factura' -Status 'ERROR' -Duration $stopwatch.Elapsed.TotalSeconds -Detail $errorMessage
    throw
}

$stopwatch.Restart()
Write-Status -Level 'RUN' -Message 'Procesando pago...'
try {
    $pagoPayload = @{
        cliente_id = $clienteId
        referencia = "DEMO-$([guid]::NewGuid().ToString('N').Substring(0,8).ToUpper())"
        metodo = 'spei'
        monto = 299.0
        idem = [guid]::NewGuid().ToString()
    }
    $pagoResp = Invoke-RestMethod -Uri "http://localhost:$orqPort/saga/procesar-pago" -Method Post -ContentType 'application/json' -Body (ConvertTo-Json -InputObject $pagoPayload -Depth 4)
    $pagoPath = Join-Path $reportDir 'json/demo_pago.json'
    $pagoResp | ConvertTo-Json -Depth 6 | Set-Content -Path $pagoPath -Encoding utf8

    try {
        $conciliado = Invoke-RestMethod -Uri "http://localhost:$pagosPort/pagos/conciliar" -Method Get -TimeoutSec 5
        if ($conciliado.csv) {
            $concPath = Join-Path $reportDir 'csv/demo_conciliacion.csv'
            Set-Content -Path $concPath -Value $conciliado.csv -Encoding utf8
        }
    } catch {
        $statusCode = $null
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        }
        if ($statusCode -ne 404) {
            throw
        }
    }

    $stopwatch.Stop()
    Write-Status -Level 'OK' -Message 'Pago conciliado.'
    Add-DemoSummary -Step 'Procesar pago' -Status 'OK' -Duration $stopwatch.Elapsed.TotalSeconds -Detail 'Pago conciliado'
} catch {
    $stopwatch.Stop()
    $errorMessage = "Procesar pago falló: $($_.Exception.Message)"
    Write-Status -Level 'ERROR' -Message $errorMessage
    Add-DemoSummary -Step 'Procesar pago' -Status 'ERROR' -Duration $stopwatch.Elapsed.TotalSeconds -Detail $errorMessage
    throw
}

$stopwatch.Restart()
Write-Status -Level 'RUN' -Message 'Revisando WhatsApp mock...'
try {
    $whatsBody = @{
        to = '+5215555555555'
        template = 'reconexion_exitosa'
        cliente = $clienteNombre
    }
    Invoke-RestMethod -Uri "http://localhost:$waPort/send-template" -Method Post -ContentType 'application/json' -Body (ConvertTo-Json -InputObject $whatsBody -Depth 3) | Out-Null
    $stopwatch.Stop()
    Write-Status -Level 'OK' -Message 'WhatsApp mock notificado.'
    Add-DemoSummary -Step 'WhatsApp mock' -Status 'OK' -Duration $stopwatch.Elapsed.TotalSeconds -Detail 'Notificación enviada'
} catch {
    $stopwatch.Stop()
    $errorMessage = "WhatsApp mock falló: $($_.Exception.Message)"
    Write-Status -Level 'ERROR' -Message $errorMessage
    Add-DemoSummary -Step 'WhatsApp mock' -Status 'ERROR' -Duration $stopwatch.Elapsed.TotalSeconds -Detail $errorMessage
    throw
}

$summaryPath = Join-Path $reportDir 'json/demo_summary.json'
$summary | ConvertTo-Json -Depth 4 | Set-Content -Path $summaryPath -Encoding utf8

Write-Status -Level 'DONE' -Message ("Demo completada correctamente. Portal Cliente: http://localhost:{0} | Backoffice: http://localhost:{1}" -f $portalPort, $backofficePort)

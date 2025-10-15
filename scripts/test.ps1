[CmdletBinding()]
param(
    [string]$EnvFile = '.env.ports',
    [switch]$PullPlaywright
)

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$reportDir = Join-Path $root 'Tests/reports'
Ensure-ReportLayout -Root $reportDir

Write-Status -Level 'RUN' -Message 'Ejecutando suite completa (unit, integration, e2e, k6)...'

& "$PSScriptRoot/test_unit.ps1"
& "$PSScriptRoot/up.ps1" -EnvFile $EnvFile
& "$PSScriptRoot/test_integration.ps1" -EnvFile $EnvFile
& "$PSScriptRoot/test_e2e.ps1" -EnvFile $EnvFile -PullImage:$PullPlaywright
& "$PSScriptRoot/test_k6.ps1" -EnvFile $EnvFile

$junitInt = Join-Path $reportDir 'junit-int.xml'
$junitMain = Join-Path $reportDir 'junit.xml'
if (Test-Path $junitInt) {
    Copy-Item -Path $junitInt -Destination $junitMain -Force
}

Write-Status -Level 'DONE' -Message "Suite completada. Evidencia en $reportDir"


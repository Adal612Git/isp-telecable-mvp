[CmdletBinding()]
param()

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$reportDir = Join-Path $root 'Tests/reports'
Ensure-ReportLayout -Root $reportDir
Write-Status -Level 'DONE' -Message "Directorios listos en $reportDir"


[CmdletBinding()]
param(
    [string]$Source = 'Tests/reports',
    [string]$Destination = 'Reports/ola1-comercial'
)

. "$PSScriptRoot/common.ps1"

$srcPath = Resolve-RepoPath -RelativePath $Source
$dstPath = Resolve-RepoPath -RelativePath $Destination

Ensure-Directory -Path $dstPath
Copy-Item -Path (Join-Path $srcPath '*') -Destination $dstPath -Recurse -Force

Write-Status -Level 'DONE' -Message "Evidencia copiada a $dstPath"


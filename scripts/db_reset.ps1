[CmdletBinding()]
param()

. "$PSScriptRoot/common.ps1"

Write-Status -Level 'RUN' -Message 'Reiniciando esquema public en infra-postgres...'
$sql = 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
& docker exec -i infra-postgres psql -U isp_admin -d isp_mvp -v ON_ERROR_STOP=1 -c $sql
Write-Status -Level 'DONE' -Message 'Base de datos reiniciada.'


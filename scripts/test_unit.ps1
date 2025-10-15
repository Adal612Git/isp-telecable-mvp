[CmdletBinding()]
param()

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$reportDir = Join-Path $root 'Tests/reports'
Ensure-ReportLayout -Root $reportDir

$dockerVolume = "$root:/work"

Write-Status -Level 'RUN' -Message 'Pytest (unit) con cobertura...'
$pytestCmd = @'
pip install -r requirements-test.txt \
            -r services/clientes/requirements.txt \
            -r services/catalogo/requirements.txt \
            -r services/facturacion/requirements.txt \
            -r services/pagos/requirements.txt && \
PYTHONPATH=/work pytest -q --cov=services --cov-report=xml:Tests/reports/coverage.xml --cov-report=html:Tests/reports/html/coverage \
  --junitxml=Tests/reports/junit-unit.xml --html=Tests/reports/unit.html --self-contained-html Tests/unit
'@

& docker run --rm -v $dockerVolume -w /work python:3.11-slim bash -lc $pytestCmd

Write-Status -Level 'DONE' -Message 'Unit tests OK.'


[CmdletBinding()]
param()

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$dockerVolume = "$root:/work"
$e2eVolume = "$(Join-Path $root 'Tests/e2e'):/e2e"

Write-Status -Level 'RUN' -Message 'Lint Python (flake8)...'
$flakeCmd = 'pip install flake8 && flake8 services || true'
& docker run --rm -v $dockerVolume -w /work python:3.11-slim bash -lc $flakeCmd

Write-Status -Level 'RUN' -Message 'Lint JavaScript (eslint)...'
$eslintCmd = 'if [ ! -d node_modules ]; then npm install --no-audit --no-fund; fi; npx eslint . || true'
& docker run --rm -v $e2eVolume -w /e2e node:20 bash -lc $eslintCmd

Write-Status -Level 'DONE' -Message 'Lint completado (non-blocking).'

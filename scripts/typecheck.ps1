[CmdletBinding()]
param()

. "$PSScriptRoot/common.ps1"

$root = Get-RepoRoot
$dockerVolume = "$root:/work"
$e2eVolume = "$(Join-Path $root 'Tests/e2e'):/e2e"

Write-Status -Level 'RUN' -Message 'Typecheck Python (mypy)...'
$mypyCmd = 'pip install mypy && mypy services || true'
& docker run --rm -v $dockerVolume -w /work python:3.11-slim bash -lc $mypyCmd

Write-Status -Level 'RUN' -Message 'Typecheck TypeScript...'
$tsCmd = 'if [ ! -d node_modules ]; then npm install --no-audit --no-fund; fi; npx tsc --noEmit || true'
& docker run --rm -v $e2eVolume -w /e2e node:20 bash -lc $tsCmd

Write-Status -Level 'DONE' -Message 'Typecheck completado (non-blocking).'


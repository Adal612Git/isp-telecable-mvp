#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

docker run --rm -v "$ROOT_DIR":/work -w /work python:3.11-slim bash -lc '
  pip install mypy && mypy services || true
'

docker run --rm -v "$ROOT_DIR/Tests/e2e":/e2e -w /e2e node:20 bash -lc '
  npm i -D typescript && npx tsc --noEmit || true
'

echo "Typecheck completed (non-blocking)."


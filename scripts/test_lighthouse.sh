#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OUT_DIR="$ROOT_DIR/Tests/reports/portal"
mkdir -p "$OUT_DIR"

PORT=${HOST_PORTAL_CLIENTE_PORT:-5173}

docker run --rm --network=host \
  -v "$OUT_DIR":/reports \
  femtopixel/google-lighthouse:latest \
  --no-enable-error-reporting --quiet --chrome-flags="--headless --no-sandbox" \
  http://localhost:${PORT} --output html --output-path /reports/lighthouse.html

echo "Lighthouse report at $OUT_DIR/lighthouse.html"

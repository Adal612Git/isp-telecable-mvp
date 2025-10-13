#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SRC="$ROOT_DIR/Tests/reports"
DST="$ROOT_DIR/Reports/ola1-comercial"
mkdir -p "$DST"
cp -r "$SRC"/* "$DST"/ || true
echo "Evidencia copiada a $DST"


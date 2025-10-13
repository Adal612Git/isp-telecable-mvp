#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REPORT_DIR="$ROOT_DIR/Tests/reports"
mkdir -p "$REPORT_DIR/json" "$REPORT_DIR/csv"

# Ensure ports file exists and export HOST_* vars
bash "$ROOT_DIR/scripts/allocate_ports.sh" --write "$ROOT_DIR/.env.ports" --quiet || true
if [[ -f "$ROOT_DIR/.env.ports" ]]; then
  set -a; source "$ROOT_DIR/.env.ports"; set +a
fi

docker run --rm --network=telecable-net \
  -u $(id -u):$(id -g) \
  -e HOST_ORQ_PORT \
  -e K6_ORQ_URL=${K6_ORQ_URL:-http://app-orquestador:8010} \
  -v "$ROOT_DIR":/work -w /work grafana/k6:0.49.0 \
  run Tests/k6/alta_clientes.js --vus 100 --duration 10s --summary-export=Tests/reports/json/k6.json

echo "k6 tests OK."

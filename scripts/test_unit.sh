#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REPORT_DIR="$ROOT_DIR/Tests/reports"
mkdir -p "$REPORT_DIR"

docker run --rm -v "$ROOT_DIR":/work -w /work python:3.11-slim bash -lc '
  pip install -r requirements-test.txt \
              -r services/clientes/requirements.txt \
              -r services/catalogo/requirements.txt \
              -r services/facturacion/requirements.txt \
              -r services/pagos/requirements.txt && \
  PYTHONPATH=/work pytest -q --cov=services --cov-report=xml:Tests/reports/coverage.xml --cov-report=html:Tests/reports/html/coverage \
    --junitxml=Tests/reports/junit-unit.xml --html=Tests/reports/unit.html --self-contained-html Tests/unit
'

echo "Unit tests OK."

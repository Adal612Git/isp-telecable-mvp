#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REPORT_DIR="$ROOT_DIR/Tests/reports"
mkdir -p "$REPORT_DIR"
bash "$ROOT_DIR/scripts/allocate_ports.sh" --write "$ROOT_DIR/.env.ports" --quiet || true
# Export HOST_* so they are available to child processes
if [[ -f "$ROOT_DIR/.env.ports" ]]; then
  set -a; source "$ROOT_DIR/.env.ports"; set +a
fi
bash scripts/db_reset.sh || true
docker compose --env-file .env.ports -f infra/docker-compose.yml -f docker-compose.yml restart clientes catalogo facturacion pagos orquestador >/dev/null 2>&1 || true
sleep 3

CLIENTES_PORT=${HOST_CLIENTES_PORT:-8000}
CATALOGO_PORT=${HOST_CATALOGO_PORT:-8001}
FACT_PORT=${HOST_FACTURACION_PORT:-8002}
PAGOS_PORT=${HOST_PAGOS_PORT:-8003}
ORQ_PORT=${HOST_ORQ_PORT:-8010}
WA_PORT=${HOST_WHATSAPP_PORT:-8011}
echo "→ Esperando servicios (clientes, catalogo, facturacion, pagos, orquestador)..."
for url in http://localhost:${CLIENTES_PORT}/health http://localhost:${CATALOGO_PORT}/health http://localhost:${FACT_PORT}/health http://localhost:${PAGOS_PORT}/health http://localhost:${ORQ_PORT}/health http://localhost:${WA_PORT}/health; do
  for i in {1..30}; do
    if curl -fsS "$url" >/dev/null; then break; fi; sleep 2; done
done

docker run --rm --network=host   -e HOST_CLIENTES_PORT -e HOST_CATALOGO_PORT -e HOST_FACTURACION_PORT -e HOST_PAGOS_PORT -e HOST_ORQ_PORT -e HOST_WHATSAPP_PORT   -v "$ROOT_DIR":/work -w /work python:3.11-slim bash -lc '
  pip install -r requirements-test.txt && \
  pytest -q --junitxml=Tests/reports/junit-int.xml --html=Tests/reports/integration.html --self-contained-html Tests/integration
'

echo "Integration tests OK."

mkdir -p "$REPORT_DIR/har"
{
  echo '{"entries": ['
  curl -sw '{"url":"%{url_effective}","code":%{http_code},"time_total":%{time_total}}\n' -o /dev/null http://localhost:${CLIENTES_PORT}/health
  echo ','
  curl -sw '{"url":"%{url_effective}","code":%{http_code},"time_total":%{time_total}}\n' -o /dev/null http://localhost:${CATALOGO_PORT}/planes
  echo ','
  curl -sw '{"url":"%{url_effective}","code":%{http_code},"time_total":%{time_total}}\n' -o /dev/null http://localhost:${FACT_PORT}/health
  echo ']}'
} > "$REPORT_DIR/har/integration.har"

# CSV de tiempos por endpoint
mkdir -p "$REPORT_DIR/csv"
{
  echo "endpoint,time_total"
  echo -n "/clientes/health,"; curl -sw "%{time_total}\n" -o /dev/null http://localhost:${CLIENTES_PORT}/health
  echo -n "/catalogo/planes,"; curl -sw "%{time_total}\n" -o /dev/null http://localhost:${CATALOGO_PORT}/planes
  echo -n "/facturacion/health,"; curl -sw "%{time_total}\n" -o /dev/null http://localhost:${FACT_PORT}/health
} > "$REPORT_DIR/csv/times.csv"

# Generar CSV de 100 CFDIs
echo "→ Generando lote de 100 CFDIs (CSV)"
python - << 'PY'
import requests, json
import os
CLIENTES_PORT=os.environ.get('HOST_CLIENTES_PORT','8000')
FACT_PORT=os.environ.get('HOST_FACTURACION_PORT','8002')
payload=[{"cliente_id":1,"total":100.0} for _ in range(100)]
r=requests.post(f'http://localhost:{FACT_PORT}/facturacion/generar-masiva?csv=1', json=payload)
open('Tests/reports/csv/cfdis_100.csv','wb').write(r.content)
print('Wrote cfdis_100.csv', r.status_code)
PY

# Conciliación a CSV (desde JSON payload)
python - << 'PY'
import requests, csv, io
import os
PAGOS_PORT=os.environ.get('HOST_PAGOS_PORT','8003')
r=requests.get(f'http://localhost:{PAGOS_PORT}/pagos/conciliar')
csv_text=r.json().get('csv','')
open('Tests/reports/csv/conciliacion.csv','w').write(csv_text)
print('Wrote conciliacion.csv')
PY

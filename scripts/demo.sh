#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEMA_FILE="${ROOT_DIR}/infra/postgres/schema.sql"
ROUTER_SCRIPT="${ROOT_DIR}/scripts/router_emulator.py"

DB_USER="${PGUSER:-isp_admin}"
DB_PASS="${PGPASSWORD:-admin}"
DB_HOST="${PGHOST:-localhost}"
DB_PORT="${PGPORT:-5432}"
DB_NAME="${PGDATABASE:-isp_mvp}"

CLIENT_PORTAL_URL="${DEMO_PORTAL_CLIENTE_URL:-http://localhost:5173}"
TECH_PORTAL_URL="${DEMO_PORTAL_TECNICO_URL:-http://localhost:5174}"
BACKOFFICE_URL="${DEMO_BACKOFFICE_URL:-http://localhost:8091}"

CLIENTES_API="${DEMO_CLIENTES_API:-http://localhost:8000}"
TICKETS_API="${DEMO_TICKETS_API:-http://localhost:8006}"
PAGOS_API="${DEMO_PAGOS_API:-http://localhost:8003}"
ORQ_API="${DEMO_ORQ_API:-http://localhost:8010}"

if ! command -v psql >/dev/null 2>&1; then
  echo "[demo] psql command not found. Install PostgreSQL client or export PG* env variables for remote access."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  DOCKER_COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  DOCKER_COMPOSE_CMD=(docker-compose)
else
  echo "[demo] docker compose command not found."
  exit 1
fi

if ! command -v python >/dev/null 2>&1; then
  echo "[demo] python command not found."
  exit 1
fi

echo "[demo] Loading demo schema into ${DB_NAME} at ${DB_HOST}:${DB_PORT}..."
PGPASSWORD="$DB_PASS" psql \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -f "$SCHEMA_FILE"

echo "[demo] Starting docker compose stack..."
"${DOCKER_COMPOSE_CMD[@]}" up -d

echo "[demo] Waiting for services to boot..."
sleep 10

open_url() {
  local url="$1"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 &
  elif command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 &
  elif command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /C start "" "$url" >/dev/null 2>&1 &
  else
    echo "[demo] Open manually: $url"
    return
  }
  echo "[demo] Opening ${url}"
}

echo "[demo] Launching router emulator..."
python "$ROUTER_SCRIPT" &
ROUTER_PID=$!

cleanup() {
  echo
  echo "[demo] Stopping router emulator..."
  if kill "$ROUTER_PID" >/dev/null 2>&1; then
    wait "$ROUTER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

open_url "$CLIENT_PORTAL_URL"
open_url "$TECH_PORTAL_URL"
open_url "$BACKOFFICE_URL"

echo "[demo] Collecting summary from services..."
python - <<PY
import json
import urllib.request
import urllib.error
import time

targets = {
    "clientes": "${CLIENTES_API}/clientes",
    "tickets": "${TICKETS_API}/tickets",
    "pagos_pendientes": "${PAGOS_API}/pagos/pendientes",
    "pagos_conciliacion": "${PAGOS_API}/pagos/conciliar",
    "router_estado": "${ORQ_API}/router/status/R-001",
}

def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read()
            if not data:
                return None
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type or url.endswith("/conciliar"):
                try:
                    return json.loads(data.decode("utf-8"))
                except json.JSONDecodeError:
                    return data.decode("utf-8")
            return data.decode("utf-8")
    except urllib.error.URLError as exc:
        return {"error": str(exc)}

def print_header(title):
    print("\\n=== {} ===".format(title))

clientes = fetch(targets["clientes"])
print_header("Clientes creados")
if isinstance(clientes, list):
    for item in clientes:
        print(f"[{item.get('id')}] {item.get('nombre')} - {item.get('estatus')} (plan {item.get('plan_id')})")
else:
    print(clientes)

tickets = fetch(targets["tickets"])
print_header("Tickets abiertos / cerrados")
if isinstance(tickets, list):
    for item in tickets:
        print(f"#{item.get('id')}: {item.get('tipo')} [{item.get('estado')}] cliente {item.get('clienteId')}")
else:
    print(tickets)

pendientes = fetch(targets["pagos_pendientes"])
print_header("Pagos procesados (pendientes)")
if isinstance(pendientes, list):
    for item in pendientes:
        print(f"{item.get('referencia')} - {item.get('estatus')} - {item.get('monto')} MXN")
else:
    print(pendientes)

conciliacion = fetch(targets["pagos_conciliacion"])
print_header("Pagos conciliados")
if isinstance(conciliacion, dict) and "csv" in conciliacion:
    lines = conciliacion["csv"].splitlines()[1:]
    for line in lines:
        if not line:
            continue
        ref, monto, estatus, conciliado = line.split(",")
        if conciliado == "true":
            print(f"{ref} - {estatus} - {monto} MXN")
else:
    print(conciliacion)

router = fetch(targets["router_estado"])
print_header("Estado router emulado")
print(router)
PY

echo
echo "[demo] Router emulator running with PID ${ROUTER_PID}."
echo "[demo] Press Ctrl+C to stop the emulator. Docker services remain up."
wait "$ROUTER_PID"

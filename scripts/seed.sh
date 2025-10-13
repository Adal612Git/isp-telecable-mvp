#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REPORT_DIR="$ROOT_DIR/Tests/reports"
mkdir -p "$REPORT_DIR/json"

echo "→ Esperando servicios (catalogo, clientes, facturacion, orquestador)..."
CLIENTES_PORT=${HOST_CLIENTES_PORT:-8000}
CATALOGO_PORT=${HOST_CATALOGO_PORT:-8001}
FACT_PORT=${HOST_FACTURACION_PORT:-8002}
ORQ_PORT=${HOST_ORQ_PORT:-8010}
for url in http://localhost:${CATALOGO_PORT}/health http://localhost:${CLIENTES_PORT}/health http://localhost:${FACT_PORT}/health http://localhost:${ORQ_PORT}/health; do
  for i in {1..30}; do
    if curl -fsS "$url" >/dev/null; then break; fi; sleep 2; done
done

echo "→ Seed: creando cliente de prueba vía saga (orquestador)"
CID=$(uuidgen || cat /proc/sys/kernel/random/uuid)
payload='{
  "nombre":"Juan Pérez",
  "rfc":"AAA010101AAA",
  "email":"juan@example.com",
  "telefono":"5555555555",
  "plan_id":"INT100",
  "domicilio": {"calle":"Av. 1","numero":"123","colonia":"Centro","cp":"01000","ciudad":"CDMX","estado":"CDMX","zona":"NORTE"},
  "contacto": {"nombre":"Juan Pérez","email":"juan@example.com","telefono":"5555555555"},
  "consentimiento": {"marketing": true, "terminos": true},
  "idem": "'$CID'"
}'
curl -fsS -H "Content-Type: application/json" -d "$payload" http://localhost:${ORQ_PORT}/saga/alta-cliente | tee "$REPORT_DIR/json/seed_alta_cliente.json" >/dev/null

echo "→ Seed completado."

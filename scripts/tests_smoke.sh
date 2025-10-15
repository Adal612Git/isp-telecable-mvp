#!/usr/bin/env bash
# Prueba de humo para validar endpoints básicos una vez que la demo está arriba.
set -euo pipefail

if [[ ! -f .env.ports ]]; then
  echo ".env.ports no encontrado. Ejecuta primero scripts/setup_linux.sh." >&2
  exit 1
fi

source .env.ports

function check_endpoint() {
  local name="$1"
  local url="$2"
  echo "Consultando $name -> $url"
  if ! curl -fsS "$url" >/dev/null; then
    echo "FALLO: no se pudo acceder a $url" >&2
    return 1
  fi
  echo "OK"
}

check_endpoint "Clientes API" "http://localhost:${HOST_CLIENTES_API_PORT:-8000}/health"
check_endpoint "Router Simulator" "http://localhost:${HOST_ROUTER_SIM_PORT:-4000}/health"
check_endpoint "Portal Cliente" "http://localhost:${HOST_CLIENTES_PORT:-3000}"

echo "Prueba de humo completada"

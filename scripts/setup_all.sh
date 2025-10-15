#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
REPORT="${LOG_DIR}/setup_report.txt"
mkdir -p "${LOG_DIR}"

info() { printf '[INFO ] %s\n' "$*"; }
warn() { printf '[WARN ] %s\n' "$*" >&2; }
fail() { printf '[FAIL ] %s\n' "$*" >&2; exit 1; }

PORTS=(5173 5174 8091 3000 9090)

info "Iniciando Telecable MVP (Linux/macOS)..."

command -v docker >/dev/null 2>&1 || fail "Docker no está instalado."
if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  fail "No se encontró docker compose. Actualiza Docker a la versión 20.10+."
fi

cd "${ROOT_DIR}"

info "Liberando puertos base (${PORTS[*]}) si están ocupados..."
for port in "${PORTS[@]}"; do
  if command -v lsof >/dev/null 2>&1 && lsof -ti ":${port}" >/dev/null 2>&1; then
    warn "Puerto ${port} ocupado. Intentando liberar..."
    PIDS=$(lsof -ti ":${port}" || true)
    if [[ -n "${PIDS}" ]]; then
      kill ${PIDS} >/dev/null 2>&1 || warn "No se pudo terminar procesos en ${port}. Revisa permisos."
    fi
  fi
done

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    info "Generando .env desde .env.example"
    cp .env.example .env
  else
    fail "No existe .env ni .env.example. Crea uno antes de continuar."
  fi
else
  info ".env detectado. Se conservará."
fi

info "Asignando puertos disponibles (.env.ports)..."
bash scripts/allocate_ports.sh --write .env.ports --force --quiet || fail "No se pudo generar .env.ports"

info "Levantando contenedores con docker compose..."
"${COMPOSE[@]}" --env-file .env.ports -f infra/docker-compose.yml -f docker-compose.yml up -d --build || fail "docker compose up falló."

"${COMPOSE[@]}" --env-file .env.ports -f infra/docker-compose.yml -f docker-compose.yml ps > "${LOG_DIR}/compose_status.txt"

HOST_PORTAL_CLIENTE_PORT=$(grep -E '^HOST_PORTAL_CLIENTE_PORT=' .env.ports | cut -d= -f2)
HOST_PORTAL_TECNICO_PORT=$(grep -E '^HOST_PORTAL_TECNICO_PORT=' .env.ports | cut -d= -f2)
HOST_PORTAL_FACTURACION_PORT=$(grep -E '^HOST_PORTAL_FACTURACION_PORT=' .env.ports | cut -d= -f2)
HOST_BACKOFFICE_PORT=$(grep -E '^HOST_BACKOFFICE_PORT=' .env.ports | cut -d= -f2)
HOST_GRAFANA_PORT=$(grep -E '^HOST_GRAFANA_PORT=' .env.ports | cut -d= -f2)
HOST_PROMETHEUS_PORT=$(grep -E '^HOST_PROMETHEUS_PORT=' .env.ports | cut -d= -f2)

END_TS="$(date '+%Y-%m-%d %H:%M:%S')"
{
  echo "=============================================="
  echo "Telecable MVP - Resumen setup"
  echo "Finalizado: ${END_TS}"
  echo
  echo "Contenedores desplegados:"
  cat "${LOG_DIR}/compose_status.txt"
  echo
  echo "Puertos asignados:"
  cat .env.ports
  echo
  echo "Accesos:"
  echo " - Portal Cliente:      http://localhost:${HOST_PORTAL_CLIENTE_PORT:-5173}"
  echo " - Portal Técnico:      http://localhost:${HOST_PORTAL_TECNICO_PORT:-5174}"
  echo " - Portal Facturación:  http://localhost:${HOST_PORTAL_FACTURACION_PORT:-8091}"
  echo " - Backoffice:          http://localhost:${HOST_BACKOFFICE_PORT:-8089}"
  echo " - Grafana:             http://localhost:${HOST_GRAFANA_PORT:-3000}"
  echo " - Prometheus:          http://localhost:${HOST_PROMETHEUS_PORT:-9090}"
  echo "=============================================="
} > "${REPORT}"

info "Setup completado. Resumen guardado en ${REPORT}"
info "Mostrando logs conjuntos (Ctrl+C para salir)..."
"${COMPOSE[@]}" --env-file .env.ports -f infra/docker-compose.yml -f docker-compose.yml logs -f --tail=200

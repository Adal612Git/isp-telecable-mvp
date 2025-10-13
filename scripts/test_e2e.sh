#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REPORT_DIR="$ROOT_DIR/Tests/reports"
mkdir -p "$REPORT_DIR"

# Ensure ports file exists and export HOST_* vars
bash "$ROOT_DIR/scripts/allocate_ports.sh" --write "$ROOT_DIR/.env.ports" --quiet || true
if [[ -f "$ROOT_DIR/.env.ports" ]]; then
  set -a; source "$ROOT_DIR/.env.ports"; set +a
fi

echo "→ E2E: asegurando servicios portal/cat/orq levantados"
# Permite desactivar rebuilds pesados: export E2E_BUILD=0
BUILD_ARG=$([ "${E2E_BUILD:-1}" = "1" ] && echo "--build" || true)
docker compose --env-file .env.ports -f infra/docker-compose.yml -f docker-compose.yml up -d ${BUILD_ARG} postgres catalogo clientes facturacion orquestador portal-cliente >/dev/null

# Wait for readiness
PORTAL_PORT=${HOST_PORTAL_PORT:-8088}
CAT_PORT=${HOST_CATALOGO_PORT:-8001}
ORQ_PORT=${HOST_ORQ_PORT:-8010}
CLI_PORT=${HOST_CLIENTES_PORT:-8000}
FACT_PORT=${HOST_FACTURACION_PORT:-8002}
echo "→ Esperando portal en http://localhost:${PORTAL_PORT} ..."
for i in {1..60}; do curl -fsS "http://localhost:${PORTAL_PORT}" >/dev/null && break || sleep 1; done
echo "→ Esperando catálogo en http://localhost:${CAT_PORT}/health ..."
for i in {1..60}; do curl -fsS "http://localhost:${CAT_PORT}/health" >/dev/null && break || sleep 1; done
echo "→ Esperando zonas en catálogo ..."
for i in {1..60}; do curl -fsS "http://localhost:${CAT_PORT}/zonas" | grep -q '"id"' && break || sleep 1; done
echo "→ Esperando orquestador en http://localhost:${ORQ_PORT}/health ..."
for i in {1..60}; do curl -fsS "http://localhost:${ORQ_PORT}/health" >/dev/null && break || sleep 1; done
echo "→ Esperando clientes en http://localhost:${CLI_PORT}/health ..."
for i in {1..60}; do curl -fsS "http://localhost:${CLI_PORT}/health" >/dev/null && break || sleep 1; done
echo "→ Esperando facturacion en http://localhost:${FACT_PORT}/health ..."
for i in {1..60}; do curl -fsS "http://localhost:${FACT_PORT}/health" >/dev/null && break || sleep 1; done

echo "→ E2E: preparar entorno Playwright (sin reinstalar navegadores)"

# Detectar versión de @playwright/test para alinear imagen
PW_VERSION=$(jq -r '.devDependencies["@playwright/test"] // ""' "$ROOT_DIR/Tests/e2e/package.json" 2>/dev/null | sed 's/^[^0-9]*//')
[ -z "$PW_VERSION" ] && PW_VERSION=1.56.0
PLAY_IMAGE=${E2E_PLAYWRIGHT_IMAGE:-"mcr.microsoft.com/playwright:v${PW_VERSION}-jammy"}

# Si la imagen no está y no se permite pull, evitamos demoras largas
if ! docker image inspect "$PLAY_IMAGE" >/dev/null 2>&1; then
  if [ "${E2E_PULL:-0}" != "1" ]; then
    echo "⚠️  La imagen $PLAY_IMAGE no está localmente. El pull puede tardar >3–4 min."
    echo "    Ejecuta con: E2E_PULL=1 bash scripts/test_e2e.sh  (o prepara la imagen con 'docker pull $PLAY_IMAGE')."
    exit 12
  fi
fi

docker run --rm --network=host \
  -e HOST_PORTAL_PORT \
  -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
  -e PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
  -e PW_VERSION="$PW_VERSION" \
  -v "$ROOT_DIR/Tests/e2e":/e2e \
  -v "$REPORT_DIR":/reports \
  -w /e2e "$PLAY_IMAGE" bash -lc '
  CURR_VER=$(node -p "try{require(\"@playwright/test/package.json\").version}catch(e){\"\"}");
  if [ ! -d node_modules ] || [ "$CURR_VER" != "$PW_VERSION" ]; then npm ci || npm i; fi
  npx playwright test
'

echo "E2E tests OK."

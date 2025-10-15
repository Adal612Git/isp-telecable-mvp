#!/bin/sh
set -e

cat > env.js <<'EOF'
window.__ENV__ = {
  VITE_API_CLIENTES_URL: "${VITE_API_CLIENTES_URL:-http://clientes:8000}",
  VITE_API_FACTURACION_URL: "${VITE_API_FACTURACION_URL:-http://facturacion:8002}",
  VITE_API_PAGOS_URL: "${VITE_API_PAGOS_URL:-http://pagos:8003}",
  VITE_API_ORQUESTADOR_URL: "${VITE_API_ORQUESTADOR_URL:-http://orquestador:8010}",
  VITE_API_INSTALACIONES_URL: "${VITE_API_INSTALACIONES_URL:-http://instalaciones:8004}",
  VITE_API_RED_URL: "${VITE_API_RED_URL:-http://red:8020}",
  VITE_API_TICKETS_URL: "${VITE_API_TICKETS_URL:-http://tickets:8006}",
  VITE_API_REPORTES_URL: "${VITE_API_REPORTES_URL:-http://reportes:8007}"
};
EOF

exec nginx -g 'daemon off;'
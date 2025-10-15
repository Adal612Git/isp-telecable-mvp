#!/bin/sh
set -e

cat > env.js <<'EOF'
window.__ENV__ = {
  VITE_API_FACTURACION_URL: "${VITE_API_FACTURACION_URL:-http://facturacion:8002}",
  VITE_API_PAGOS_URL: "${VITE_API_PAGOS_URL:-http://pagos:8003}",
  VITE_API_REPORTES_URL: "${VITE_API_REPORTES_URL:-http://reportes:8007}"
};
EOF

exec nginx -g 'daemon off;'
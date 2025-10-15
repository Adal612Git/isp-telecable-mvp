#!/bin/sh
set -e

cat > env.js <<'EOF'
window.__ENV__ = {
  VITE_API_CLIENTES_URL: "${VITE_API_CLIENTES_URL:-http://clientes:8000}",
  VITE_API_INSTALACIONES_URL: "${VITE_API_INSTALACIONES_URL:-http://instalaciones:8004}",
  VITE_API_TICKETS_URL: "${VITE_API_TICKETS_URL:-http://tickets:8006}",
  VITE_API_RED_URL: "${VITE_API_RED_URL:-http://red:8020}",
  VITE_API_INVENTARIO_URL: "${VITE_API_INVENTARIO_URL:-http://inventario:8008}"
};
EOF

exec nginx -g 'daemon off;'
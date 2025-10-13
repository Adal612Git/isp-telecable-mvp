#!/bin/sh
set -e

HTML=/usr/share/nginx/html/index.html
ENVJS=/usr/share/nginx/html/env.js

# Replace backend URLs with dynamic host ports if provided
CAT_PORT="${HOST_CATALOGO_PORT:-8001}"
ORQ_PORT="${HOST_ORQ_PORT:-8010}"

# Generar env.js para que el frontend conozca puertos/URLs del host
cat > "$ENVJS" <<EOF
// Generado por entrypoint.sh
window.HOST_CATALOGO_PORT = ${CAT_PORT};
window.HOST_ORQ_PORT = ${ORQ_PORT};
// URLs directas hacia servicios expuestos en el host
window.CAT_URL = 'http://localhost:${CAT_PORT}';
window.ORQ_URL = 'http://app-orquestador:8010';
EOF

chmod 644 "$ENVJS"

exec nginx -g 'daemon off;'

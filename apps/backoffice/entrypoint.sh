#!/bin/sh
set -e

HTML=/usr/share/nginx/html/index.html

CLI_PORT="${HOST_CLIENTES_PORT:-8000}"
FACT_PORT="${HOST_FACTURACION_PORT:-8002}"

if [ -f "$HTML" ]; then
  # Alpine BusyBox sed no soporta -r; usar -i con delimitador seguro
  sed -i "s|http://localhost:8000|http://localhost:${CLI_PORT}|g" "$HTML" || true
  sed -i "s|http://localhost:8002|http://localhost:${FACT_PORT}|g" "$HTML" || true
fi

exec nginx -g 'daemon off;'

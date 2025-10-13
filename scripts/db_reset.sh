#!/usr/bin/env bash
set -euo pipefail
docker exec -i infra-postgres psql -U isp_admin -d isp_mvp -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
echo "DB reset done"


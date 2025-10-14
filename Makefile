SHELL := /bin/bash
DOCKER_COMPOSE := docker compose --env-file .env.ports
ENV_FILE := .env
REPORT_DIR := Tests/reports
COMPOSE_FILES := -f infra/docker-compose.yml -f docker-compose.yml
.ONESHELL:

.PHONY: up down logs seed test test-unit test-int e2e k6 k6-smoke lint typecheck clean reports cfdi-lote cfdi-lote-export k6-load perf k6-core k6-ops portal-a11y

up:
	@echo "🚀 Levantando infraestructura y servicios..."
	@docker network inspect telecable-net >/dev/null 2>&1 || docker network create telecable-net
	@bash scripts/allocate_ports.sh --write .env.ports || exit 1
	$(DOCKER_COMPOSE) $(COMPOSE_FILES) up -d --build
	@echo "✅ Todo en ejecución. Use 'make logs service=clientes' para ver logs."

down:
	@echo "🛑 Deteniendo y limpiando..."
	$(DOCKER_COMPOSE) $(COMPOSE_FILES) down -v --remove-orphans
	@echo "🧹 Limpieza lista."

logs:
	$(DOCKER_COMPOSE) $(COMPOSE_FILES) logs -f --tail=200 $(service)

seed:
	@echo "🌱 Cargando datos de prueba..."
	bash scripts/seed.sh
	@echo "✅ Seed completado."

test:
	@echo "🧪 Ejecutando TODAS las pruebas (unit+integration+e2e+k6)..."
	$(MAKE) reports
	$(MAKE) test-unit
	$(MAKE) up
	$(MAKE) test-int
	$(MAKE) e2e
	$(MAKE) k6
	@# Copia un junit.xml agregando el de integración como referencia principal
	cp -f Tests/reports/junit-int.xml Tests/reports/junit.xml || true
	@echo "✅ Pruebas completas. Evidencia en $(REPORT_DIR)"

test-unit:
	@echo "🔹 Unit tests (pytest + coverage)"
	bash scripts/test_unit.sh

test-int:
	@echo "🔸 Integration tests contra servicios en docker"
	bash scripts/test_integration.sh

e2e:
	@echo "🔺 E2E tests (Playwright)"
	bash scripts/test_e2e.sh

k6:
	@echo "⚙️ Pruebas de carga con k6"
	bash scripts/test_k6.sh

## k6 smoke: /health en 3 servicios (p95<500ms)
k6-smoke:
	@mkdir -p $(REPORT_DIR)/json
	@echo "🏃 k6 smoke /health (clientes, catalogo, facturacion)"
	docker run --rm --network telecable-net \
	  -u $(shell id -u):$(shell id -g) \
	  -v $(CURDIR)/Tests/k6:/scripts \
	  -v $(CURDIR)/Tests/reports/json:/out \
	  grafana/k6:0.49.0 run /scripts/health_smoke.js --summary-export=/out/k6-smoke.json
	@echo "✅ k6 smoke listo → Tests/reports/json/k6-smoke.json"

## k6 core: POST /clientes y GET /catalogo/planes (10 VUs, 1m, p95<800ms)
k6-core:
	@mkdir -p $(REPORT_DIR)/json
	@echo "🏋️ k6 core: /clientes y /catalogo/planes"
	docker run --rm --network telecable-net \
	  -u $(shell id -u):$(shell id -g) \
	  -v $(CURDIR)/Tests/k6:/scripts \
	  -v $(CURDIR)/Tests/reports/json:/out \
	  grafana/k6:0.49.0 run /scripts/endpoints_smoke.js --summary-export=/out/k6-core.json
	@echo "✅ k6 core listo → Tests/reports/json/k6-core.json"

## k6 clientes directo (POST /clientes)
k6-clientes:
	@mkdir -p $(REPORT_DIR)/json
	@echo "🏋️ k6 clientes (POST /clientes)"
	docker run --rm --network telecable-net \
	  -u $(shell id -u):$(shell id -g) \
	  -e HOST_CLIENTES_PORT \
	  -v $(CURDIR)/Tests/k6:/scripts \
	  -v $(CURDIR)/Tests/reports/json:/out \
	  grafana/k6:0.49.0 run /scripts/alta_clientes_direct.js --summary-export=/out/k6-clientes.json
	@echo "✅ k6 clientes listo → Tests/reports/json/k6-clientes.json"

## k6 instalaciones ops: agendar/cerrar (5 VUs, p95<800ms)
k6-ops:
	@mkdir -p $(REPORT_DIR)/json
	@echo "🔧 k6 instalaciones: agendar/cerrar"
	docker run --rm --network telecable-net \
	  -u $(shell id -u):$(shell id -g) \
	  -v $(CURDIR)/Tests/k6:/scripts \
	  -v $(CURDIR)/Tests/reports/json:/out \
	  grafana/k6:0.49.0 run /scripts/instalaciones_smoke.js --summary-export=/out/k6-instalaciones.json
	@echo "✅ k6 instalaciones listo → Tests/reports/json/k6-instalaciones.json"

lint:
	@echo "🔍 Lint (Python + JS)"
	bash scripts/lint.sh

typecheck:
	@echo "🔎 Typecheck (mypy + tsc)"
	bash scripts/typecheck.sh

reports:
	@mkdir -p $(REPORT_DIR)/screenshots $(REPORT_DIR)/har $(REPORT_DIR)/html $(REPORT_DIR)/json $(REPORT_DIR)/csv
	@mkdir -p $(REPORT_DIR)/portal
	@mkdir -p $(REPORT_DIR)/bi $(REPORT_DIR)/migracion $(REPORT_DIR)/finanzas

clean:
	rm -rf node_modules $(REPORT_DIR) .venv

# Generate a synthetic CSV batch inside the facturacion container
cfdi-lote:
	@echo "💸 Generando lote masivo de CFDIs (100 registros) dentro de app-facturacion..."
	@docker exec app-facturacion mkdir -p /app/exports/facturacion
	@docker exec -i app-facturacion python - <<- 'PYCODE'
	import csv, random
	from datetime import datetime
	
	path = "/app/exports/facturacion"
	ts = datetime.now().strftime("%Y%m%d_%H%M")
	cfdi_file = f"{path}/cfdis_100.csv"
	conc_file = f"{path}/conciliacion.csv"
	times_file = f"{path}/times.csv"
	
	# CFDIs simulados
	with open(cfdi_file, "w", newline="", encoding="utf-8") as f:
	    w = csv.writer(f)
	    w.writerow(["folio_interno","cliente_id","plan_id","monto","estatus","detalle","tiempo_ms"])
	    tiempos = []
	    for i in range(1, 101):
	        t = random.randint(50, 300)
	        tiempos.append(t)
	        w.writerow([
	            f"CFDI-{i:03d}",
	            random.randint(1, 5),
	            random.randint(1, 3),
	            round(random.uniform(100, 500), 2),
	            "OK",
	            "Emisión simulada exitosa",
	            t,
	        ])
	
	# Conciliación simulada
	with open(conc_file, "w", newline="", encoding="utf-8") as f:
	    w = csv.writer(f)
	    w.writerow(["referencia","monto","estatus","conciliado"])
	    for i in range(1, 21):
	        w.writerow([
	            f"CFDI-{i:03d}",
	            round(random.uniform(100, 500), 2),
	            "confirmado",
	            "true",
	        ])
	
	# Estadísticas de tiempos
	def percentile(sorted_vals, p):
	    if not sorted_vals:
	        return 0
	    k = (len(sorted_vals)-1) * (p/100)
	    f = int(k)
	    c = min(f+1, len(sorted_vals)-1)
	    if f == c:
	        return sorted_vals[int(k)]
	    d0 = sorted_vals[f] * (c - k)
	    d1 = sorted_vals[c] * (k - f)
	    return int(round(d0 + d1))
	
	vals = sorted(tiempos)
	avg = sum(vals)/len(vals) if vals else 0
	p50 = percentile(vals, 50)
	p90 = percentile(vals, 90)
	p95 = percentile(vals, 95)
	p99 = percentile(vals, 99)
	mn = vals[0] if vals else 0
	mx = vals[-1] if vals else 0
	
	with open(times_file, "w", newline="", encoding="utf-8") as f:
	    w = csv.writer(f)
	    w.writerow(["stat","value_ms"])
	    w.writerow(["count", len(vals)])
	    w.writerow(["avg_ms", round(avg, 2)])
	    w.writerow(["p50_ms", p50])
	    w.writerow(["p90_ms", p90])
	    w.writerow(["p95_ms", p95])
	    w.writerow(["p99_ms", p99])
	    w.writerow(["min_ms", mn])
	    w.writerow(["max_ms", mx])
	
	print("Wrote cfdis_100.csv")
	print("Wrote conciliacion.csv")
	print("Wrote times.csv")
	PYCODE
	@docker exec app-facturacion ls -lh /app/exports/facturacion | tail -n 5
	@echo "📦 CSVs disponibles en /app/exports/facturacion dentro del contenedor app-facturacion"

# Export CSVs from the container to the host reports folder
cfdi-lote-export: cfdi-lote
	@mkdir -p Tests/reports/csv
	@echo "📤 Exportando CSV desde app-facturacion → Tests/reports/csv/"
	@docker cp app-facturacion:/app/exports/facturacion/cfdis_100.csv Tests/reports/csv/ 2>/dev/null || true
	@docker cp app-facturacion:/app/exports/facturacion/conciliacion.csv Tests/reports/csv/ 2>/dev/null || true
	@docker cp app-facturacion:/app/exports/facturacion/times.csv Tests/reports/csv/ 2>/dev/null || true
	@ls -lh Tests/reports/csv/ | tail -n 5
	@echo "✅ CSV copiados en Tests/reports/csv/"
## Run lightweight k6 load test against app-clientes (GET /clientes)
k6-load:
	@mkdir -p $(REPORT_DIR)/json
	@echo "🏋️ Ejecutando k6 contra app-clientes (/clientes)"
	docker run --rm --network telecable-net \
	  -u $(shell id -u):$(shell id -g) \
	  -v $(CURDIR)/tests:/scripts \
	  -v $(CURDIR)/Tests/reports/json:/out \
	  grafana/k6:0.49.0 run /scripts/load_test.js --summary-export=/out/k6_clientes.json
	@echo "✅ k6 finalizado. Resumen en Tests/reports/json/k6_clientes.json"

perf:
	docker run --rm --network telecable-net -v $(PWD)/tests:/scripts -v $(PWD)/exports:/exports grafana/k6 run /scripts/load_test.js | tee exports/perf_report.txt

portal-a11y:
	@echo "♿ AXE + Lighthouse portal"
	$(MAKE) e2e
	bash scripts/test_lighthouse.sh

bi-churn:
	@echo "📈 Generando backtest churn (reportes service)"
	docker compose --env-file .env.ports -f infra/docker-compose.yml -f docker-compose.yml up -d reportes >/dev/null
	@bash -lc 'curl -fsS -X POST http://localhost:$${HOST_REPORTES_PORT:-8007}/bi/churn/backtest >/dev/null || true'
	@docker cp app-reportes:/app/exports/bi/backtest.csv Tests/reports/bi/backtest.csv 2>/dev/null || true
	@docker cp app-reportes:/app/exports/bi/mape.json Tests/reports/bi/mape.json 2>/dev/null || true
	@ls -lh Tests/reports/bi || true

migrate-sample:
	@echo "📦 Migración muestra (clientes.csv)"
	@mkdir -p Tests/data/migracion
	@bash -lc 'echo "rfc,email" > Tests/data/migracion/clientes.csv && echo "AAA010101AAA,ana@example.com" >> Tests/data/migracion/clientes.csv && echo ",sin@mail" >> Tests/data/migracion/clientes.csv'
	python scripts/migrate/migrate_clients.py Tests/data/migracion/clientes.csv
	@ls -lh Tests/reports/migracion || true

cierre-mensual:
	@echo "🧾 Cierre mensual finanzas"
	python scripts/finanzas/cierre_mensual.py
	@ls -lh Tests/reports/finanzas || true

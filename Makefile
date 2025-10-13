SHELL := /bin/bash
DOCKER_COMPOSE := docker compose --env-file .env.ports
ENV_FILE := .env
REPORT_DIR := Tests/reports
COMPOSE_FILES := -f infra/docker-compose.yml -f docker-compose.yml

.PHONY: up down logs seed test test-unit test-int e2e k6 lint typecheck clean reports

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

lint:
	@echo "🔍 Lint (Python + JS)"
	bash scripts/lint.sh

typecheck:
	@echo "🔎 Typecheck (mypy + tsc)"
	bash scripts/typecheck.sh

reports:
	@mkdir -p $(REPORT_DIR)/screenshots $(REPORT_DIR)/har $(REPORT_DIR)/html $(REPORT_DIR)/json $(REPORT_DIR)/csv

clean:
	rm -rf node_modules $(REPORT_DIR) .venv

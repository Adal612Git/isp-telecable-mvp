ROOT := $(CURDIR)
SCRIPTS_DIR := $(ROOT)/scripts
DOCKER_COMPOSE := docker compose --env-file .env.ports
ENV_FILE := .env
REPORT_DIR := Tests/reports
COMPOSE_FILES := -f infra/docker-compose.yml -f docker-compose.yml

.PHONY: up down logs seed test test-unit test-int e2e k6 lint typecheck clean reports collect-reports demo-win demo db-reset

ifeq ($(OS),Windows_NT)
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command
POWERSHELL := powershell.exe -NoProfile -ExecutionPolicy Bypass -File

up:
	$(POWERSHELL) "$(SCRIPTS_DIR)/up.ps1"

down:
	$(POWERSHELL) "$(SCRIPTS_DIR)/down.ps1"

logs:
	$(POWERSHELL) "$(SCRIPTS_DIR)/logs.ps1" $(if $(service),-Service "$(service)",) $(if $(tail),-Tail $(tail),) $(if $(filter 1 true yes,$(follow)),-Follow,)

seed:
	$(POWERSHELL) "$(SCRIPTS_DIR)/seed.ps1"

test:
	$(POWERSHELL) "$(SCRIPTS_DIR)/test.ps1" $(if $(filter 1 true yes,$(pull)),-PullPlaywright,)

test-unit:
	$(POWERSHELL) "$(SCRIPTS_DIR)/test_unit.ps1"

test-int:
	$(POWERSHELL) "$(SCRIPTS_DIR)/test_integration.ps1"

e2e:
	$(POWERSHELL) "$(SCRIPTS_DIR)/test_e2e.ps1" $(if $(filter 1 true yes,$(pull)),-PullImage,)

k6:
	$(POWERSHELL) "$(SCRIPTS_DIR)/test_k6.ps1"

lint:
	$(POWERSHELL) "$(SCRIPTS_DIR)/lint.ps1"

typecheck:
	$(POWERSHELL) "$(SCRIPTS_DIR)/typecheck.ps1"

reports:
	$(POWERSHELL) "$(SCRIPTS_DIR)/reports.ps1"

clean:
	$(POWERSHELL) "$(SCRIPTS_DIR)/clean.ps1"

collect-reports:
	$(POWERSHELL) "$(SCRIPTS_DIR)/collect_reports.ps1"

db-reset:
	$(POWERSHELL) "$(SCRIPTS_DIR)/db_reset.ps1"

demo-win demo:
	$(POWERSHELL) "$(SCRIPTS_DIR)/demo.ps1"

else
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c

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
	cp -f Tests/reports/junit-int.xml Tests/reports/junit.xml || true
	@echo "✅ Pruebas completas. Evidencia en $(REPORT_DIR)"

test-unit:
	@echo "🔹 Unit tests (pytest + cobertura)"
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

collect-reports:
	bash scripts/collect_reports.sh

db-reset:
	bash scripts/db_reset.sh

demo-win demo:
	@echo "Demo disponible únicamente en Windows via scripts/demo.ps1"

endif

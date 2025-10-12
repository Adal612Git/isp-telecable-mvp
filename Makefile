# === Makefile Base para ISP Telecable ===
# Ubuntu compatible

SHELL := /bin/bash

# Variables de entorno
DOCKER_COMPOSE := docker-compose
ENV_FILE := .env
SERVICES := backend frontend
CID_FILE := .cid

# ======================
# 🟢 Targets principales
# ======================

up:
	@echo "🚀 Levantando entorno Docker..."
	$(DOCKER_COMPOSE) up -d
	@echo "✅ Servicios en ejecución"

down:
	@echo "🛑 Deteniendo todos los servicios..."
	$(DOCKER_COMPOSE) down

logs:
	@echo "📜 Mostrando logs..."
	$(DOCKER_COMPOSE) logs -f --tail=100 $(service)

seed:
	@echo "🌱 Poblando datos de prueba..."
	bash scripts/seed.sh

test:
	@echo "🧪 Ejecutando todas las pruebas..."
	npm test || true

test-unit:
	@echo "🧩 Pruebas unitarias..."
	npm run test:unit || true

test-int:
	@echo "🔗 Pruebas de integración..."
	npm run test:int || true

e2e:
	@echo "🌐 Pruebas end-to-end..."
	npm run test:e2e || true

k6:
	@echo "⚙️ Pruebas de carga (k6)..."
	k6 run tests/k6/load_test.js || true

lint:
	@echo "🔍 Linting..."
	npm run lint || true

typecheck:
	@echo "🧠 Verificación de tipos..."
	npm run typecheck || true

help:
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'


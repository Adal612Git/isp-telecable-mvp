# Ola 1 Comercial – ISP Telecable MVP

Este paquete entrega el núcleo comercial con 4 microservicios (Clientes, Catálogo, Facturación, Pagos), orquestador de sagas, 2 apps frontend (Portal Cliente y Backoffice), pruebas completas (unit/integration/e2e/k6/manual), observabilidad, idempotencia y modo emulado.

## Alcance Implementado
- Servicio Clientes (`services/clientes`): alta/consulta/actualización/listado con idempotency-key; validaciones RFC/email/teléfono; validación de zona (vía Catálogo); eventos Kafka: `ClienteCreado`, `ContratoModificado`, `ConsentimientoActualizado` (fallback a archivo en dev).
- Servicio Catálogo (`services/catalogo`): planes/combos/zonas; cálculo de precio por zona; compatibilidad tecnológica y promociones vigentes.
- Servicio Facturación (`services/facturacion`): generación masiva CFDI (emulado), timbrado asíncrono con retry simple, cancelación; almacenamiento XML en S3-compatible (MinIO).
- Servicio Pagos (`services/pagos`): procesamiento idempotente, webhook con anti-replay (HMAC), conciliación automática.
- Orquestador (`services/orquestador`): sagas AltaCliente y ProcesarPago con llamadas entre servicios y compensación básica (errores explícitos).
- Observabilidad: `/health`, `/metrics` (Prometheus), OpenTelemetry → Jaeger (exporter Thrift), logs JSON: `cid`, `service`, `timestamp`, `level`.
- Frontend apps: Portal Cliente (alta multi-paso simple), Backoffice (listado de clientes).
- Modo emulado: `PAC_MODE`, `PAYMENT_MODE` y fallbacks controlados por env.

## Dependencias y Pre-requisitos
- Docker y Docker Compose.
- Puertos libres: 5432, 29092/29093 (Kafka), 8080 (Keycloak), 16686 (Jaeger), 9090 (Prometheus), 9000/9001 (MinIO), 8000–8010, 8088–8089.

## URLs locales y credenciales demo
- Keycloak: http://localhost:8080 (admin/admin) – Realm: telecable, roles: admin/tecnico/soporte/cobranzas/cliente
- Jaeger: http://localhost:16686
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Loki: http://localhost:3100 (API)
- Tempo: http://localhost:3200 (API)
- MinIO: http://localhost:9001 (console) – (admin/admin123)
- Portal Cliente: http://localhost:${HOST_PORTAL_CLIENTE_PORT:-5173}
- Portal T�cnico: http://localhost:${HOST_PORTAL_TECNICO_PORT:-5174}
- Portal Facturaci�n: http://localhost:${HOST_PORTAL_FACTURACION_PORT:-8091}
- Backoffice: http://localhost:${HOST_BACKOFFICE_PORT:-8089}
- Clientes API: http://localhost:${HOST_CLIENTES_PORT:-8000}
- Catálogo API: http://localhost:${HOST_CATALOGO_PORT:-8001}
- Facturación API: http://localhost:${HOST_FACTURACION_PORT:-8002}
- Pagos API: http://localhost:${HOST_PAGOS_PORT:-8003}
- Orquestador: http://localhost:${HOST_ORQ_PORT:-8010}
- WhatsApp Mock: http://localhost:${HOST_WHATSAPP_PORT:-8011}

## Arranque r�pido
- Windows: ejecuta `scripts/setup_all.bat` (doble clic).
- Linux/macOS: `bash scripts/setup_all.sh`

## Comandos para ejecutar y probar
- make up
- make seed
- make test
- make test-unit
- make test-int
- make e2e
- make k6
- make logs service=clientes
- make down

## Criterios de Aceptación (objetivo)
- Alta cliente end-to-end < 3 minutos (Portal → Orquestador → Servicios).
- Facturación masiva 1,000 CFDIs < 10 minutos (emulado).
- Webhooks idempotentes con anti-replay (pagos) comprobados por pruebas.
- Portal Cliente Lighthouse ≥ 85 (estructura ligera, estática).
- Cobertura de tests ≥ 90% por servicio (objetivo; ver Reports/ola1-comercial/).

## Matriz Historia → Prueba → Evidencia
- Alta Cliente → `Tests/e2e/tests/alta-cliente.spec.ts` → `Tests/reports/html/e2e`, `Tests/reports/playwright`, `Reports/ola1-comercial/`.
- Buscar Planes → `Tests/integration/test_catalogo_filters.py` → JUnit/HTML en `Tests/reports`.
- Generar CFDI → `Tests/integration/test_facturacion_flow.py` + `Tests/unit/test_cfdi_generation.py` → Reportes en `Tests/reports` y archivo en MinIO.
- Pago y Conciliación → `Tests/integration/test_pagos_flow.py` + `Tests/unit/test_idempotencia_pagos.py` → Evidencia JSON/HTML.
- Carga Alta Cliente → `Tests/k6/alta_clientes.js` → métricas en `Tests/reports/json/k6.json`.

## Variables de Entorno clave
- Clientes: `DATABASE_URL`, `CATALOGO_URL`, `KAFKA_BROKER`, `OTEL_JAEGER_ENDPOINT`.
- Catálogo: `DATABASE_URL`, `OTEL_JAEGER_ENDPOINT`.
- Facturación: `DATABASE_URL`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `PAC_MODE`.
- Pagos: `DATABASE_URL`, `PAYMENT_MODE`, `WEBHOOK_SECRET`.
- Orquestador: `CLIENTES_URL`, `FACTURACION_URL`, `PAGOS_URL`.
 - Infra: `ROUTER_MODE` (emulated|real)

## Evidencia y Métricas
- Se recopilan automáticamente en `Tests/reports/` y se puede consolidar en `Reports/ola1-comercial/` con `scripts/collect_reports.sh`.

## Notas
- Kafka es opcional en dev; los eventos también se reflejan en `/app_events/events.log` dentro del contenedor de clientes.
- Para S3, MinIO corre en `http://localhost:9000` credenciales `minioadmin/minioadmin` (bucket `cfdi`).

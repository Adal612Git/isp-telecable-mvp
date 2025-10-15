# Ola 1 Comercial  ISP Telecable MVP

Este paquete entrega el ncleo comercial con 4 microservicios (Clientes, Catlogo, Facturacin, Pagos), orquestador de sagas, 2 apps frontend (Portal Cliente y Backoffice), pruebas completas (unit/integration/e2e/k6/manual), observabilidad, idempotencia y modo emulado.

## Fase DEMO (Oct 2025)
- Base de datos demo en 4NF: `infra/postgres/schema.sql` y carga automatizada desde `scripts/demo.sh`.
- Simulacion de router: `scripts/router_emulator.py`, reporta cada 10 s al orquestador y atiende resets.
- Portales listos para demo: Portal Cliente (5173), Portal Tecnico (5174), Backoffice (8091) y nuevo portal de facturacion estatico en `apps/portal-facturacion/public`.
- Endpoints agregados:
  - Clientes: `POST /clientes`, `GET /clientes/{id}/estado`.
  - Instalaciones: `POST /tickets/instalacion`, `PATCH /tickets/{id}/progreso`.
  - Orquestador: `POST /router/status`, `GET /router/status/{router_id}`, `POST /notificaciones`.
  - Pagos: `POST /pagos`, `GET /pagos/pendientes`.
  - Facturacion: `GET /facturacion/kpis`, `GET /facturacion/ultimas`, `PATCH /facturacion/{uuid}/pagar`.
  - Tickets: `PATCH /tickets/{id}/cerrar`, `POST /tickets/{id}/feedback` (ademas de `POST /tickets` existente).
- Demo script (`scripts/demo.sh`):
  1. ejecuta `psql` con `infra/postgres/schema.sql`.
  2. levanta servicios con `docker compose up -d`.
  3. lanza el emulador de router.
  4. abre los tres portales demo.
  5. imprime resumen (clientes, tickets, pagos, estado router).
- Dependencias nuevas:
  - Python: `requests` (ya presente en requirements, usado por el emulador).
  - Frontend: Chart.js via CDN para grafica de ingresos (sin build extra).

### ER simplificado
```
[planes] 1---* [clientes] *---1 [consentimientos]
   |                 |
   |                 *---* [contratos] *---1 [routers]
   |
   *---* [facturas] 1---* [pagos]

[clientes] *---* [tickets] 1---* [ticket_feedback]
[clientes] *---* [eventos_sistema]
[clientes] 1---1 [domicilios]
[planes] 1---* [contratos]
[tecnicos] 1---* [tickets]
[faq] (independiente)
```

## Alcance Implementado
- Servicio Clientes (`services/clientes`): alta/consulta/actualizacin/listado con idempotency-key; validaciones RFC/email/telfono; validacin de zona (va Catlogo); eventos Kafka: `ClienteCreado`, `ContratoModificado`, `ConsentimientoActualizado` (fallback a archivo en dev).
- Servicio Catlogo (`services/catalogo`): planes/combos/zonas; clculo de precio por zona; compatibilidad tecnolgica y promociones vigentes.
- Servicio Facturacin (`services/facturacion`): generacin masiva CFDI (emulado), timbrado asncrono con retry simple, cancelacin; almacenamiento XML en S3-compatible (MinIO).
- Servicio Pagos (`services/pagos`): procesamiento idempotente, webhook con anti-replay (HMAC), conciliacin automtica.
- Orquestador (`services/orquestador`): sagas AltaCliente y ProcesarPago con llamadas entre servicios y compensacin bsica (errores explcitos).
- Observabilidad: `/health`, `/metrics` (Prometheus), OpenTelemetry  Jaeger (exporter Thrift), logs JSON: `cid`, `service`, `timestamp`, `level`.
- Frontend apps: Portal Cliente (alta multi-paso simple), Backoffice (listado de clientes).
- Modo emulado: `PAC_MODE`, `PAYMENT_MODE` y fallbacks controlados por env.

## Dependencias y Pre-requisitos
- Docker y Docker Compose.
- Puertos libres: 5432, 29092/29093 (Kafka), 8080 (Keycloak), 16686 (Jaeger), 9090 (Prometheus), 9000/9001 (MinIO), 80008010, 80888089.

## URLs locales y credenciales demo
- Keycloak: http://localhost:8080 (admin/admin)  Realm: telecable, roles: admin/tecnico/soporte/cobranzas/cliente
- Jaeger: http://localhost:16686
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Loki: http://localhost:3100 (API)
- Tempo: http://localhost:3200 (API)
- MinIO: http://localhost:9001 (console)  (admin/admin123)
- Portal Cliente: http://localhost:${HOST_PORTAL_PORT:-8088}
- Backoffice: http://localhost:${HOST_BACKOFFICE_PORT:-8089}
- Clientes API: http://localhost:${HOST_CLIENTES_PORT:-8000}
- Catlogo API: http://localhost:${HOST_CATALOGO_PORT:-8001}
- Facturacin API: http://localhost:${HOST_FACTURACION_PORT:-8002}
- Pagos API: http://localhost:${HOST_PAGOS_PORT:-8003}
- Orquestador: http://localhost:${HOST_ORQ_PORT:-8010}
- WhatsApp Mock: http://localhost:${HOST_WHATSAPP_PORT:-8011}

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

## Criterios de Aceptacin (objetivo)
- Alta cliente end-to-end < 3 minutos (Portal  Orquestador  Servicios).
- Facturacin masiva 1,000 CFDIs < 10 minutos (emulado).
- Webhooks idempotentes con anti-replay (pagos) comprobados por pruebas.
- Portal Cliente Lighthouse  85 (estructura ligera, esttica).
- Cobertura de tests  90% por servicio (objetivo; ver Reports/ola1-comercial/).

## Matriz Historia  Prueba  Evidencia
- Alta Cliente  `Tests/e2e/tests/alta-cliente.spec.ts`  `Tests/reports/html/e2e`, `Tests/reports/playwright`, `Reports/ola1-comercial/`.
- Buscar Planes  `Tests/integration/test_catalogo_filters.py`  JUnit/HTML en `Tests/reports`.
- Generar CFDI  `Tests/integration/test_facturacion_flow.py` + `Tests/unit/test_cfdi_generation.py`  Reportes en `Tests/reports` y archivo en MinIO.
- Pago y Conciliacin  `Tests/integration/test_pagos_flow.py` + `Tests/unit/test_idempotencia_pagos.py`  Evidencia JSON/HTML.
- Carga Alta Cliente  `Tests/k6/alta_clientes.js`  mtricas en `Tests/reports/json/k6.json`.

## Variables de Entorno clave
- Clientes: `DATABASE_URL`, `CATALOGO_URL`, `KAFKA_BROKER`, `OTEL_JAEGER_ENDPOINT`.
- Catlogo: `DATABASE_URL`, `OTEL_JAEGER_ENDPOINT`.
- Facturacin: `DATABASE_URL`, `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `PAC_MODE`.
- Pagos: `DATABASE_URL`, `PAYMENT_MODE`, `WEBHOOK_SECRET`.
- Orquestador: `CLIENTES_URL`, `FACTURACION_URL`, `PAGOS_URL`.
 - Infra: `ROUTER_MODE` (emulated|real)

## Evidencia y Mtricas
- Se recopilan automticamente en `Tests/reports/` y se puede consolidar en `Reports/ola1-comercial/` con `scripts/collect_reports.sh`.

## Notas
- Kafka es opcional en dev; los eventos tambin se reflejan en `/app_events/events.log` dentro del contenedor de clientes.
- Para S3, MinIO corre en `http://localhost:9000` credenciales `minioadmin/minioadmin` (bucket `cfdi`).

# Pruebas Manuales (MVP Comercial)

Siga estos pasos para validar manualmente los flujos:

1) make up
   - Verifique /health:
     - Clientes: http://localhost:8000/health
     - Catálogo: http://localhost:8001/health
     - Facturación: http://localhost:8002/health
     - Pagos: http://localhost:8003/health
     - Orquestador: http://localhost:8010/health

2) make seed
   - Crea un cliente vía orquestador. Evidencia en `Tests/reports/json/seed_alta_cliente.json`.

3) Portal Cliente
   - Abrir http://localhost:8088
   - Completar formulario y enviar. Debe mostrar respuesta con `cliente.id` y `facturas`.

4) Backoffice
   - Abrir http://localhost:8089 y verificar la tabla de clientes.

5) Facturación manual
   - POST http://localhost:8002/facturacion/generar-masiva con body: `[{"cliente_id": 1, "total": 200}]`
   - GET por UUID para verificar `estatus` timbrado.

6) Pagos manual
   - POST http://localhost:8003/pagos/procesar `{ "metodo": "spei", "monto": 100, "referencia": "MAN-1" }`
   - GET http://localhost:8003/pagos/MAN-1 → `confirmado`.

7) Observabilidad
   - Jaeger: http://localhost:16686 → trace por servicio.
   - Prometheus: http://localhost:9090 (si corre desde infra) → `/metrics` de cada servicio.

8) Evidencia
   - `Tests/reports/` contiene JUnit XML, HTML, JSON, screenshots (E2E), HAR (si aplica), CSV/JSON (k6).


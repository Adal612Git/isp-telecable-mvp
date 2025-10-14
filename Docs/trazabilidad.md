# Trazabilidad US ↔ Pruebas ↔ Evidencia (Sprint 0)

- Alta Cliente
  - Pruebas: Tests/integration/test_api_clientes.py, Tests/k6/alta_clientes.js
  - Evidencia: Tests/reports/junit-int.xml, Tests/reports/html, Tests/reports/json/k6.json

- Facturación Masiva
  - Pruebas: Tests/integration/test_facturacion_flow.py, Tests/facturacion/test_lote_facturacion.py
  - Evidencia: Tests/reports/junit-int.xml, MinIO (bucket cfdi), logs JSON

- Observabilidad (/health, /metrics, tracing)
  - Pruebas: curl /health, Prometheus Targets UP, Jaeger traces
  - Evidencia: Capturas/URLs en README, dashboards en Grafana

Nota: esta matriz se ampliará con cada Historia y Sprints siguientes.

# ADR 0001 – Núcleo Comercial ISP Telecable (MVP)

Fecha: 2025-10-12

Contexto
- Se requiere un MVP comercial con servicios de Clientes, Catálogo, Facturación y Pagos.
- Observabilidad integrada (OTel→Jaeger, /metrics, logs JSON) y modo emulado para integraciones.

Decisiones
- Lenguaje/Stack: Python 3.11 + FastAPI para los servicios por velocidad de entrega y ecosistema.
- Infra: Docker Compose para laboratorio. Postgres, Kafka (opcional dev), Redis, Keycloak, Jaeger, Prometheus, Grafana, MinIO, Loki, Tempo.
- Idempotencia: Cabecera `Idempotency-Key` persistida por recurso; duplicados responden 200 con `X-Idempotent-Replay: true`.
- Eventos: Kafka si disponible; espejo a volumen `/app_events` para auditoría en dev.
- Sagas: Orquestador HTTP con compensación mínima (inactivar cliente si falla facturación).
- Facturación: CFDI emulado; timbrado asíncrono; almacenamiento en MinIO con fallback a disco.
- Pagos: Procesamiento emulado, webhooks idempotentes con HMAC y conciliación a CSV.

Consecuencias
- Fácil portabilidad a K8s en fases siguientes.
- Latencia de arranque baja; pruebas automatizadas rápidas (<2 minutos smoke).
- Se requiere endurecimiento de seguridad para producción (authz compleja, secrets, red). 

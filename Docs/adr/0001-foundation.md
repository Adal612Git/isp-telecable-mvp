# ADR 0001 — Foundation: Monorepo Observability-First

Contexto
- Monorepo con servicios Python (FastAPI) + apps Frontend
- Observabilidad integrada (OTel → Jaeger, /metrics → Prometheus, Loki)
- Paridad staging≈producción con Docker Compose y esqueletos K8s/Terraform

Decisión
- Usar Docker Compose para dev/staging local con imágenes oficiales pinneadas
- Adoptar Keycloak (OIDC) con roles base: admin, tecnico, soporte, cobranzas, cliente
- Estándar de endpoints: /health, /metrics en todos los servicios
- Provisionar Grafana con datasources (Prometheus/Loki/Tempo) y un dashboard base

Consecuencias
- Facilita smoke/E2E/k6 y monitoreo desde el primer sprint
- Simplifica onboarding; despliegues K8s se modelarán sobre los mismos contenedores

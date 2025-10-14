# SLOs y Alertas (Sprint OLA 3)

- SLO p95 < 1s y error rate < 1% por servicio (Prometheus)
- Tickets con SLA vencido (métrica `tickets_sla_breaches`)

Cómo verlo
- Prometheus: Alerts y Rules (http://localhost:9090)
- Grafana: dashboard Telecable Base (p95/error rate/RPS)

Archivos
- Prom rules: infra/prometheus/alerts/sla.yml

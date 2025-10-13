
---

## 🧱 PASO 6 — Crear ADR inicial (registro de decisiones técnicas)

```bash
mkdir -p Docs/adr
cat <<'EOF' > Docs/adr/0001-initial-architecture.md
# ADR 0001 — Arquitectura Inicial ISP Telecable

**Fecha:** 2025-10-12  
**Estado:** Aprobado  

**Decisión:**  
Se adopta una arquitectura basada en microservicios con infraestructura observada mediante Prometheus, Grafana y Jaeger.  
Keycloak se usará para autenticación y autorización; Kafka para mensajería interna.  

**Consecuencias:**  
Permite escalar cada módulo de manera independiente y garantizar observabilidad centralizada desde el Sprint 0.
EOF

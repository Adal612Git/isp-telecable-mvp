# K8s Manifests (base)

Este es un esqueleto para staging/prod. Usa Kustomize.

Estructura propuesta:
- base/: deployments y services mínimos (clientes, catalogo, facturacion)
- overlays/{staging,prod}/: values y patches por entorno

Nota: no se aplica automáticamente en Sprint 0.

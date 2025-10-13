FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/facturacion/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/facturacion/app /app/app
# Crear carpeta de exportaciones del servicio
RUN mkdir -p /app/exports/facturacion

ENV SERVICE_NAME=facturacion \
    DATABASE_URL=postgresql+psycopg2://isp_admin:admin@postgres:5432/isp_mvp \
    OTEL_JAEGER_ENDPOINT=http://jaeger:14268/api/traces \
    S3_ENDPOINT=http://minio:9000 \
    S3_ACCESS_KEY=minioadmin \
    S3_SECRET_KEY=minioadmin \
    S3_BUCKET=cfdi \
    PAC_MODE=emulated

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]

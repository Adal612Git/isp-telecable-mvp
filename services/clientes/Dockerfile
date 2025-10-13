FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/clientes/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/clientes/app /app/app

ENV SERVICE_NAME=clientes \
    DATABASE_URL=postgresql+psycopg2://isp_admin:admin@postgres:5432/isp_mvp \
    KAFKA_BROKER=infra-kafka:29093 \
    OTEL_JAEGER_ENDPOINT=http://jaeger:14268/api/traces \
    ROUTER_MODE=emulated

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


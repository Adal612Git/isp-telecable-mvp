FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/orquestador/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/orquestador/app /app/app

ENV SERVICE_NAME=orquestador \
    CLIENTES_URL=http://clientes:8000 \
    FACTURACION_URL=http://facturacion:8002 \
    PAGOS_URL=http://pagos:8003 \
    OTEL_JAEGER_ENDPOINT=http://jaeger:14268/api/traces

EXPOSE 8010

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]


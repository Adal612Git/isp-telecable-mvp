FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/whatsapp/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/whatsapp/app /app/app

ENV SERVICE_NAME=whatsapp \
    WHATSAPP_VERIFY_TOKEN=testtoken \
    OTEL_JAEGER_ENDPOINT=http://jaeger:14268/api/traces

EXPOSE 8011

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011"]


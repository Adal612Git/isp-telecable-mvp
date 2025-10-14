FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/instalaciones/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/instalaciones/app /app/app

ENV SERVICE_NAME=instalaciones \
    DB_HOST=postgres \
    DB_USER=isp_admin \
    DB_PASS=admin \
    DB_NAME=isp_mvp \
    RED_URL=http://red:8020 \
    ROUTER_MODE=emulated

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]

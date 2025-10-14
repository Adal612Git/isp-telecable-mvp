FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY services/red/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY services/red/app /app/app

ENV SERVICE_NAME=red \
    DB_HOST=postgres \
    DB_USER=isp_admin \
    DB_PASS=admin \
    DB_NAME=isp_mvp \
    ROUTER_MODE=emulated

EXPOSE 8020

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8020"]

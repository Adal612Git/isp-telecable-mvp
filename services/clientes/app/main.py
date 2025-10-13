import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from .logging_conf import configure_logging
from .metrics import setup_metrics
from .db import init_db
from .events import event_bus
from .routers import clientes as clientes_router


service_name = os.getenv("SERVICE_NAME", "clientes")
logger = configure_logging(service_name)
router_mode = os.getenv("ROUTER_MODE", "emulated")

def setup_tracing():
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    exporter = None
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint.rstrip("/") + "/v1/traces")
    else:
        jaeger_endpoint = os.getenv("OTEL_JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
        exporter = JaegerExporter(agent_host_name=None, collector_endpoint=jaeger_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


app = FastAPI(title="Servicio Clientes", version="0.1.0")


@app.on_event("startup")
async def on_startup():
    setup_tracing()
    init_db()
    await event_bus.start()
    logger.info("clientes startup", extra={"service": service_name, "router_mode": router_mode})


@app.on_event("shutdown")
async def on_shutdown():
    await event_bus.stop()
    logger.info("clientes shutdown", extra={"service": service_name})


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    cid = request.headers.get("X-Correlation-Id") or request.headers.get("X-Request-Id") or "anon"
    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception("unhandled error", extra={"cid": cid, "service": service_name})
        return JSONResponse(status_code=500, content={"detail": "internal error"})
    response.headers["X-Correlation-Id"] = cid
    return response


@app.get("/health")
def health():
    return {"status": "ok", "service": service_name}


setup_metrics(app)
app.include_router(clientes_router.router)

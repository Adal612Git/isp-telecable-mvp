import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from prometheus_fastapi_instrumentator import Instrumentator
from .logging_conf import configure_logging


service_name = os.getenv("SERVICE_NAME", "orquestador")
logger = configure_logging(service_name)


def setup_tracing():
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint.rstrip("/") + "/v1/traces")
    else:
        jaeger_endpoint = os.getenv("OTEL_JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
        exporter = JaegerExporter(agent_host_name=None, collector_endpoint=jaeger_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


app = FastAPI(title="Orquestador", version="0.1.0")

# Enable permissive CORS for dev/E2E usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    setup_tracing()


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    cid = request.headers.get("X-Correlation-Id") or request.headers.get("X-Request-Id") or "anon"
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled error", extra={"cid": cid, "service": service_name})
        return JSONResponse(status_code=500, content={"detail": "internal error"})
    response.headers["X-Correlation-Id"] = cid
    return response


@app.get("/health")
def health():
    return {"status": "ok", "service": service_name}


@app.post("/saga/alta-cliente")
async def saga_alta_cliente(body: dict):
    # Steps: cliente -> facturacion (1er factura) -> notificación
    clientes = os.getenv("CLIENTES_URL", "http://clientes:8000")
    fact = os.getenv("FACTURACION_URL", "http://facturacion:8002")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Create client
        r = await client.post(f"{clientes}/clientes", json=body, headers={"Idempotency-Key": body.get("idem", "")})
        if r.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"error clientes: {r.text}")
        cli = r.json()
        # Generate first invoice
        lote = [{"cliente_id": cli["id"], "total": 299.0}]
        r2 = await client.post(f"{fact}/facturacion/generar-masiva", json=lote)
        if r2.status_code >= 400:
            # compensate: mark client inactive
            try:
                await client.post(f"{clientes}/clientes/{cli['id']}/inactivar")
            finally:
                raise HTTPException(status_code=400, detail=f"error facturacion: {r2.text}")
        return {"cliente": cli, "facturas": r2.json()}


@app.post("/saga/procesar-pago")
async def saga_procesar_pago(body: dict):
    pagos = os.getenv("PAGOS_URL", "http://pagos:8003")
    fact = os.getenv("FACTURACION_URL", "http://facturacion:8002")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Process payment
        r = await client.post(f"{pagos}/pagos/procesar", json=body, headers={"Idempotency-Key": body.get("idem", "")})
        if r.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"error pagos: {r.text}")
        pago = r.json()
        # In a real flow, reconcile and possibly trigger invoice payment complement
        return {"pago": pago, "conciliado": True}

# expose metrics at import time
Instrumentator().instrument(app).expose(app)

import os
import json
from datetime import datetime
from typing import Any
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
try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:  # pragma: no cover
    class Instrumentator:  # type: ignore
        def instrument(self, app):
            return self
        def expose(self, app, endpoint: str = "/metrics"):
            return None
from .logging_conf import configure_logging
from .proxy_router import router as proxy_router
from pydantic import BaseModel, Field, field_validator


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
app.include_router(proxy_router)

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


class RouterStatusIn(BaseModel):
    router_id: str = Field(..., min_length=1)
    cliente_id: int = Field(..., ge=1)
    estado: str
    velocidad_mbps: int = Field(..., ge=0, le=3000)

    @field_validator("estado")
    @classmethod
    def validate_estado(cls, value: str) -> str:
        allowed = {"online", "offline", "instalando"}
        if value not in allowed:
            raise ValueError(f"estado invalido: {value}")
        return value


router_status_cache: dict[str, dict[str, Any]] = {}


@app.post("/router/status")
async def router_status(payload: RouterStatusIn):
    now = datetime.utcnow().isoformat()
    router_status_cache[payload.router_id] = {
        "router_id": payload.router_id,
        "cliente_id": payload.cliente_id,
        "estado": payload.estado,
        "velocidad_mbps": payload.velocidad_mbps,
        "timestamp": now,
    }
    logger.info(
        "router status update",
        extra={
            "service": service_name,
            "router_id": payload.router_id,
            "estado": payload.estado,
            "velocidad": payload.velocidad_mbps,
        },
    )
    response: dict[str, Any] = {"status": "ok", "timestamp": now}
    if payload.estado == "offline":
        response["accion"] = "reset"
    return response


@app.get("/router/status/{router_id}")
def obtener_router_status(router_id: str):
    data = router_status_cache.get(router_id)
    if not data:
        raise HTTPException(status_code=404, detail="No encontrado")
    return data


class NotificacionIn(BaseModel):
    canal: str
    destino: str | None = None
    asunto: str | None = None
    mensaje: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("canal")
    @classmethod
    def validate_canal(cls, value: str) -> str:
        canal = value.strip().lower()
        if canal not in {"whatsapp", "portal"}:
            raise ValueError("canal no soportado")
        return canal


@app.post("/notificaciones")
async def reenviar_notificacion(payload: NotificacionIn):
    canal = payload.canal
    delivered = False
    if canal == "whatsapp":
        wa_url = os.getenv("WHATSAPP_URL", "http://whatsapp:8011")
        template = payload.metadata.get("template", "notificacion_generica")
        vars_payload = payload.metadata.get("vars") or {"mensaje": payload.mensaje}
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.post(
                    f"{wa_url}/send-template",
                    json={
                        "to": payload.destino or "",
                        "template": template,
                        "vars": vars_payload,
                    },
                )
                delivered = True
            except Exception:
                delivered = False
    else:
        delivered = True  # portal notifications are handled in-app
    logger.info(
        "notificacion reenviada",
        extra={
            "service": service_name,
            "canal": canal,
            "destino": payload.destino,
            "entregado": delivered,
        },
    )
    return {"status": "ok", "canal": canal, "entregado": delivered}


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
    wa_url = os.getenv("WHATSAPP_URL", "http://whatsapp:8011")
    red_url = os.getenv("RED_URL", "http://red:8020")
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Process payment
        r = await client.post(f"{pagos}/pagos/procesar", json=body, headers={"Idempotency-Key": body.get("idem", "")})
        if r.status_code >= 400:
            raise HTTPException(status_code=400, detail=f"error pagos: {r.text}")
        pago = r.json()
        # In a real flow, reconcile and possibly trigger invoice payment complement
        # Send WhatsApp notification (emulado)
        try:
            await client.post(f"{wa_url}/send-template", json={
                "to": body.get("to", "0000000000"),
                "template": "pago_confirmado",
                "vars": {"referencia": pago.get("referencia")}
            })
        except Exception:
            pass
        # Reconectar tras pago conciliado (emulado)
        try:
            cli_id = int(body.get("cliente_id")) if body.get("cliente_id") is not None else None
        except Exception:
            cli_id = None
        if cli_id:
            try:
                await client.post(f"{red_url}/router/reconectar", json={"cliente_id": cli_id})
            except Exception:
                pass
        return {"pago": pago, "conciliado": True, "notificado": True, "reconectado": bool(cli_id)}

# expose metrics at import time
Instrumentator().instrument(app).expose(app)

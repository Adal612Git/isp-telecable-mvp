import os
import json
import hashlib
import hmac
from uuid import uuid4
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from prometheus_fastapi_instrumentator import Instrumentator

from .logging_conf import configure_logging
from .db import init_db, SessionLocal
from .models import Pago, Transaccion, WebhookLog, IdempotencyKey, Conciliacion


service_name = os.getenv("SERVICE_NAME", "pagos")
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


app = FastAPI(title="Servicio Pagos", version="0.1.0")


@app.on_event("startup")
async def on_startup():
    setup_tracing()
    init_db()


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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/pagos/procesar")
def procesar_pago(body: dict, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    db: Session = next(get_db())
    try:
        if idempotency_key:
            existing = db.query(IdempotencyKey).filter(IdempotencyKey.key == idempotency_key).first()
            if existing:
                return json.loads(existing.response)
        referencia = body.get("referencia") or str(uuid4())
        metodo = body.get("metodo", "spei")
        monto = float(body.get("monto", 0))
        pago = Pago(referencia=referencia, metodo=metodo, monto=monto, estatus="confirmado")
        db.add(pago)
        db.flush()
        tx = Transaccion(pago_ref=referencia, provider=metodo.upper(), provider_tx=str(uuid4()), exitoso=True)
        db.add(tx)
        db.add(Conciliacion(referencia=referencia, conciliado=True))
        db.commit()
        resp = {"referencia": referencia, "estatus": "confirmado", "monto": monto}
        if idempotency_key:
            db.add(IdempotencyKey(key=idempotency_key, reference=referencia, response=json.dumps(resp)))
            db.commit()
        return resp
    finally:
        db.close()


@app.get("/pagos/{referencia}")
def obtener_pago(referencia: str):
    db: Session = next(get_db())
    try:
        p = db.query(Pago).filter(Pago.referencia == referencia).first()
        if not p:
            raise HTTPException(status_code=404, detail="No encontrado")
        return {"referencia": p.referencia, "estatus": p.estatus, "monto": p.monto}
    finally:
        db.close()


@app.post("/pagos/webhook")
async def webhook(request: Request, x_signature: str | None = Header(default=None)):
    secret = os.getenv("WEBHOOK_SECRET", "devsecret")
    # Simple anti-replay: event_id uniqueness
    db: Session = next(get_db())
    try:
        body = await request.json()
        event_id = body.get("id") or str(uuid4())
        if db.query(WebhookLog).filter(WebhookLog.event_id == event_id).first():
            return {"status": "ignored"}
        # naive HMAC check
        raw = json.dumps(body, sort_keys=True).encode("utf-8")
        expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        if x_signature and x_signature != expected:
            raise HTTPException(status_code=401, detail="Invalid signature")
        db.add(WebhookLog(event_id=event_id, payload=json.dumps(body)))
        db.commit()
        return {"status": "ok"}
    finally:
        db.close()


@app.get("/pagos/conciliar")
def conciliar():
    db: Session = next(get_db())
    try:
        # Simple reconciliation report: list confirmed payments
        pagos = db.query(Pago).all()
        rows = ["referencia,monto,estatus,conciliado"]
        for p in pagos:
            conc = db.query(Conciliacion).filter(Conciliacion.referencia == p.referencia).first()
            rows.append(f"{p.referencia},{p.monto:.2f},{p.estatus},{'true' if conc and conc.conciliado else 'false'}")
        csv = "\n".join(rows)
        return JSONResponse(content={"csv": csv})
    finally:
        db.close()

# expose metrics at import time
Instrumentator().instrument(app).expose(app)

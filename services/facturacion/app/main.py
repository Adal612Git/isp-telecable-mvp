import os
import uuid as uuidlib
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
# Optional deps for local testing: boto3 and prometheus instrumentator
try:
    import boto3  # type: ignore
except Exception:  # pragma: no cover - tolerate missing boto3 in unit envs
    boto3 = None

from .logging_conf import configure_logging
from .db import init_db, SessionLocal
from .models import Factura
try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:  # pragma: no cover - provide a no-op fallback
    class Instrumentator:  # type: ignore
        def instrument(self, app):
            return self
        def expose(self, app, endpoint: str = "/metrics"):
            return None


service_name = os.getenv("SERVICE_NAME", "facturacion")
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


def s3_client():
    endpoint = os.getenv("S3_ENDPOINT") or os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    access = os.getenv("S3_ACCESS_KEY") or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret = os.getenv("S3_SECRET_KEY") or os.getenv("MINIO_SECRET_KEY", "minioadmin")
    if boto3 is None:
        # Return a dummy object to trigger local fallback paths
        class _Dummy:
            def create_bucket(self, *a, **k):
                raise RuntimeError("boto3 not available")
            def put_object(self, *a, **k):
                raise RuntimeError("boto3 not available")
        return _Dummy()
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name="us-east-1",
    )


app = FastAPI(title="Servicio Facturación", version="0.1.0")

# Enable permissive CORS for Backoffice usage in dev/E2E
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
try:
    # Registrar rutas separadas
    from .routes.facturacion_lote import router as fact_lote_router
    app.include_router(fact_lote_router)
except Exception:
    # Evitar fallar en import para ciertos entornos de test
    pass


@app.on_event("startup")
async def on_startup():
    setup_tracing()
    init_db()
    # Ensure bucket exists
    s3 = s3_client()
    bucket = os.getenv("S3_BUCKET") or os.getenv("MINIO_BUCKET", "cfdi")
    try:
        s3.create_bucket(Bucket=bucket)
    except Exception:
        pass
    # Start simple event consumer from shared volume
    import asyncio
    asyncio.create_task(consume_events())


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


def generar_cfdi_xml(cliente_id: int, total: float, uuid: str) -> str:
    # Simplified CFDI 4.0-like XML
    return (
        f"<cfdi:Comprobante Version=\"4.0\" Total=\"{total:.2f}\">"
        f"<cfdi:Emisor Rfc=\"AAA010101AAA\"/>"
        f"<cfdi:Receptor Rfc=\"XEXX010101000\"/>"
        f"<tfd:TimbreFiscalDigital UUID=\"{uuid}\"/>"
        f"</cfdi:Comprobante>"
    )


def timbrar_emulado(xml: str) -> str:
    # In emulated mode, immediately return timbre UUID
    return str(uuidlib.uuid4())


def upload_xml_to_s3(xml: str, key: str):
    try:
        s3 = s3_client()
        bucket = os.getenv("S3_BUCKET") or os.getenv("MINIO_BUCKET", "cfdi")
        s3.put_object(Bucket=bucket, Key=key, Body=xml.encode("utf-8"), ContentType="application/xml")
        return f"s3://{bucket}/{key}"
    except Exception:
        # Dev fallback: write to local path
        os.makedirs("/tmp/cfdi", exist_ok=True)
        with open(f"/tmp/cfdi/{key}", "w", encoding="utf-8") as f:
            f.write(xml)
        return f"file:///tmp/cfdi/{key}"


def procesar_timbrado(factura_id: int):
    db: Session = SessionLocal()
    try:
        fac = db.query(Factura).filter(Factura.id == factura_id).first()
        if not fac:
            return
        uuid = timbrar_emulado(f"xml-{fac.uuid}")
        fac.estatus = "timbrado"
        db.commit()
        logger.info("Factura timbrada", extra={"service": service_name, "cid": fac.uuid})
    finally:
        db.close()


@app.post("/facturacion/generar-masiva")
def generar_masiva(lote: list[dict], bg: BackgroundTasks, csv: int = 0):
    db: Session = SessionLocal()
    try:
        out = []
        rows = ["uuid,cliente_id,total,estatus,time_ms"]
        for item in lote:
            cliente_id = int(item.get("cliente_id"))
            total = float(item.get("total", 0))
            uuid = str(uuidlib.uuid4())
            t0 = datetime.utcnow()
            xml = generar_cfdi_xml(cliente_id, total, uuid)
            key = f"{uuid}.xml"
            upload_xml_to_s3(xml, key)
            fac = Factura(uuid=uuid, cliente_id=cliente_id, total=total, xml_path=key, estatus="pendiente")
            db.add(fac)
            db.flush()
            bg.add_task(procesar_timbrado, fac.id)
            dt = (datetime.utcnow() - t0).total_seconds() * 1000.0
            out.append({"uuid": uuid, "estatus": "pendiente"})
            rows.append(f"{uuid},{cliente_id},{total:.2f},pendiente,{int(dt)}")
        db.commit()
        if csv:
            body = "\n".join(rows)
            return Response(content=body, media_type="text/csv")
        else:
            return out
    finally:
        db.close()


@app.get("/facturacion/{uuid}")
def obtener_factura(uuid: str):
    db: Session = SessionLocal()
    try:
        fac = db.query(Factura).filter(Factura.uuid == uuid).first()
        if not fac:
            raise HTTPException(status_code=404, detail="No encontrado")
        return {"uuid": fac.uuid, "total": fac.total, "estatus": fac.estatus, "xml_path": fac.xml_path}
    finally:
        db.close()


@app.post("/facturacion/{uuid}/cancelar")
def cancelar(uuid: str):
    db: Session = SessionLocal()
    try:
        fac = db.query(Factura).filter(Factura.uuid == uuid).first()
        if not fac:
            raise HTTPException(status_code=404, detail="No encontrado")
        fac.estatus = "cancelado"
        db.commit()
        return {"uuid": fac.uuid, "estatus": fac.estatus, "acuse": f"Cancelado-{datetime.utcnow().isoformat()}"}
    finally:
        db.close()


@app.get("/facturacion/stats")
def stats():
    db: Session = SessionLocal()
    try:
        total = db.query(Factura).count()
        timbradas = db.query(Factura).filter(Factura.estatus == "timbrado").count()
        pendientes = db.query(Factura).filter(Factura.estatus == "pendiente").count()
        canceladas = db.query(Factura).filter(Factura.estatus == "cancelado").count()
        return {"total": total, "timbradas": timbradas, "pendientes": pendientes, "canceladas": canceladas}
    finally:
        db.close()


async def consume_events():
    import asyncio, json, os
    path = "/app_events/events.log"
    pos = 0
    while True:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    f.seek(pos)
                    for line in f:
                        pos = f.tell()
                        try:
                            evt = json.loads(line)
                            if evt.get("topic") == "ClienteCreado":
                                logger.info("consumed ClienteCreado", extra={"service": service_name, "cid": str(evt.get("payload", {}).get("cliente_id"))})
                        except Exception:
                            pass
        except Exception:
            pass
        await asyncio.sleep(2)

# expose metrics at import time
Instrumentator().instrument(app).expose(app)

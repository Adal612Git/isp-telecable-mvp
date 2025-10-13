import os
from datetime import datetime, timedelta
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

from .logging_conf import configure_logging
from .metrics import setup_metrics
from .db import init_db, SessionLocal
from .models import Plan, Combo, ZonaCobertura, CompatibilidadTecnologica
from .schemas import PlanOut, ComboOut


service_name = os.getenv("SERVICE_NAME", "catalogo")
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


app = FastAPI(title="Servicio Catálogo", version="0.1.0")

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
    init_db()
    logger.info("catalogo startup", extra={"service": service_name})
    # Seed minimal data on first run (idempotent)
    db: Session = SessionLocal()
    try:
        if not db.query(ZonaCobertura).first():
            zonas = [
                ZonaCobertura(nombre="NORTE", factor_precio=1.0, tecnologias="FTTH,HFC"),
                ZonaCobertura(nombre="SUR", factor_precio=1.1, tecnologias="FTTH"),
            ]
            db.add_all(zonas)
            db.flush()
        if not db.query(Plan).first():
            planes = [
                Plan(codigo="INT100", tecnologia="FTTH", velocidad=100, precio_base=299.0),
                Plan(codigo="INT300", tecnologia="FTTH", velocidad=300, precio_base=499.0),
                Plan(codigo="HFC50", tecnologia="HFC", velocidad=50, precio_base=199.0),
            ]
            db.add_all(planes)
        if not db.query(CompatibilidadTecnologica).first():
            # Allow all listed combos by default
            for zona in db.query(ZonaCobertura).all():
                for t in zona.tecnologias.split(","):
                    db.add(CompatibilidadTecnologica(tecnologia=t, zona=zona.nombre))
        if not db.query(Combo).first():
            db.add(
                Combo(
                    nombre="Doble Play",
                    descripcion="Internet + TV",
                    descuento_pct=10.0,
                    vigente_desde=datetime.utcnow(),
                    vigente_hasta=datetime.utcnow() + timedelta(days=30),
                    activo=True,
                )
            )
        db.commit()
    finally:
        db.close()


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


setup_metrics(app)


@app.get("/planes")
def get_planes(zona: str | None = None, tecnologia: str | None = None, velocidad: int | None = None):
    db: Session = SessionLocal()
    try:
        q = db.query(Plan)
        if tecnologia:
            q = q.filter(Plan.tecnologia == tecnologia)
        if velocidad:
            q = q.filter(Plan.velocidad >= velocidad)
        planes = q.all()
        factor = 1.0
        if zona:
            z = db.query(ZonaCobertura).filter(ZonaCobertura.nombre == zona).first()
            factor = z.factor_precio if z else 1.0
            # filter by compatibility
            comp = {c.tecnologia for c in db.query(CompatibilidadTecnologica).filter(CompatibilidadTecnologica.zona == zona).all()}
            planes = [p for p in planes if p.tecnologia in comp]
        out = [
            {"codigo": p.codigo, "tecnologia": p.tecnologia, "velocidad": p.velocidad, "precio": round(p.precio_base * factor, 2)}
            for p in planes
        ]
        return out
    finally:
        db.close()


@app.get("/combos")
def get_combos():
    db: Session = SessionLocal()
    try:
        now = datetime.utcnow()
        combos = db.query(Combo).filter(Combo.activo == True).all()
        out = [
            ComboOut(
                nombre=c.nombre,
                descripcion=c.descripcion,
                descuento_pct=c.descuento_pct,
                vigente_desde=c.vigente_desde,
                vigente_hasta=c.vigente_hasta,
            )
            for c in combos
            if c.vigente_desde <= now <= c.vigente_hasta
        ]
        return out
    finally:
        db.close()


@app.get("/zonas")
def get_zonas():
    db: Session = SessionLocal()
    try:
        zonas = db.query(ZonaCobertura).all()
        return [{"id": z.nombre, "factor": z.factor_precio, "tecnologias": z.tecnologias.split(",")} for z in zonas]
    finally:
        db.close()

# Aliases with /catalogo prefix for gateway-less testing
app.add_api_route("/catalogo/planes", get_planes, methods=["GET"])
app.add_api_route("/catalogo/combos", get_combos, methods=["GET"])
app.add_api_route("/catalogo/zonas", get_zonas, methods=["GET"])

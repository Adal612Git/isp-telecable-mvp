import os
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import init_db, SessionLocal
from .models import IdempotencyKey

try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:
    class Instrumentator:  # type: ignore
        def instrument(self, app):
            return self
        def expose(self, app, endpoint: str = "/metrics"):
            return None


service_name = os.getenv("SERVICE_NAME", "red")
router_mode = os.getenv("ROUTER_MODE", "emulated")

app = FastAPI(title="Servicio Red", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": service_name, "mode": router_mode}


def get_db() -> Session:
    return SessionLocal()


def idem_get_or_store(db: Session, key: str, resource: str, resp: str | None = None):
    rec = db.query(IdempotencyKey).filter(IdempotencyKey.key == key, IdempotencyKey.resource == resource).first()
    if rec:
        return True, rec.response
    if resp is not None:
        rec = IdempotencyKey(key=key, resource=resource, response=resp)
        db.add(rec)
        db.commit()
    return False, None


class RouterActionIn(BaseModel):
    cliente_id: int


@app.post("/router/provisionar-pppoe")
def provisionar_pppoe(body: RouterActionIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    db = get_db()
    try:
        key = idempotency_key or f"pppoe-{body.cliente_id}"
        found, resp = idem_get_or_store(db, key, "pppoe")
        if found:
            return {"status": "ok", "replay": True}
        # Emulado: éxito inmediato
        idem_get_or_store(db, key, "pppoe", resp="ok")
        return {"status": "ok"}
    finally:
        db.close()


@app.post("/router/crear-usuario-hotspot")
def crear_usuario_hotspot(body: RouterActionIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    db = get_db()
    try:
        key = idempotency_key or f"hotspot-{body.cliente_id}"
        found, resp = idem_get_or_store(db, key, "hotspot")
        if found:
            return {"status": "ok", "replay": True}
        idem_get_or_store(db, key, "hotspot", resp="ok")
        return {"status": "ok"}
    finally:
        db.close()


@app.post("/router/cortar")
def cortar(body: RouterActionIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    db = get_db()
    try:
        key = idempotency_key or f"cortar-{body.cliente_id}"
        found, _ = idem_get_or_store(db, key, "cortar")
        if found:
            return {"status": "ok", "replay": True}
        idem_get_or_store(db, key, "cortar", resp="ok")
        return {"status": "ok"}
    finally:
        db.close()


@app.post("/router/reconectar")
def reconectar(body: RouterActionIn, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    db = get_db()
    try:
        key = idempotency_key or f"reconectar-{body.cliente_id}"
        found, _ = idem_get_or_store(db, key, "reconectar")
        if found:
            return {"status": "ok", "replay": True}
        idem_get_or_store(db, key, "reconectar", resp="ok")
        return {"status": "ok"}
    finally:
        db.close()


class PingIn(BaseModel):
    host: str


@app.post("/diagnostico/ping")
def ping(body: PingIn):
    # Emulado: responde ok con latencia fija
    return {"host": body.host, "ok": True, "latency_ms": 42}


@app.post("/diagnostico/traceroute")
def traceroute(body: PingIn):
    # Emulado: hops fijos
    return {"host": body.host, "hops": ["gw.local", "isp-edge", "upstream"]}


Instrumentator().instrument(app).expose(app)

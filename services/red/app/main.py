import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import init_db, SessionLocal
from .models import IdempotencyKey, RouterState

try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    class Instrumentator:  # type: ignore
        def instrument(self, app):
            return self

        def expose(self, app, endpoint: str = "/metrics"):
            return None


service_name = os.getenv("SERVICE_NAME", "red")
router_mode = os.getenv("ROUTER_MODE", "emulated")
log_path = Path(os.getenv("ROUTER_LOG_PATH", "/app_logs/router.log"))
log_path.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("router")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(handler)

app = FastAPI(title="Servicio Red", version="0.2.0")
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


def idem_get_or_store(db: Session, key: str, resource: str, resp: Optional[str] = None):
    record = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.key == key, IdempotencyKey.resource == resource)
        .first()
    )
    if record:
        return True, record.response
    if resp is not None:
        record = IdempotencyKey(key=key, resource=resource, response=resp)
        db.add(record)
        db.commit()
    return False, None


def _serialize_state(state: RouterState) -> dict:
    ip = getattr(state, "ip_fake", None) or "189.210.10.10"
    return {
        "cliente_id": state.cliente_id,
        "conectado": state.conectado,
        "modo": state.modo,
        "latencia_ms": state.latencia_ms,
        "ip_fake": ip,
        "actualizado_en": state.actualizado_en.isoformat(),
    }


def _touch_state(
    db: Session,
    cliente_id: int,
    *,
    conectado: Optional[bool] = None,
    latencia_ms: Optional[int] = None,
) -> RouterState:
    state = (
        db.query(RouterState)
        .filter(RouterState.cliente_id == cliente_id)
        .first()
    )
    if not state:
        ip_octet = 10 + (cliente_id % 200)
        ip_block = 100 + (cliente_id % 80)
        fake_ip = f"189.210.{ip_block}.{ip_octet}"
        state = RouterState(cliente_id=cliente_id, ip_fake=fake_ip)
        db.add(state)
        db.flush()
    elif not state.ip_fake:
        ip_octet = 10 + (cliente_id % 200)
        ip_block = 100 + (cliente_id % 80)
        state.ip_fake = f"189.210.{ip_block}.{ip_octet}"
    if conectado is not None:
        state.conectado = conectado
    if latencia_ms is not None:
        state.latencia_ms = latencia_ms
    state.modo = router_mode
    state.actualizado_en = datetime.utcnow()
    db.commit()
    db.refresh(state)
    return state


def _log(action: str, state: RouterState):
    logger.info(
        "%s cliente=%s conectado=%s latencia=%sms ip=%s modo=%s",
        action,
        state.cliente_id,
        state.conectado,
        state.latencia_ms,
        state.ip_fake,
        state.modo,
    )



class RouterActionIn(BaseModel):
    cliente_id: int


@app.get("/router/status")
def list_router_status():
    db = get_db()
    try:
        rows = (
            db.query(RouterState)
            .order_by(RouterState.actualizado_en.desc())
            .limit(250)
            .all()
        )
        return [_serialize_state(r) for r in rows]
    finally:
        db.close()


@app.get("/router/status/{cliente_id}")
def get_router_status(cliente_id: int):
    db = get_db()
    try:
        state = (
            db.query(RouterState)
            .filter(RouterState.cliente_id == cliente_id)
            .first()
        )
        if not state:
            raise HTTPException(status_code=404, detail="cliente sin historial de red")
        return _serialize_state(state)
    finally:
        db.close()


@app.post("/router/provisionar-pppoe")
def provisionar_pppoe(
    body: RouterActionIn,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    db = get_db()
    try:
        key = idempotency_key or f"pppoe-{body.cliente_id}"
        found, _ = idem_get_or_store(db, key, "pppoe")
        state = _touch_state(db, body.cliente_id, conectado=True)
        _log("provisionar_pppoe", state)
        if found:
            return {"status": "ok", "replay": True, "estado": _serialize_state(state)}
        idem_get_or_store(db, key, "pppoe", resp="ok")
        return {"status": "ok", "estado": _serialize_state(state)}
    finally:
        db.close()


@app.post("/router/crear-usuario-hotspot")
def crear_usuario_hotspot(
    body: RouterActionIn,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    db = get_db()
    try:
        key = idempotency_key or f"hotspot-{body.cliente_id}"
        found, _ = idem_get_or_store(db, key, "hotspot")
        state = _touch_state(db, body.cliente_id)
        _log("crear_usuario_hotspot", state)
        if found:
            return {"status": "ok", "replay": True, "estado": _serialize_state(state)}
        idem_get_or_store(db, key, "hotspot", resp="ok")
        return {"status": "ok", "estado": _serialize_state(state)}
    finally:
        db.close()


@app.post("/router/cortar")
def cortar(
    body: RouterActionIn,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    db = get_db()
    try:
        key = idempotency_key or f"cortar-{body.cliente_id}"
        found, _ = idem_get_or_store(db, key, "cortar")
        state = _touch_state(db, body.cliente_id, conectado=False)
        _log("cortar", state)
        if found:
            return {"status": "ok", "replay": True, "estado": _serialize_state(state)}
        idem_get_or_store(db, key, "cortar", resp="ok")
        return {"status": "ok", "estado": _serialize_state(state)}
    finally:
        db.close()


@app.post("/router/reconectar")
def reconectar(
    body: RouterActionIn,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
):
    db = get_db()
    try:
        key = idempotency_key or f"reconectar-{body.cliente_id}"
        found, _ = idem_get_or_store(db, key, "reconectar")
        state = _touch_state(db, body.cliente_id, conectado=True)
        _log("reconectar", state)
        if found:
            return {"status": "ok", "replay": True, "estado": _serialize_state(state)}
        idem_get_or_store(db, key, "reconectar", resp="ok")
        return {"status": "ok", "estado": _serialize_state(state)}
    finally:
        db.close()


class PingIn(BaseModel):
    host: str
    cliente_id: Optional[int] = None


@app.post("/diagnostico/ping")
def ping(body: PingIn):
    latency = 42
    result = {"host": body.host, "ok": True, "latency_ms": latency}
    db = get_db()
    try:
        cid = body.cliente_id or int(os.getenv("PING_DEFAULT_CLIENTE", "0")) or None
        if cid:
            state = _touch_state(db, cid, latencia_ms=latency)
            _log("ping", state)
            result["estado"] = _serialize_state(state)
    finally:
        db.close()
    return result


@app.post("/diagnostico/traceroute")
def traceroute(body: PingIn):
    return {"host": body.host, "hops": ["gw.local", "isp-edge", "upstream"]}


Instrumentator().instrument(app).expose(app)

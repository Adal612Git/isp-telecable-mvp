import asyncio
import json
import os
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator, Field
from sqlalchemy.orm import Session

from .db import SessionLocal, init_db
from .models import Instalacion

try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    class Instrumentator:  # type: ignore
        def instrument(self, app):
            return self

        def expose(self, app, endpoint: str = "/metrics"):
            return None


service_name = os.getenv("SERVICE_NAME", "instalaciones")

app = FastAPI(title="Servicio Instalaciones", version="0.2.0")
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
    return {"status": "ok", "service": service_name}


class AgendarIn(BaseModel):
    clienteId: int
    ventana: str
    zona: str
    descripcion: str | None = None


class CerrarIn(BaseModel):
    evidencias: list[str]
    notas: Optional[str] = ""

    @field_validator("evidencias")
    @classmethod
    def validate_evidencias(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("evidencias requeridas")
        return value


def get_db() -> Session:
    return SessionLocal()


def _serialize(inst: Instalacion) -> dict:
    try:
        evidencias = json.loads(inst.evidencias or "[]")
    except json.JSONDecodeError:
        evidencias = []
    return {
        "id": inst.id,
        "clienteId": inst.cliente_id,
        "estado": inst.estado,
        "ventana": inst.ventana,
        "zona": inst.zona,
        "notas": inst.notas,
        "evidencias": evidencias,
        "creadoEn": inst.creado_en.isoformat(),
    }

def _tecnicos_catalogo() -> list[tuple[str, str]]:
    raw = os.getenv(
        "INSTALACIONES_TECNICOS",
        "Norte:tec-norte-01,Centro:tec-centro-01,Sur:tec-sur-01",
    )
    pairs: list[tuple[str, str]] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue
        zona, tecnico = chunk.split(":", 1)
        zona = zona.strip().lower()
        tecnico = tecnico.strip()
        if zona and tecnico:
            pairs.append((zona, tecnico))
    if not pairs:
        pairs.append(("default", "tecnico-demo-01"))
    return pairs


def _seleccionar_tecnico(zona: str) -> str:
    zona_key = zona.strip().lower()
    catalogo = _tecnicos_catalogo()
    for entry_zona, tecnico in catalogo:
        if entry_zona == zona_key:
            return tecnico
    return catalogo[0][1]


class TicketInstalacionIn(BaseModel):
    clienteId: int = Field(..., ge=1)
    zona: str
    ventana: Optional[str] = None
    descripcion: Optional[str] = None

    @field_validator("zona")
    @classmethod
    def validate_zona(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("zona requerida")
        return value


class ProgresoIn(BaseModel):
    estatus: str

    @field_validator("estatus")
    @classmethod
    def validate_estatus(cls, value: str) -> str:
        allowed = {"en_camino", "instalando", "completado"}
        if value not in allowed:
            raise ValueError(f"estatus invalido: {value}")
        return value


@app.post("/instalaciones/agendar")
def agendar(payload: AgendarIn):
    db = get_db()
    try:
        inv_url = os.getenv("INVENTARIO_URL")
        skus = os.getenv("REQUIRED_SKUS", "ONT,ROUTER")
        if inv_url and skus:
            items = ",".join(
                f"{sku.strip()}:1" for sku in skus.split(",") if sku.strip()
            )
            try:
                response = httpx.get(
                    f"{inv_url.rstrip('/')}/inventario/available",
                    params={"items": items, "zona": payload.zona},
                    timeout=5.0,
                )
                ok = response.status_code == 200 and response.json().get("ok")
                if not ok:
                    raise HTTPException(
                        status_code=409,
                        detail=f"inventario insuficiente: {response.json().get('missing')}",
                    )
            except Exception:
                # En dev no bloqueamos si inventario no responde
                pass
        inst = Instalacion(
            cliente_id=payload.clienteId,
            ventana=payload.ventana,
            zona=payload.zona,
            estado="Programada",
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return _serialize(inst)
    finally:
        db.close()


@app.put("/instalaciones/despachar/{id}")
def despachar(id: int):
    db = get_db()
    try:
        inst = db.query(Instalacion).filter(Instalacion.id == id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="No encontrado")
        if inst.estado in ("EnRuta", "EnSitio", "Completada"):
            return _serialize(inst)
        if inst.estado != "Programada":
            raise HTTPException(status_code=409, detail="Estado invalido")
        inst.estado = "EnRuta"
        db.commit()
        db.refresh(inst)
        return _serialize(inst)
    finally:
        db.close()


async def _router_provisionar(cliente_id: int) -> bool:
    red_url = os.getenv("RED_URL", "http://red:8020")
    timeout = httpx.Timeout(5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                f"{red_url}/router/provisionar-pppoe",
                json={"cliente_id": cliente_id},
            )
            return response.status_code == 200
        except Exception:
            return False


@app.put("/instalaciones/cerrar/{id}")
async def cerrar(id: int, body: CerrarIn):
    db = get_db()
    try:
        inst = db.query(Instalacion).filter(Instalacion.id == id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="No encontrado")
        if not body.evidencias:
            raise HTTPException(status_code=400, detail="Evidencias requeridas")
        inst.evidencias = json.dumps(body.evidencias)
        inst.notas = body.notas or ""
        ok = False
        for intento in range(3):
            ok = await _router_provisionar(inst.cliente_id)
            if ok:
                break
            await asyncio.sleep(0.5 * (2**intento))
        if not ok:
            inst.estado = "NoCompletada"
            db.commit()
            raise HTTPException(status_code=502, detail="Provisionamiento fallido")
        inst.estado = "Completada"
        db.commit()
        db.refresh(inst)
        return _serialize(inst)
    finally:
        db.close()


@app.get("/instalaciones/{id}")
def obtener_instalacion(id: int):
    db = get_db()
    try:
        inst = db.query(Instalacion).filter(Instalacion.id == id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="No encontrado")
        return _serialize(inst)
    finally:
        db.close()


@app.get("/instalaciones/cliente/{cliente_id}")
def instalaciones_cliente(
    cliente_id: int, limit: int = Query(10, ge=1, le=100)
):
    db = get_db()
    try:
        rows = (
            db.query(Instalacion)
            .filter(Instalacion.cliente_id == cliente_id)
            .order_by(Instalacion.creado_en.desc())
            .limit(limit)
            .all()
        )
        return [_serialize(inst) for inst in rows]
    finally:
        db.close()


@app.get("/instalaciones/agenda")
def agenda(
    zona: Optional[str] = None,
    estado: Optional[str] = None,
    limit: int = Query(25, ge=1, le=200),
):
    db = get_db()
    try:
        query = db.query(Instalacion)
        if zona:
            query = query.filter(Instalacion.zona == zona)
        if estado:
            query = query.filter(Instalacion.estado == estado)
        rows = query.order_by(Instalacion.creado_en.asc()).limit(limit).all()
        return [_serialize(inst) for inst in rows]
    finally:
        db.close()


@app.post("/tickets/instalacion")
def crear_ticket_instalacion(payload: TicketInstalacionIn):
    db = get_db()
    try:
        ventana = payload.ventana or "Ventana abierta"
        tecnico = _seleccionar_tecnico(payload.zona)
        notas = payload.descripcion.strip() if payload.descripcion else ""
        if notas:
            notas += f"\nTecnico asignado: {tecnico}"
        else:
            notas = f"Tecnico asignado: {tecnico}"
        inst = Instalacion(
            cliente_id=payload.clienteId,
            ventana=ventana,
            zona=payload.zona,
            estado="Programada",
            notas=notas,
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)
        data = _serialize(inst)
        data["tecnicoAsignado"] = tecnico
        return data
    finally:
        db.close()


PROGRESO_MAP = {
    "en_camino": "EnRuta",
    "instalando": "EnSitio",
    "completado": "Completada",
}


@app.patch("/tickets/{id}/progreso")
def actualizar_progreso(id: int, payload: ProgresoIn):
    db = get_db()
    try:
        inst = db.query(Instalacion).filter(Instalacion.id == id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="No encontrado")
        inst.estado = PROGRESO_MAP[payload.estatus]
        db.commit()
        db.refresh(inst)
        return _serialize(inst)
    finally:
        db.close()


Instrumentator().instrument(app).expose(app)

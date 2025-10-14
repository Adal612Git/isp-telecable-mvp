import os
import json
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
import httpx

from .db import init_db, SessionLocal
from .models import Instalacion

try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:
    class Instrumentator:  # type: ignore
        def instrument(self, app):
            return self
        def expose(self, app, endpoint: str = "/metrics"):
            return None


service_name = os.getenv("SERVICE_NAME", "instalaciones")

app = FastAPI(title="Servicio Instalaciones", version="0.1.0")
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

class CerrarIn(BaseModel):
    evidencias: list[str]
    notas: Optional[str] = ""

    @field_validator("evidencias")
    @classmethod
    def validate_evidencias(cls, v: list[str]) -> list[str]:
        if not v or len(v) == 0:
            raise ValueError("evidencias requeridas")
        return v


def get_db() -> Session:
    return SessionLocal()


@app.post("/instalaciones/agendar")
def agendar(payload: AgendarIn):
    db = get_db()
    try:
        # Validación de inventario (si INVENTARIO_URL y REQUIRED_SKUS están definidos)
        inv_url = os.getenv("INVENTARIO_URL")
        skus = os.getenv("REQUIRED_SKUS", "ONT,ROUTER")
        if inv_url and skus:
            items = ",".join([f"{sku.strip()}:1" for sku in skus.split(",") if sku.strip()])
            import httpx
            try:
                r = httpx.get(f"{inv_url.rstrip('/')}/inventario/available", params={"items": items, "zona": payload.zona}, timeout=5.0)
                ok = r.status_code == 200 and r.json().get("ok")
                if not ok:
                    raise HTTPException(status_code=409, detail=f"inventario insuficiente: {r.json().get('missing')}")
            except Exception:
                # si inventario no responde, no bloquear agendado
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
        return {"id": inst.id, "estado": inst.estado}
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
            return {"id": inst.id, "estado": inst.estado}
        if inst.estado != "Programada":
            raise HTTPException(status_code=409, detail="Estado inválido")
        inst.estado = "EnRuta"
        db.commit()
        return {"id": inst.id, "estado": inst.estado}
    finally:
        db.close()


async def _router_provisionar(cliente_id: int) -> bool:
    red_url = os.getenv("RED_URL", "http://red:8020")
    timeout = httpx.Timeout(5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            r = await client.post(f"{red_url}/router/provisionar-pppoe", json={"cliente_id": cliente_id})
            return r.status_code == 200
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
        # Intentar provisionar en router (hasta 3 reintentos con backoff)
        ok = False
        for i in range(3):
            ok = await _router_provisionar(inst.cliente_id)
            if ok:
                break
            await asyncio.sleep(0.5 * (2**i))
        if not ok:
            inst.estado = "NoCompletada"
            db.commit()
            raise HTTPException(status_code=502, detail="Provisionamiento fallido")
        inst.estado = "Completada"
        db.commit()
        return {"id": inst.id, "estado": inst.estado, "evidencias": body.evidencias}
    finally:
        db.close()


Instrumentator().instrument(app).expose(app)

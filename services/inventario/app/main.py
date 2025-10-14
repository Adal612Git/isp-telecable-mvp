import os
import csv
import io
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .db import init_db, SessionLocal
from .models import Stock, Reserva, Movimiento

try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
except Exception:
    class Instrumentator:  # type: ignore
        def instrument(self, app):
            return self
        def expose(self, app, endpoint: str = "/metrics"):
            return None


service_name = os.getenv("SERVICE_NAME", "inventario")

app = FastAPI(title="Servicio Inventario", version="0.1.0")
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


def get_db() -> Session:
    return SessionLocal()


class StockIn(BaseModel):
    sku: str
    zona: str = "GLOBAL"
    cantidad: int


@app.post("/inventario/lotes")
def lotes(payload: StockIn):
    db = get_db()
    try:
        s = db.query(Stock).filter(Stock.sku == payload.sku, Stock.zona == payload.zona).first()
        if not s:
            s = Stock(sku=payload.sku, zona=payload.zona, cantidad=0)
            db.add(s)
        s.cantidad += payload.cantidad
        db.add(Movimiento(tipo="ajuste", referencia="lote", zona=payload.zona, sku=payload.sku, cantidad=payload.cantidad))
        db.commit()
        return {"sku": s.sku, "zona": s.zona, "cantidad": s.cantidad}
    finally:
        db.close()


@app.get("/inventario/available")
def available(items: str, zona: str = "GLOBAL"):
    """items format: sku:qty,sku2:qty2"""
    db = get_db()
    try:
        pairs = [i for i in (items or "").split(",") if i]
        for p in pairs:
            sku, qty = p.split(":")
            qty = int(qty)
            s = db.query(Stock).filter(Stock.sku == sku, Stock.zona == zona).first()
            if not s or s.cantidad < qty:
                return {"ok": False, "missing": sku}
        return {"ok": True}
    finally:
        db.close()


class ReservaIn(BaseModel):
    instalacionId: int
    zona: str
    items: List[StockIn]


@app.post("/inventario/reservar")
def reservar(body: ReservaIn):
    db = get_db()
    try:
        # validate availability
        for it in body.items:
            s = db.query(Stock).filter(Stock.sku == it.sku, Stock.zona == body.zona).first()
            if not s or s.cantidad < it.cantidad:
                raise HTTPException(status_code=409, detail=f"stock insuficiente {it.sku}")
        # reserve (decrement)
        for it in body.items:
            s = db.query(Stock).filter(Stock.sku == it.sku, Stock.zona == body.zona).first()
            s.cantidad -= it.cantidad
            db.add(Reserva(instalacion_id=body.instalacionId, zona=body.zona, sku=it.sku, cantidad=it.cantidad))
            db.add(Movimiento(tipo="reserva", referencia=str(body.instalacionId), zona=body.zona, sku=it.sku, cantidad=it.cantidad))
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.post("/inventario/salida/{instalacion_id}")
def salida(instalacion_id: int):
    db = get_db()
    try:
        res = db.query(Reserva).filter(Reserva.instalacion_id == instalacion_id).all()
        for r in res:
            db.add(Movimiento(tipo="salida", referencia=str(instalacion_id), zona=r.zona, sku=r.sku, cantidad=r.cantidad))
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.post("/inventario/devolucion/{instalacion_id}")
def devolucion(instalacion_id: int):
    db = get_db()
    try:
        res = db.query(Reserva).filter(Reserva.instalacion_id == instalacion_id).all()
        for r in res:
            s = db.query(Stock).filter(Stock.sku == r.sku, Stock.zona == r.zona).first()
            if not s:
                s = Stock(sku=r.sku, zona=r.zona, cantidad=0)
                db.add(s)
            s.cantidad += r.cantidad
            db.add(Movimiento(tipo="devolucion", referencia=str(instalacion_id), zona=r.zona, sku=r.sku, cantidad=r.cantidad))
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.get("/inventario/auditoria.csv")
def auditoria_csv():
    db = get_db()
    try:
        rows = db.query(Movimiento).all()
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["tipo","referencia","zona","sku","cantidad","creado_en"])
        for m in rows:
            w.writerow([m.tipo, m.referencia, m.zona, m.sku, m.cantidad, m.creado_en.isoformat()])
        return buf.getvalue()
    finally:
        db.close()


Instrumentator().instrument(app).expose(app)


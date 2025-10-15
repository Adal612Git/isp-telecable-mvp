import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from .db import init_db, SessionLocal
from .models import Ticket, TicketFeedback

try:
    from prometheus_fastapi_instrumentator import Instrumentator  # type: ignore
    from prometheus_client import Gauge
except Exception:
    class Instrumentator:  # type: ignore
        def instrument(self, app):
            return self
        def expose(self, app, endpoint: str = "/metrics"):
            return None
    class Gauge:  # type: ignore
        def __init__(self, *a, **k):
            pass
        def set(self, v):
            pass


service_name = os.getenv("SERVICE_NAME", "tickets")

app = FastAPI(title="Servicio Tickets", version="0.1.0")
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


def _serialize_ticket(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "tipo": ticket.tipo,
        "prioridad": ticket.prioridad,
        "estado": ticket.estado,
        "zona": ticket.zona,
        "clienteId": ticket.cliente_id,
        "asignadoA": ticket.asignado_a,
        "slaAt": ticket.sla_at.isoformat(),
        "creadoEn": ticket.creado_en.isoformat(),
        "fechaCierre": ticket.fecha_cierre.isoformat() if ticket.fecha_cierre else None,
    }


def _sla_delta(pri: str) -> timedelta:
    return {"P1": timedelta(hours=4), "P2": timedelta(hours=8), "P3": timedelta(hours=24)}.get(pri, timedelta(hours=24))


class TicketIn(BaseModel):
    tipo: str
    prioridad: str = "P3"
    zona: str
    clienteId: int


class EstadoIn(BaseModel):
    estado: str


class FeedbackIn(BaseModel):
    puntuacion: int = Field(..., ge=1, le=5)
    comentario: str | None = None

    @field_validator("comentario")
    @classmethod
    def sanitize_comentario(cls, value: str | None) -> str | None:
        if value is not None:
            return value.strip()
        return value


tickets_sla_breaches = Gauge("tickets_sla_breaches", "Tickets con SLA vencido")


@app.post("/tickets")
def crear(payload: TicketIn):
    db = get_db()
    try:
        sla_at = datetime.utcnow() + _sla_delta(payload.prioridad)
        asignado = f"zona-{payload.zona}-01"
        t = Ticket(tipo=payload.tipo, prioridad=payload.prioridad, zona=payload.zona, cliente_id=payload.clienteId, sla_at=sla_at, asignado_a=asignado)
        db.add(t)
        db.commit()
        db.refresh(t)
        return _serialize_ticket(t)
    finally:
        db.close()


@app.put("/tickets/{id}/estado")
def cambiar_estado(id: int, body: EstadoIn):
    db = get_db()
    try:
        t = db.query(Ticket).filter(Ticket.id == id).first()
        if not t:
            raise HTTPException(status_code=404, detail="No encontrado")
        t.estado = body.estado
        db.commit()
        return {"id": t.id, "estado": t.estado}
    finally:
        db.close()


@app.get("/tickets/{id}")
def obtener(id: int):
    db = get_db()
    try:
        t = db.query(Ticket).filter(Ticket.id == id).first()
        if not t:
            raise HTTPException(status_code=404, detail="No encontrado")
        return _serialize_ticket(t)
    finally:
        db.close()


@app.patch("/tickets/{id}/cerrar")
def cerrar_ticket(id: int):
    db = get_db()
    try:
        t = db.query(Ticket).filter(Ticket.id == id).first()
        if not t:
            raise HTTPException(status_code=404, detail="No encontrado")
        t.estado = "cerrado"
        t.fecha_cierre = datetime.utcnow()
        db.commit()
        db.refresh(t)
        return _serialize_ticket(t)
    finally:
        db.close()


@app.post("/tickets/{id}/feedback")
def guardar_feedback(id: int, payload: FeedbackIn):
    db = get_db()
    try:
        t = db.query(Ticket).filter(Ticket.id == id).first()
        if not t:
            raise HTTPException(status_code=404, detail="No encontrado")
        fb = TicketFeedback(
            ticket_id=id,
            calificacion=payload.puntuacion,
            comentario=payload.comentario or "",
        )
        db.add(fb)
        db.commit()
        db.refresh(fb)
        return {
            "ticketId": id,
            "calificacion": fb.calificacion,
            "comentario": fb.comentario,
            "creadoEn": fb.creado_en.isoformat(),
        }
    finally:
        db.close()


@app.get("/tickets/sla/breaches")
def breaches():
    db = get_db()
    try:
        now = datetime.utcnow()
        q = (
            db.query(Ticket)
            .filter(Ticket.sla_at < now)
            .filter(Ticket.estado.notin_(["cerrado", "completado"]))
        )
        rows = q.all()
        tickets_sla_breaches.set(len(rows))
        return [{"id": t.id, "estado": t.estado, "slaAt": t.sla_at.isoformat()} for t in rows]
    finally:
        db.close()


@app.get("/tickets/cliente/{cliente_id}")
def tickets_cliente(cliente_id: int):
    db = get_db()
    try:
        rows = (
            db.query(Ticket)
            .filter(Ticket.cliente_id == cliente_id)
            .order_by(Ticket.creado_en.desc())
            .limit(50)
            .all()
        )
        return [_serialize_ticket(t) for t in rows]
    finally:
        db.close()


@app.get("/tickets")
def listar_tickets(zona: str | None = None, estado: str | None = None, prioridad: str | None = None):
    db = get_db()
    try:
        query = db.query(Ticket)
        if zona:
            query = query.filter(Ticket.zona == zona)
        if estado:
            query = query.filter(Ticket.estado == estado)
        if prioridad:
            query = query.filter(Ticket.prioridad == prioridad)
        rows = query.order_by(Ticket.creado_en.desc()).limit(100).all()
        return [_serialize_ticket(t) for t in rows]
    finally:
        db.close()


Instrumentator().instrument(app).expose(app)


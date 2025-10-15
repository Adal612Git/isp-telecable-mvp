from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, ForeignKey
from datetime import datetime
from .db import Base


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(50))
    prioridad: Mapped[str] = mapped_column(String(10), default="P3")
    estado: Mapped[str] = mapped_column(String(20), default="abierto")
    sla_at: Mapped[datetime] = mapped_column(DateTime)
    zona: Mapped[str] = mapped_column(String(20))
    cliente_id: Mapped[int] = mapped_column(Integer)
    asignado_a: Mapped[str] = mapped_column(String(50), default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    fecha_cierre: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TicketFeedback(Base):
    __tablename__ = "ticket_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    calificacion: Mapped[int] = mapped_column(Integer)
    comentario: Mapped[str] = mapped_column(String(500), default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


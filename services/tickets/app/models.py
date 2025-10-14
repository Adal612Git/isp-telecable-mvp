from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime
from datetime import datetime
from .db import Base


class Ticket(Base):
    __tablename__ = "tickets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(50))
    prioridad: Mapped[str] = mapped_column(String(10), default="P3")
    estado: Mapped[str] = mapped_column(String(20), default="Abierto")
    sla_at: Mapped[datetime] = mapped_column(DateTime)
    zona: Mapped[str] = mapped_column(String(20))
    cliente_id: Mapped[int] = mapped_column(Integer)
    asignado_a: Mapped[str] = mapped_column(String(50), default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


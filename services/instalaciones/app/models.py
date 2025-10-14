from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, JSON
from datetime import datetime
from .db import Base


class Instalacion(Base):
    __tablename__ = "instalaciones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(Integer)
    ventana: Mapped[str] = mapped_column(String(50))
    zona: Mapped[str] = mapped_column(String(20))
    estado: Mapped[str] = mapped_column(String(20), default="Programada")
    evidencias: Mapped[str] = mapped_column(String(1000), default="[]")
    notas: Mapped[str] = mapped_column(String(1000), default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IdempotencyKey(Base):
    __tablename__ = "idem_red_ops"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    resource: Mapped[str] = mapped_column(String(50))
    response: Mapped[str] = mapped_column(String(1000))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


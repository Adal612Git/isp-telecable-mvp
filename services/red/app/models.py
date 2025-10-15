from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime, Boolean
from datetime import datetime
from .db import Base


class IdempotencyKey(Base):
    __tablename__ = "idem_red"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    resource: Mapped[str] = mapped_column(String(50))
    response: Mapped[str] = mapped_column(String(1000))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RouterState(Base):
    __tablename__ = "router_state"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(Integer, index=True, unique=True)
    conectado: Mapped[bool] = mapped_column(Boolean, default=True)
    modo: Mapped[str] = mapped_column(String(20), default="emulated")
    latencia_ms: Mapped[int] = mapped_column(Integer, default=40)
    ip_fake: Mapped[str] = mapped_column(String(32), default="189.210.10.10")
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


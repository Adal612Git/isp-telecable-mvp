from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Float, DateTime, Boolean
from datetime import datetime
from .db import Base


class IdempotencyKey(Base):
    __tablename__ = "idem_pagos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    reference: Mapped[str] = mapped_column(String(100))
    response: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Pago(Base):
    __tablename__ = "pagos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referencia: Mapped[str] = mapped_column(String(100), unique=True)
    metodo: Mapped[str] = mapped_column(String(30))
    monto: Mapped[float] = mapped_column(Float)
    estatus: Mapped[str] = mapped_column(String(30), default="pendiente")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Transaccion(Base):
    __tablename__ = "transacciones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pago_ref: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(50))
    provider_tx: Mapped[str] = mapped_column(String(100))
    exitoso: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WebhookLog(Base):
    __tablename__ = "webhooks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(100), unique=True)
    payload: Mapped[str] = mapped_column(String(1000))
    recibido_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Conciliacion(Base):
    __tablename__ = "conciliaciones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referencia: Mapped[str] = mapped_column(String(100))
    conciliado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


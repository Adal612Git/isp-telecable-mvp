from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from .db import Base


class Cliente(Base):
    __tablename__ = "clientes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    rfc: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    telefono: Mapped[str] = mapped_column(String(20), nullable=False)
    estatus: Mapped[str] = mapped_column(String(30), default="activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    router_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    domicilio_id: Mapped[int] = mapped_column(ForeignKey("domicilios.id"))

    domicilio = relationship("Domicilio", back_populates="cliente", uselist=False)
    # contrato: derived via Contrato.cliente_id
    contacto = relationship("Contacto", back_populates="cliente", uselist=False)
    consentimiento = relationship("Consentimiento", back_populates="cliente", uselist=False)


class Domicilio(Base):
    __tablename__ = "domicilios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    calle: Mapped[str] = mapped_column(String(200))
    numero: Mapped[str] = mapped_column(String(50))
    colonia: Mapped[str] = mapped_column(String(200))
    cp: Mapped[str] = mapped_column(String(10))
    ciudad: Mapped[str] = mapped_column(String(100))
    estado: Mapped[str] = mapped_column(String(100))
    zona: Mapped[str] = mapped_column(String(100), index=True)

    cliente = relationship("Cliente", back_populates="domicilio")


class Contacto(Base):
    __tablename__ = "contactos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    nombre: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200))
    telefono: Mapped[str] = mapped_column(String(20))

    cliente = relationship("Cliente", back_populates="contacto")


class Consentimiento(Base):
    __tablename__ = "consentimientos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    marketing: Mapped[bool] = mapped_column(Boolean, default=False)
    terminos: Mapped[bool] = mapped_column(Boolean, default=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cliente = relationship("Cliente", back_populates="consentimiento")


class Contrato(Base):
    __tablename__ = "contratos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"))
    plan_id: Mapped[str] = mapped_column(String(50))
    estatus: Mapped[str] = mapped_column(String(30), default="activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cliente = relationship("Cliente")


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    resource: Mapped[str] = mapped_column(String(50))
    response: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint('key', name='uq_idem_key'),)

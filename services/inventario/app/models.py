from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime
from datetime import datetime
from .db import Base


class Stock(Base):
    __tablename__ = "inv_stock"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50))
    zona: Mapped[str] = mapped_column(String(20), default="GLOBAL")
    cantidad: Mapped[int] = mapped_column(Integer, default=0)


class Reserva(Base):
    __tablename__ = "inv_reservas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instalacion_id: Mapped[int] = mapped_column(Integer)
    zona: Mapped[str] = mapped_column(String(20))
    sku: Mapped[str] = mapped_column(String(50))
    cantidad: Mapped[int] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Movimiento(Base):
    __tablename__ = "inv_movimientos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20))  # reserva|salida|devolucion|ajuste
    referencia: Mapped[str] = mapped_column(String(100))
    zona: Mapped[str] = mapped_column(String(20))
    sku: Mapped[str] = mapped_column(String(50))
    cantidad: Mapped[int] = mapped_column(Integer)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


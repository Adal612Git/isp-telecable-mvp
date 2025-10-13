from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Float, Boolean, DateTime
from datetime import datetime
from .db import Base


class ZonaCobertura(Base):
    __tablename__ = "zonas_cobertura"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    factor_precio: Mapped[float] = mapped_column(Float, default=1.0)
    tecnologias: Mapped[str] = mapped_column(String(200), default="FTTH,HFC")


class Plan(Base):
    __tablename__ = "planes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True)
    tecnologia: Mapped[str] = mapped_column(String(50))
    velocidad: Mapped[int] = mapped_column(Integer)
    precio_base: Mapped[float] = mapped_column(Float)


class CompatibilidadTecnologica(Base):
    __tablename__ = "compatibilidad_tecnologica"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tecnologia: Mapped[str] = mapped_column(String(50))
    zona: Mapped[str] = mapped_column(String(100))


class Combo(Base):
    __tablename__ = "combos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str] = mapped_column(String(200))
    descuento_pct: Mapped[float] = mapped_column(Float, default=0.0)
    vigente_desde: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    vigente_hasta: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


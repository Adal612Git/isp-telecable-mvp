from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Float, DateTime
from datetime import datetime
from .db import Base


class Factura(Base):
    __tablename__ = "facturas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str] = mapped_column(String(64), unique=True)
    cliente_id: Mapped[int] = mapped_column(Integer)
    total: Mapped[float] = mapped_column(Float)
    xml_path: Mapped[str] = mapped_column(String(255))
    estatus: Mapped[str] = mapped_column(String(20), default="pendiente")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime
from datetime import datetime
from .db import Base


class IdempotencyKey(Base):
    __tablename__ = "idem_red"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    resource: Mapped[str] = mapped_column(String(50))
    response: Mapped[str] = mapped_column(String(1000))
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


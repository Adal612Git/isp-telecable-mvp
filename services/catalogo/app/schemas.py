from pydantic import BaseModel
from datetime import datetime


class PlanOut(BaseModel):
    codigo: str
    tecnologia: str
    velocidad: int
    precio: float


class ComboOut(BaseModel):
    nombre: str
    descripcion: str
    descuento_pct: float
    vigente_desde: datetime
    vigente_hasta: datetime


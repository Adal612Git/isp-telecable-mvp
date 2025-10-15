from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class DomicilioIn(BaseModel):
    calle: str
    numero: str
    colonia: str
    cp: str
    ciudad: str
    estado: str
    zona: str


class ContactoIn(BaseModel):
    nombre: str
    email: EmailStr
    telefono: str


class ConsentimientoIn(BaseModel):
    marketing: bool = False
    terminos: bool = True


class ClienteCreate(BaseModel):
    nombre: str = Field(min_length=2)
    rfc: str
    email: EmailStr
    telefono: str
    plan_id: str
    domicilio: DomicilioIn
    contacto: ContactoIn
    consentimiento: ConsentimientoIn


class ClienteOut(BaseModel):
    id: int
    nombre: str
    rfc: str
    email: EmailStr
    telefono: str
    estatus: str
    zona: str
    plan_id: Optional[str]
    router_id: Optional[str] = None

    class Config:
        from_attributes = True


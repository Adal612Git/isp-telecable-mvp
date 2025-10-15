from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session
import os
import httpx

from ..db import SessionLocal
from .. import models
from ..schemas import ClienteCreate, ClienteOut
from ..utils.validators import validate_rfc, validate_phone
from ..utils.idempotency import get_or_store_idempotent
from ..events import event_bus
import os


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/clientes", response_model=ClienteOut)
async def crear_cliente(
    payload: ClienteCreate,
    response: Response,
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not validate_rfc(payload.rfc):
        raise HTTPException(status_code=400, detail="RFC inválido")
    if not validate_phone(payload.telefono):
        raise HTTPException(status_code=400, detail="Teléfono inválido")

    # Validate zone existence via catalogo service
    catalogo_url = os.getenv("CATALOGO_URL", "http://catalogo:8001")
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"{catalogo_url}/zonas")
        r.raise_for_status()
        zonas = {z["id"] for z in r.json()}
    if payload.domicilio.zona not in zonas:
        raise HTTPException(status_code=400, detail="Zona de cobertura inexistente")

    # Idempotency
    if idempotency_key:
        found, resp = get_or_store_idempotent(db, idempotency_key, resource="cliente")
        if found and resp:
            # Return previously stored response and mark replay header
            if response is not None:
                response.headers["X-Idempotent-Replay"] = "true"
            from pydantic import TypeAdapter
            ta = TypeAdapter(ClienteOut)
            return ta.validate_json(resp)

    dom = models.Domicilio(
        calle=payload.domicilio.calle,
        numero=payload.domicilio.numero,
        colonia=payload.domicilio.colonia,
        cp=payload.domicilio.cp,
        ciudad=payload.domicilio.ciudad,
        estado=payload.domicilio.estado,
        zona=payload.domicilio.zona,
    )
    db.add(dom)
    db.flush()

    cli = models.Cliente(
        nombre=payload.nombre,
        rfc=payload.rfc.upper(),
        email=payload.email,
        telefono=payload.telefono,
        domicilio_id=dom.id,
    )
    from sqlalchemy.exc import IntegrityError
    db.add(cli)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        # Duplicate RFC: return existing record (idempotent on RFC)
        existing = db.query(models.Cliente).filter(models.Cliente.rfc == payload.rfc.upper()).first()
        if existing:
            dom = db.query(models.Domicilio).filter(models.Domicilio.id == existing.domicilio_id).first()
            con = db.query(models.Contrato).filter(models.Contrato.cliente_id == existing.id, models.Contrato.estatus == "activo").first()
            if response is not None:
                response.headers["X-Idempotent-Replay"] = "true"
            return ClienteOut(
                id=existing.id,
                nombre=existing.nombre,
                rfc=existing.rfc,
                email=existing.email,
                telefono=existing.telefono,
                estatus=existing.estatus,
                zona=dom.zona if dom else "",
                plan_id=con.plan_id if con else None,
            )
        else:
            raise

    contacto = models.Contacto(
        cliente_id=cli.id,
        nombre=payload.contacto.nombre,
        email=payload.contacto.email,
        telefono=payload.contacto.telefono,
    )
    db.add(contacto)

    cons = models.Consentimiento(
        cliente_id=cli.id,
        marketing=payload.consentimiento.marketing,
        terminos=payload.consentimiento.terminos,
    )
    db.add(cons)

    contrato = models.Contrato(
        cliente_id=cli.id,
        plan_id=payload.plan_id,
        estatus="activo",
    )
    db.add(contrato)
    db.flush()
    db.commit()

    out = ClienteOut(
        id=cli.id,
        nombre=cli.nombre,
        rfc=cli.rfc,
        email=cli.email,
        telefono=cli.telefono,
        estatus=cli.estatus,
        zona=dom.zona,
        plan_id=contrato.plan_id,
    )

    # store idempotent response
    if idempotency_key:
        from json import dumps
        get_or_store_idempotent(db, idempotency_key, resource="cliente", response=out.model_dump_json())

    await event_bus.publish(
        "ClienteCreado",
        {"cliente_id": cli.id, "rfc": cli.rfc, "plan_id": contrato.plan_id, "zona": dom.zona},
    )
    await event_bus.publish(
        "ConsentimientoActualizado",
        {"cliente_id": cli.id, "marketing": cons.marketing, "terminos": cons.terminos},
    )
    # Comportamiento según ROUTER_MODE (emulado vs real)
    mode = os.getenv("ROUTER_MODE", "emulated")
    if mode == "real":
        # Aquí se invocaría un router real; en dev solo registramos
        pass
    return out


@router.get("/clientes/{id}", response_model=ClienteOut)
def obtener_cliente(id: int, db: Session = Depends(get_db)):
    cli = db.query(models.Cliente).filter(models.Cliente.id == id).first()
    if not cli:
        raise HTTPException(status_code=404, detail="No encontrado")
    dom = db.query(models.Domicilio).filter(models.Domicilio.id == cli.domicilio_id).first()
    plan_id = None
    con = db.query(models.Contrato).filter(models.Contrato.cliente_id == cli.id, models.Contrato.estatus == "activo").first()
    plan_id = con.plan_id if con else None
    return ClienteOut(
        id=cli.id,
        nombre=cli.nombre,
        rfc=cli.rfc,
        email=cli.email,
        telefono=cli.telefono,
        estatus=cli.estatus,
        zona=dom.zona if dom else "",
        plan_id=plan_id,
    )


@router.get("/clientes/{id}/estado")
def obtener_estado_cliente(id: int, db: Session = Depends(get_db)):
    cli = db.query(models.Cliente).filter(models.Cliente.id == id).first()
    if not cli:
        raise HTTPException(status_code=404, detail="No encontrado")
    contrato = (
        db.query(models.Contrato)
        .filter(models.Contrato.cliente_id == cli.id, models.Contrato.estatus == "activo")
        .first()
    )
    if cli.estatus == "inactivo":
        estado = "suspendido"
    elif contrato:
        estado = "instalado"
    else:
        estado = "pendiente"
    return {
        "cliente_id": cli.id,
        "estado": estado,
        "plan_id": contrato.plan_id if contrato else None,
    }


@router.put("/clientes/{id}", response_model=ClienteOut)
async def actualizar_cliente(id: int, payload: ClienteCreate, db: Session = Depends(get_db)):
    cli = db.query(models.Cliente).filter(models.Cliente.id == id).first()
    if not cli:
        raise HTTPException(status_code=404, detail="No encontrado")
    if not validate_rfc(payload.rfc):
        raise HTTPException(status_code=400, detail="RFC inválido")
    if not validate_phone(payload.telefono):
        raise HTTPException(status_code=400, detail="Teléfono inválido")

    dom = db.query(models.Domicilio).filter(models.Domicilio.id == cli.domicilio_id).first()
    if dom:
        dom.calle = payload.domicilio.calle
        dom.numero = payload.domicilio.numero
        dom.colonia = payload.domicilio.colonia
        dom.cp = payload.domicilio.cp
        dom.ciudad = payload.domicilio.ciudad
        dom.estado = payload.domicilio.estado
        dom.zona = payload.domicilio.zona
    cli.nombre = payload.nombre
    cli.rfc = payload.rfc.upper()
    cli.email = payload.email
    cli.telefono = payload.telefono
    con = db.query(models.Contrato).filter(models.Contrato.cliente_id == cli.id, models.Contrato.estatus == "activo").first()
    if con:
        con.plan_id = payload.plan_id
        await event_bus.publish("ContratoModificado", {"cliente_id": cli.id, "plan_id": con.plan_id})
    db.commit()
    return obtener_cliente(id, db)


@router.get("/clientes")
def listar_clientes(zona: str | None = None, estatus: str | None = None, db: Session = Depends(get_db)):
    q = db.query(models.Cliente)
    if estatus:
        q = q.filter(models.Cliente.estatus == estatus)
    clientes = q.all()
    out = []
    for c in clientes:
        dom = db.query(models.Domicilio).filter(models.Domicilio.id == c.domicilio_id).first()
        if zona and dom and dom.zona != zona:
            continue
        con = db.query(models.Contrato).filter(models.Contrato.cliente_id == c.id, models.Contrato.estatus == "activo").first()
        out.append(
            {
                "id": c.id,
                "nombre": c.nombre,
                "rfc": c.rfc,
                "email": c.email,
                "telefono": c.telefono,
                "estatus": c.estatus,
                "zona": dom.zona if dom else None,
                "plan_id": con.plan_id if con else None,
            }
        )
    return out


@router.post("/clientes/{id}/inactivar")
def inactivar_cliente(id: int, db: Session = Depends(get_db)):
    cli = db.query(models.Cliente).filter(models.Cliente.id == id).first()
    if not cli:
        raise HTTPException(status_code=404, detail="No encontrado")
    cli.estatus = "inactivo"
    db.commit()
    return {"id": cli.id, "estatus": cli.estatus}


@router.get("/admin/stats")
def admin_stats(x_role: str | None = Header(default=None, alias="X-Role"), db: Session = Depends(get_db)):
    if x_role != "admin":
        raise HTTPException(status_code=403, detail="forbidden")
    total = db.query(models.Cliente).count()
    activos = db.query(models.Cliente).filter(models.Cliente.estatus == "activo").count()
    inactivos = db.query(models.Cliente).filter(models.Cliente.estatus == "inactivo").count()
    return {"total": total, "activos": activos, "inactivos": inactivos}

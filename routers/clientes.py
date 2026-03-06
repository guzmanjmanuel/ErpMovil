from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.contribuyente import DirectorioCliente, ClienteContacto
from schemas.contribuyente import ClienteCreate, ClienteUpdate, ClienteOut, ContactoCreate, ContactoUpdate, ContactoOut
from auth.deps import get_tenant_user

router = APIRouter(prefix="/tenants/{tenant_id}/clientes", tags=["Clientes"])


@router.get("", response_model=List[ClienteOut])
def listar_clientes(
    tenant_id: int,
    buscar: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(DirectorioCliente).filter(
        DirectorioCliente.tenant_id == tenant_id,
        DirectorioCliente.activo == True,
    )
    if buscar:
        like = f"%{buscar}%"
        q = q.filter(
            (DirectorioCliente.nombre.ilike(like)) |
            (DirectorioCliente.nombre_comercial.ilike(like)) |
            (DirectorioCliente.nit.ilike(like)) |
            (DirectorioCliente.dui.ilike(like)) |
            (DirectorioCliente.num_documento.ilike(like)) |
            (DirectorioCliente.correo_factura.ilike(like))
        )
    return q.order_by(DirectorioCliente.nombre).all()


@router.get("/{cliente_id}", response_model=ClienteOut)
def obtener_cliente(
    tenant_id: int,
    cliente_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    c = db.query(DirectorioCliente).filter(
        DirectorioCliente.id == cliente_id,
        DirectorioCliente.tenant_id == tenant_id,
    ).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    return c


@router.post("", response_model=ClienteOut, status_code=201)
def crear_cliente(
    tenant_id: int,
    data: ClienteCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    cliente = DirectorioCliente(tenant_id=tenant_id, **data.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.patch("/{cliente_id}", response_model=ClienteOut)
def actualizar_cliente(
    tenant_id: int,
    cliente_id: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    c = db.query(DirectorioCliente).filter(
        DirectorioCliente.id == cliente_id,
        DirectorioCliente.tenant_id == tenant_id,
    ).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(c, field, val)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{cliente_id}", status_code=204)
def eliminar_cliente(
    tenant_id: int,
    cliente_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    c = db.query(DirectorioCliente).filter(
        DirectorioCliente.id == cliente_id,
        DirectorioCliente.tenant_id == tenant_id,
    ).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    c.activo = False
    db.commit()


# ── Contactos ─────────────────────────────────────────────────────────────────

def _get_cliente(db: Session, tenant_id: int, cliente_id: int) -> DirectorioCliente:
    c = db.query(DirectorioCliente).filter(
        DirectorioCliente.id == cliente_id,
        DirectorioCliente.tenant_id == tenant_id,
    ).first()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    return c


@router.get("/{cliente_id}/contactos", response_model=List[ContactoOut])
def listar_contactos(
    tenant_id: int,
    cliente_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    _get_cliente(db, tenant_id, cliente_id)
    return (
        db.query(ClienteContacto)
        .filter(ClienteContacto.cliente_id == cliente_id, ClienteContacto.activo == True)
        .order_by(ClienteContacto.principal.desc(), ClienteContacto.nombre)
        .all()
    )


@router.post("/{cliente_id}/contactos", response_model=ContactoOut, status_code=201)
def agregar_contacto(
    tenant_id: int,
    cliente_id: int,
    data: ContactoCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    _get_cliente(db, tenant_id, cliente_id)
    # Si el nuevo contacto es principal, desmarcar los demás
    if data.principal:
        db.query(ClienteContacto).filter(
            ClienteContacto.cliente_id == cliente_id,
        ).update({"principal": False})
    contacto = ClienteContacto(
        cliente_id=cliente_id,
        tenant_id=tenant_id,
        **data.model_dump(),
    )
    db.add(contacto)
    db.commit()
    db.refresh(contacto)
    return contacto


@router.patch("/{cliente_id}/contactos/{contacto_id}", response_model=ContactoOut)
def actualizar_contacto(
    tenant_id: int,
    cliente_id: int,
    contacto_id: int,
    data: ContactoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    _get_cliente(db, tenant_id, cliente_id)
    ct = db.query(ClienteContacto).filter(
        ClienteContacto.id == contacto_id,
        ClienteContacto.cliente_id == cliente_id,
    ).first()
    if not ct:
        raise HTTPException(404, "Contacto no encontrado")
    if data.principal:
        db.query(ClienteContacto).filter(
            ClienteContacto.cliente_id == cliente_id,
            ClienteContacto.id != contacto_id,
        ).update({"principal": False})
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(ct, field, val)
    db.commit()
    db.refresh(ct)
    return ct


@router.delete("/{cliente_id}/contactos/{contacto_id}", status_code=204)
def eliminar_contacto(
    tenant_id: int,
    cliente_id: int,
    contacto_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    _get_cliente(db, tenant_id, cliente_id)
    ct = db.query(ClienteContacto).filter(
        ClienteContacto.id == contacto_id,
        ClienteContacto.cliente_id == cliente_id,
    ).first()
    if not ct:
        raise HTTPException(404, "Contacto no encontrado")
    ct.activo = False
    db.commit()

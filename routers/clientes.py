from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.contribuyente import DirectorioCliente
from schemas.contribuyente import ClienteCreate, ClienteUpdate, ClienteOut
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
            (DirectorioCliente.nit.ilike(like)) |
            (DirectorioCliente.dui.ilike(like)) |
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

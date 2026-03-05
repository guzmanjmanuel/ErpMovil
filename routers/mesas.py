from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.mesa import Mesa, Area
from schemas.mesa import MesaOut, MesaCreate, MesaEstadoUpdate, AreaOut
from auth.deps import get_tenant_user

router = APIRouter(prefix="/tenants/{tenant_id}/mesas", tags=["Mesas"])


@router.get("/areas", response_model=List[AreaOut])
def listar_areas(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    return db.query(Area).filter(Area.tenant_id == tenant_id, Area.activo == True).all()


@router.get("", response_model=List[MesaOut])
def listar_mesas(
    tenant_id: int,
    area_id: int | None = None,
    estado: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(Mesa).filter(Mesa.tenant_id == tenant_id)
    if area_id:
        q = q.filter(Mesa.area_id == area_id)
    if estado:
        q = q.filter(Mesa.estado == estado)
    return q.order_by(Mesa.numero).all()


@router.get("/{mesa_id}", response_model=MesaOut)
def obtener_mesa(
    tenant_id: int,
    mesa_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id, Mesa.tenant_id == tenant_id).first()
    if not mesa:
        raise HTTPException(404, "Mesa no encontrada")
    return mesa


@router.post("", response_model=MesaOut, status_code=201)
def crear_mesa(
    tenant_id: int,
    data: MesaCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    mesa = Mesa(tenant_id=tenant_id, **data.model_dump())
    db.add(mesa)
    db.commit()
    db.refresh(mesa)
    return mesa


@router.patch("/{mesa_id}/estado", response_model=MesaOut)
def actualizar_estado_mesa(
    tenant_id: int,
    mesa_id: int,
    data: MesaEstadoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    mesa = db.query(Mesa).filter(Mesa.id == mesa_id, Mesa.tenant_id == tenant_id).first()
    if not mesa:
        raise HTTPException(404, "Mesa no encontrada")
    estados_validos = {"disponible", "ocupada", "reservada"}
    if data.estado not in estados_validos:
        raise HTTPException(400, f"Estado inválido. Use: {', '.join(estados_validos)}")
    mesa.estado = data.estado
    db.commit()
    db.refresh(mesa)
    return mesa

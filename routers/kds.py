from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.comanda import Comanda, ComandaItem, AreaCocina
from schemas.comanda import ComandaOut, ComandaItemOut, ComandaEstadoUpdate, ComandaItemEstadoUpdate
from auth.deps import get_tenant_user

router = APIRouter(prefix="/tenants/{tenant_id}/kds", tags=["KDS - Cocina"])


@router.get("/areas", response_model=List[dict])
def listar_areas_cocina(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    areas = db.query(AreaCocina).filter(
        AreaCocina.tenant_id == tenant_id,
        AreaCocina.activo == True,
    ).all()
    return [{"id": a.id, "nombre": a.nombre} for a in areas]


@router.get("/comandas", response_model=List[ComandaOut])
def listar_comandas(
    tenant_id: int,
    estado: str | None = None,
    area_cocina_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(Comanda).filter(Comanda.tenant_id == tenant_id)
    if estado:
        q = q.filter(Comanda.estado == estado)
    if area_cocina_id:
        q = q.filter(Comanda.area_cocina_id == area_cocina_id)
    return q.order_by(Comanda.created_at).all()


@router.get("/comandas/{comanda_id}", response_model=ComandaOut)
def obtener_comanda(
    tenant_id: int,
    comanda_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    comanda = db.query(Comanda).filter(
        Comanda.id == comanda_id, Comanda.tenant_id == tenant_id
    ).first()
    if not comanda:
        raise HTTPException(404, "Comanda no encontrada")
    return comanda


@router.patch("/comandas/{comanda_id}/estado", response_model=ComandaOut)
def actualizar_estado_comanda(
    tenant_id: int,
    comanda_id: int,
    data: ComandaEstadoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    estados_validos = {"pendiente", "en_preparacion", "listo", "entregado"}
    if data.estado not in estados_validos:
        raise HTTPException(400, f"Estado inválido. Use: {', '.join(estados_validos)}")
    comanda = db.query(Comanda).filter(
        Comanda.id == comanda_id, Comanda.tenant_id == tenant_id
    ).first()
    if not comanda:
        raise HTTPException(404, "Comanda no encontrada")
    comanda.estado = data.estado
    db.commit()
    db.refresh(comanda)
    return comanda


@router.get("/comandas/{comanda_id}/items", response_model=List[ComandaItemOut])
def listar_items_comanda(
    tenant_id: int,
    comanda_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    return db.query(ComandaItem).filter(
        ComandaItem.comanda_id == comanda_id,
        ComandaItem.tenant_id == tenant_id,
    ).all()


@router.patch("/comandas/{comanda_id}/items/{item_id}/estado", response_model=ComandaItemOut)
def actualizar_estado_item(
    tenant_id: int,
    comanda_id: int,
    item_id: int,
    data: ComandaItemEstadoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    estados_validos = {"pendiente", "en_preparacion", "listo"}
    if data.estado not in estados_validos:
        raise HTTPException(400, f"Estado inválido. Use: {', '.join(estados_validos)}")
    item = db.query(ComandaItem).filter(
        ComandaItem.id == item_id,
        ComandaItem.comanda_id == comanda_id,
        ComandaItem.tenant_id == tenant_id,
    ).first()
    if not item:
        raise HTTPException(404, "Item no encontrado")
    item.estado = data.estado
    db.commit()
    db.refresh(item)
    return item

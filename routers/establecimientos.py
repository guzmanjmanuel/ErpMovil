from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel

from database import get_db
from models.establecimiento import Establecimiento, CatTipoEstablecimiento
from models.contribuyente import Contribuyente
from auth.deps import get_tenant_user

router = APIRouter(prefix="/tenants/{tenant_id}/establecimientos", tags=["Establecimientos"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class TipoEstablecimientoOut(BaseModel):
    codigo: str
    descripcion: str
    model_config = {"from_attributes": True}


class EstablecimientoCreate(BaseModel):
    nombre: str
    tipo: str                               # CAT-009: 01/02/04/07/20
    cod_estable_mh: Optional[str] = None
    cod_estable: Optional[str] = None
    cod_punto_venta_mh: Optional[str] = None
    cod_punto_venta: Optional[str] = None
    telefono: Optional[str] = None
    es_principal: bool = False


class EstablecimientoUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    cod_estable_mh: Optional[str] = None
    cod_estable: Optional[str] = None
    cod_punto_venta_mh: Optional[str] = None
    cod_punto_venta: Optional[str] = None
    telefono: Optional[str] = None
    es_principal: Optional[bool] = None
    activo: Optional[bool] = None


class EstablecimientoOut(BaseModel):
    id: int
    tenant_id: int
    contribuyente_id: int
    nombre: str
    tipo: str
    tipo_descripcion: Optional[str] = None
    cod_estable_mh: Optional[str] = None
    cod_estable: Optional[str] = None
    cod_punto_venta_mh: Optional[str] = None
    cod_punto_venta: Optional[str] = None
    telefono: Optional[str] = None
    es_principal: bool
    activo: bool
    model_config = {"from_attributes": True}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _to_out(e: Establecimiento, db: Session) -> EstablecimientoOut:
    cat = db.query(CatTipoEstablecimiento).filter(
        CatTipoEstablecimiento.codigo == e.tipo
    ).first()
    out = EstablecimientoOut.model_validate(e)
    out.tipo_descripcion = cat.descripcion if cat else None
    return out


def _get_emisor_id(tenant_id: int, db: Session) -> int:
    c = db.query(Contribuyente).filter(
        Contribuyente.tenant_id == tenant_id,
        Contribuyente.tipo == "emisor",
        Contribuyente.activo == True,
    ).first()
    if not c:
        raise HTTPException(400, "El tenant no tiene emisor configurado. Configure primero los datos fiscales.")
    return c.id


def _validate_tipo(tipo: str, db: Session):
    cat = db.query(CatTipoEstablecimiento).filter(
        CatTipoEstablecimiento.codigo == tipo
    ).first()
    if not cat:
        raise HTTPException(400, f"Tipo '{tipo}' inválido. Usar: 01=Sucursal, 02=Casa Matriz, 04=Bodega, 07=Patio, 20=Virtual")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/tipos", response_model=List[TipoEstablecimientoOut])
def listar_tipos(db: Session = Depends(get_db), _=Depends(get_tenant_user)):
    return db.query(CatTipoEstablecimiento).order_by(CatTipoEstablecimiento.codigo).all()


@router.get("", response_model=List[EstablecimientoOut])
def listar_establecimientos(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    items = db.query(Establecimiento).filter(
        Establecimiento.tenant_id == tenant_id,
        Establecimiento.activo == True,
    ).order_by(Establecimiento.es_principal.desc(), Establecimiento.id).all()
    return [_to_out(e, db) for e in items]


@router.post("", response_model=EstablecimientoOut, status_code=201)
def crear_establecimiento(
    tenant_id: int,
    data: EstablecimientoCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    _validate_tipo(data.tipo, db)
    contribuyente_id = _get_emisor_id(tenant_id, db)

    # Si es_principal, quitar el principal actual
    if data.es_principal:
        db.query(Establecimiento).filter(
            Establecimiento.tenant_id == tenant_id,
            Establecimiento.es_principal == True,
        ).update({"es_principal": False})

    e = Establecimiento(
        tenant_id=tenant_id,
        contribuyente_id=contribuyente_id,
        nombre=data.nombre,
        tipo=data.tipo,
        cod_estable_mh=data.cod_estable_mh,
        cod_estable=data.cod_estable,
        cod_punto_venta_mh=data.cod_punto_venta_mh,
        cod_punto_venta=data.cod_punto_venta,
        telefono=data.telefono,
        es_principal=data.es_principal,
        activo=True,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _to_out(e, db)


@router.patch("/{estab_id}", response_model=EstablecimientoOut)
def actualizar_establecimiento(
    tenant_id: int,
    estab_id: int,
    data: EstablecimientoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    e = db.query(Establecimiento).filter(
        Establecimiento.id == estab_id,
        Establecimiento.tenant_id == tenant_id,
    ).first()
    if not e:
        raise HTTPException(404, "Establecimiento no encontrado")

    if data.tipo is not None:
        _validate_tipo(data.tipo, db)
        e.tipo = data.tipo

    if data.es_principal is True and not e.es_principal:
        db.query(Establecimiento).filter(
            Establecimiento.tenant_id == tenant_id,
            Establecimiento.es_principal == True,
        ).update({"es_principal": False})
        e.es_principal = True
    elif data.es_principal is False:
        e.es_principal = False

    for field in ("nombre", "cod_estable_mh", "cod_estable",
                  "cod_punto_venta_mh", "cod_punto_venta", "telefono", "activo"):
        val = getattr(data, field)
        if val is not None:
            setattr(e, field, val)

    db.commit()
    db.refresh(e)
    return _to_out(e, db)


@router.delete("/{estab_id}", status_code=204)
def eliminar_establecimiento(
    tenant_id: int,
    estab_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    e = db.query(Establecimiento).filter(
        Establecimiento.id == estab_id,
        Establecimiento.tenant_id == tenant_id,
    ).first()
    if not e:
        raise HTTPException(404, "Establecimiento no encontrado")
    if e.es_principal:
        raise HTTPException(400, "No puedes eliminar el establecimiento principal")
    e.activo = False
    db.commit()

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from database import get_db
from models.catalogo import CatActividadEconomica, CatTipoItem, CatUnidadMedida, Departamento, Municipio
from cache.manager import global_cache, CacheKeys, invalidar_catalogo

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])


class ActividadOut(BaseModel):
    codigo: str
    descripcion: str
    model_config = {"from_attributes": True}


class DepartamentoOut(BaseModel):
    codigo: str
    nombre: str
    model_config = {"from_attributes": True}


class MunicipioOut(BaseModel):
    codigo: str
    departamento_id: str
    nombre: str
    model_config = {"from_attributes": True}


class TipoItemOut(BaseModel):
    codigo: int
    descripcion: str
    model_config = {"from_attributes": True}


class UnidadMedidaOut(BaseModel):
    codigo: int
    descripcion: str
    model_config = {"from_attributes": True}


@router.get("/actividades", response_model=List[ActividadOut])
def listar_actividades(db: Session = Depends(get_db)):
    cached = global_cache.get(CacheKeys.ACTIVIDADES)
    if cached is not None:
        return cached
    rows = db.query(CatActividadEconomica).order_by(CatActividadEconomica.codigo).all()
    result = [ActividadOut.model_validate(r) for r in rows]
    global_cache.set(CacheKeys.ACTIVIDADES, result)
    return result


@router.get("/departamentos", response_model=List[DepartamentoOut])
def listar_departamentos(db: Session = Depends(get_db)):
    cached = global_cache.get(CacheKeys.DEPARTAMENTOS)
    if cached is not None:
        return cached
    rows = db.query(Departamento).order_by(Departamento.codigo).all()
    result = [DepartamentoOut.model_validate(r) for r in rows]
    global_cache.set(CacheKeys.DEPARTAMENTOS, result)
    return result


@router.get("/municipios", response_model=List[MunicipioOut])
def listar_municipios(
    departamento: str | None = None,
    db: Session = Depends(get_db),
):
    cache_key = CacheKeys.municipios_depto(departamento) if departamento else CacheKeys.MUNICIPIOS
    cached = global_cache.get(cache_key)
    if cached is not None:
        return cached
    q = db.query(Municipio)
    if departamento:
        q = q.filter(Municipio.departamento_id == departamento)
    rows = q.order_by(Municipio.nombre).all()
    result = [MunicipioOut.model_validate(r) for r in rows]
    global_cache.set(cache_key, result)
    return result


@router.get("/tipos-item", response_model=List[TipoItemOut])
def listar_tipos_item(db: Session = Depends(get_db)):
    cached = global_cache.get(CacheKeys.TIPO_ITEM)
    if cached is not None:
        return cached
    rows = db.query(CatTipoItem).order_by(CatTipoItem.codigo).all()
    result = [TipoItemOut.model_validate(r) for r in rows]
    global_cache.set(CacheKeys.TIPO_ITEM, result)
    return result


@router.get("/unidades-medida", response_model=List[UnidadMedidaOut])
def listar_unidades_medida(db: Session = Depends(get_db)):
    cached = global_cache.get(CacheKeys.UNIDADES_MEDIDA)
    if cached is not None:
        return cached
    rows = db.query(CatUnidadMedida).order_by(CatUnidadMedida.codigo).all()
    result = [UnidadMedidaOut.model_validate(r) for r in rows]
    global_cache.set(CacheKeys.UNIDADES_MEDIDA, result)
    return result


# ── Endpoint admin: forzar invalidación de catálogos ─────────────────────────
@router.post("/cache/invalidar", tags=["Admin"], status_code=204)
def invalidar_cache_catalogos():
    """Fuerza recarga de todos los catálogos estáticos. Útil tras importar datos."""
    for key in [
        CacheKeys.TIPO_ITEM, CacheKeys.UNIDADES_MEDIDA,
        CacheKeys.DEPARTAMENTOS, CacheKeys.MUNICIPIOS, CacheKeys.ACTIVIDADES,
    ]:
        invalidar_catalogo(key)

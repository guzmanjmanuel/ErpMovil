from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from database import get_db
from models.catalogo import CatActividadEconomica

router = APIRouter(prefix="/catalogos", tags=["Catálogos"])


class ActividadOut(BaseModel):
    codigo: str
    descripcion: str
    model_config = {"from_attributes": True}


@router.get("/actividades", response_model=List[ActividadOut])
def listar_actividades(db: Session = Depends(get_db)):
    return db.query(CatActividadEconomica).order_by(CatActividadEconomica.codigo).all()

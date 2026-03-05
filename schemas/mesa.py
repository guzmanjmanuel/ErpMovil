from pydantic import BaseModel
from typing import Optional


class AreaOut(BaseModel):
    id: int
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}


class MesaOut(BaseModel):
    id: int
    area_id: Optional[int] = None
    numero: str
    capacidad: int
    estado: str
    qr_code: Optional[str] = None

    model_config = {"from_attributes": True}


class MesaCreate(BaseModel):
    area_id: Optional[int] = None
    numero: str
    capacidad: int = 4


class MesaEstadoUpdate(BaseModel):
    estado: str  # disponible / ocupada / reservada

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ComandaItemOut(BaseModel):
    id: int
    pedido_item_id: int
    estado: str

    model_config = {"from_attributes": True}


class ComandaOut(BaseModel):
    id: int
    pedido_id: int
    area_cocina_id: Optional[int] = None
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ComandaEstadoUpdate(BaseModel):
    estado: str     # pendiente / en_preparacion / listo / entregado


class ComandaItemEstadoUpdate(BaseModel):
    estado: str     # pendiente / en_preparacion / listo

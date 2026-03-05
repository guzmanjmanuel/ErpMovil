from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class ClienteCreate(BaseModel):
    nombre: str
    nombre_comercial: Optional[str] = None
    nit: Optional[str] = None
    nrc: Optional[str] = None
    dui: Optional[str] = None
    correo_factura: Optional[str] = None
    telefono: Optional[str] = None
    tipo_contribuyente: Optional[str] = None   # natural / juridico


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    nombre_comercial: Optional[str] = None
    nit: Optional[str] = None
    nrc: Optional[str] = None
    dui: Optional[str] = None
    correo_factura: Optional[str] = None
    telefono: Optional[str] = None
    tipo_contribuyente: Optional[str] = None
    activo: Optional[bool] = None


class ClienteOut(BaseModel):
    id: int
    nombre: str
    nombre_comercial: Optional[str] = None
    nit: Optional[str] = None
    nrc: Optional[str] = None
    dui: Optional[str] = None
    correo_factura: Optional[str] = None
    telefono: Optional[str] = None
    tipo_contribuyente: Optional[str] = None
    activo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EmisorOut(BaseModel):
    id: int
    nit: Optional[str] = None
    nrc: Optional[str] = None
    nombre: str
    nombre_comercial: Optional[str] = None
    cod_actividad: Optional[str] = None
    desc_actividad: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None

    model_config = {"from_attributes": True}

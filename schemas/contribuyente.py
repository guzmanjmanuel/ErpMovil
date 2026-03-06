from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class ClienteCreate(BaseModel):
    nombre: str
    nombre_comercial: Optional[str] = None
    tipo_contribuyente: Optional[str] = None    # natural / juridico
    tipo_documento_id: Optional[str] = None     # 36=NIT, 13=DUI, 03=Pasaporte, 02=Carné, 37=Otro
    num_documento: Optional[str] = None
    nit: Optional[str] = None
    nrc: Optional[str] = None
    dui: Optional[str] = None
    cod_actividad: Optional[str] = None
    desc_actividad: Optional[str] = None
    correo_factura: Optional[str] = None
    telefono: Optional[str] = None
    cod_pais: Optional[str] = "9200"
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    complemento_direccion: Optional[str] = None
    lista_precio_id: Optional[int] = None            # lista de precio asignada al cliente


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    nombre_comercial: Optional[str] = None
    tipo_contribuyente: Optional[str] = None
    tipo_documento_id: Optional[str] = None
    num_documento: Optional[str] = None
    nit: Optional[str] = None
    nrc: Optional[str] = None
    dui: Optional[str] = None
    cod_actividad: Optional[str] = None
    desc_actividad: Optional[str] = None
    correo_factura: Optional[str] = None
    telefono: Optional[str] = None
    cod_pais: Optional[str] = None
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    complemento_direccion: Optional[str] = None
    lista_precio_id: Optional[int] = None
    activo: Optional[bool] = None


class ContactoCreate(BaseModel):
    nombre: str
    correo: Optional[str] = None
    telefono: Optional[str] = None
    cargo: Optional[str] = None
    principal: bool = False


class ContactoUpdate(BaseModel):
    nombre: Optional[str] = None
    correo: Optional[str] = None
    telefono: Optional[str] = None
    cargo: Optional[str] = None
    principal: Optional[bool] = None


class ContactoOut(BaseModel):
    id: int
    nombre: str
    correo: Optional[str] = None
    telefono: Optional[str] = None
    cargo: Optional[str] = None
    principal: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ClienteOut(BaseModel):
    id: int
    nombre: str
    nombre_comercial: Optional[str] = None
    tipo_contribuyente: Optional[str] = None
    tipo_documento_id: Optional[str] = None
    num_documento: Optional[str] = None
    nit: Optional[str] = None
    nrc: Optional[str] = None
    dui: Optional[str] = None
    cod_actividad: Optional[str] = None
    desc_actividad: Optional[str] = None
    correo_factura: Optional[str] = None
    telefono: Optional[str] = None
    cod_pais: Optional[str] = None
    departamento: Optional[str] = None
    municipio: Optional[str] = None
    complemento_direccion: Optional[str] = None
    lista_precio_id: Optional[int] = None
    activo: bool
    created_at: datetime
    contactos: List[ContactoOut] = []

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

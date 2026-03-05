from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


class UsuarioCreate(BaseModel):
    email: EmailStr
    password: str
    nombre: str
    rol: str = "operador"
    establecimiento_id: Optional[int] = None


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None
    establecimiento_id: Optional[int] = None


class PermisoOut(BaseModel):
    id: int
    codigo: str
    modulo: str
    accion: str
    descripcion: Optional[str] = None

    model_config = {"from_attributes": True}


class RolOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    tipo_negocio: str
    permisos: List[str] = []

    model_config = {"from_attributes": True}


class UsuarioTenantOut(BaseModel):
    id: int
    email: str
    nombre: str
    activo: bool
    rol: str
    establecimiento_id: Optional[int] = None
    establecimiento_nombre: Optional[str] = None
    permisos: List[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantOut(BaseModel):
    id: int
    nombre: str
    plan: str
    tipo: str
    activo: bool

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None   # restaurante / pos

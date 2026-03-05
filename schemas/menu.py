from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal


class CategoriaOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    orden: int
    activo: bool

    model_config = {"from_attributes": True}


class CategoriaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    orden: int = 0


class VarianteOut(BaseModel):
    id: int
    nombre: str
    precio: Decimal
    disponible: bool

    model_config = {"from_attributes": True}


class MenuItemOut(BaseModel):
    id: int
    categoria_id: Optional[int] = None
    nombre: str
    descripcion: Optional[str] = None
    es_combo: bool
    precio_override: Optional[Decimal] = None
    imagen_url: Optional[str] = None
    orden: int
    disponible: bool
    activo: bool

    model_config = {"from_attributes": True}


class MenuItemCreate(BaseModel):
    categoria_id: Optional[int] = None
    producto_id: int
    nombre: str
    descripcion: Optional[str] = None
    es_combo: bool = False
    precio_override: Optional[Decimal] = None
    imagen_url: Optional[str] = None
    orden: int = 0


class MenuItemUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_override: Optional[Decimal] = None
    imagen_url: Optional[str] = None
    disponible: Optional[bool] = None
    activo: Optional[bool] = None
    orden: Optional[int] = None


class ModificadorOut(BaseModel):
    id: int
    nombre: str
    precio_adicional: Decimal
    disponible: bool

    model_config = {"from_attributes": True}


class ModificadorGrupoOut(BaseModel):
    id: int
    nombre: str
    requerido: bool
    seleccion_multiple: bool
    modificadores: List[ModificadorOut] = []

    model_config = {"from_attributes": True}

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, SmallInteger, Text
from sqlalchemy.sql import func
from database import Base


class MenuCategoria(Base):
    __tablename__ = "menu_categorias"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(300))
    imagen_url = Column(String(500))
    orden = Column(SmallInteger, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("menu_categorias.id"))
    producto_id = Column(Integer, nullable=False)
    nombre = Column(String(200), nullable=False)
    descripcion = Column(String(500))
    es_combo = Column(Boolean, nullable=False, default=False)
    precio_override = Column(Numeric)
    imagen_url = Column(String(500))
    orden = Column(SmallInteger, nullable=False, default=0)
    disponible = Column(Boolean, nullable=False, default=True)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MenuVariante(Base):
    __tablename__ = "menu_variantes"

    id = Column(Integer, primary_key=True)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    precio = Column(Numeric, nullable=False)
    disponible = Column(Boolean, nullable=False, default=True)
    activo = Column(Boolean, nullable=False, default=True)


class ModificadorGrupo(Base):
    __tablename__ = "modificador_grupos"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    requerido = Column(Boolean, nullable=False, default=False)
    seleccion_multiple = Column(Boolean, nullable=False, default=False)
    min_selecciones = Column(SmallInteger, default=0)
    max_selecciones = Column(SmallInteger)
    activo = Column(Boolean, nullable=False, default=True)


class Modificador(Base):
    __tablename__ = "modificadores"

    id = Column(Integer, primary_key=True)
    grupo_id = Column(Integer, ForeignKey("modificador_grupos.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    precio_adicional = Column(Numeric, nullable=False, default=0)
    disponible = Column(Boolean, nullable=False, default=True)
    activo = Column(Boolean, nullable=False, default=True)

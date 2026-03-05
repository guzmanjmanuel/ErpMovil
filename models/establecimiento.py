from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class CatTipoEstablecimiento(Base):
    __tablename__ = "cat_tipo_establecimiento"

    codigo      = Column(String(2), primary_key=True)
    descripcion = Column(String(50), nullable=False)


class Establecimiento(Base):
    __tablename__ = "establecimientos"

    id                 = Column(Integer, primary_key=True)
    tenant_id          = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    contribuyente_id   = Column(Integer, ForeignKey("contribuyentes.id"), nullable=False)
    nombre             = Column(String(200), nullable=False)
    tipo               = Column(String(2), ForeignKey("cat_tipo_establecimiento.codigo"), nullable=False)
    cod_estable_mh     = Column(String(4))
    cod_estable        = Column(String(10))
    cod_punto_venta_mh = Column(String(4))
    cod_punto_venta    = Column(String(10))
    telefono           = Column(String(30))
    direccion_id       = Column(Integer)   # FK a direcciones, gestionada en DB
    es_principal       = Column(Boolean, nullable=False, default=False)
    activo             = Column(Boolean, nullable=False, default=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())
    updated_at         = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

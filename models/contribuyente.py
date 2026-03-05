from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, SmallInteger
from sqlalchemy.sql import func
from database import Base


class TipoDocumentoIdentificacion(Base):
    __tablename__ = "tipo_documento_identificacion"

    codigo = Column(String(1), primary_key=True)
    descripcion = Column(String(100), nullable=False)


class Contribuyente(Base):
    __tablename__ = "contribuyentes"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    tipo = Column(String(20), nullable=False)        # emisor / receptor
    nit = Column(String(20))
    nrc = Column(String(20))
    tipo_documento_id = Column(String(2))
    num_documento = Column(String(30))
    nombre = Column(String(250), nullable=False)
    nombre_comercial = Column(String(250))
    cod_actividad = Column(String(10))
    desc_actividad = Column(String(250))
    telefono = Column(String(30))
    correo = Column(String(100))
    direccion_id = Column(Integer, ForeignKey("direcciones.id"))
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EmisorDetalle(Base):
    __tablename__ = "emisor_detalle"

    contribuyente_id = Column(Integer, ForeignKey("contribuyentes.id"), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), primary_key=True)
    tipo_establecimiento = Column(String(2), nullable=False)
    cod_estable_mh = Column(String(4))
    cod_estable = Column(String(10))
    cod_punto_venta_mh = Column(String(4))
    cod_punto_venta = Column(String(10))
    tipo_item_expor = Column(SmallInteger)
    recinto_fiscal = Column(String(4))
    regimen = Column(String(20))


class DirectorioCliente(Base):
    __tablename__ = "directorio_clientes"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    contribuyente_id = Column(Integer, ForeignKey("contribuyentes.id"))
    nit = Column(String(20))
    nrc = Column(String(20))
    dui = Column(String(10))
    nombre = Column(String(250), nullable=False)
    nombre_comercial = Column(String(250))
    correo_factura = Column(String(100))
    telefono = Column(String(30))
    tipo_contribuyente = Column(String(20))   # natural / juridico
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

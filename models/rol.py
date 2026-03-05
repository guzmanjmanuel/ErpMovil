from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False)
    descripcion = Column(String(200))
    tipo_negocio = Column(String(20), nullable=False, default="ambos")
    es_sistema = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, nullable=False, default=True)


class Permiso(Base):
    __tablename__ = "permisos"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False)
    modulo = Column(String(30), nullable=False)
    accion = Column(String(30), nullable=False)
    descripcion = Column(String(200))


class RolPermiso(Base):
    __tablename__ = "rol_permisos"

    rol_id = Column(String(50), primary_key=True)
    permiso_id = Column(Integer, ForeignKey("permisos.id"), primary_key=True)


class TenantUsuarioPermiso(Base):
    __tablename__ = "tenant_usuario_permisos"

    tenant_id = Column(Integer, ForeignKey("tenants.id"), primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), primary_key=True)
    permiso_id = Column(Integer, ForeignKey("permisos.id"), primary_key=True)
    concedido = Column(Boolean, nullable=False, default=True)

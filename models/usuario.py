from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    nombre = Column(String(200), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TenantUsuario(Base):
    __tablename__ = "tenant_usuarios"

    tenant_id          = Column(Integer, ForeignKey("tenants.id"), primary_key=True)
    usuario_id         = Column(Integer, ForeignKey("usuarios.id"), primary_key=True)
    rol                = Column(String(20), nullable=False, default="operador")
    activo             = Column(Boolean, nullable=False, default=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())

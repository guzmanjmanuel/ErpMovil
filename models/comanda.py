from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, SmallInteger
from sqlalchemy.sql import func
from database import Base


class AreaCocina(Base):
    __tablename__ = "areas_cocina"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)


class Comanda(Base):
    __tablename__ = "comandas"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    area_cocina_id = Column(Integer, ForeignKey("areas_cocina.id"))
    estado = Column(String(20), nullable=False, default="pendiente")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ComandaItem(Base):
    __tablename__ = "comanda_items"

    id = Column(Integer, primary_key=True)
    comanda_id = Column(Integer, ForeignKey("comandas.id"), nullable=False)
    pedido_item_id = Column(Integer, ForeignKey("pedido_items.id"), nullable=False)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    estado = Column(String(20), nullable=False, default="pendiente")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

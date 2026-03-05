from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, SmallInteger
from database import Base


class Area(Base):
    __tablename__ = "areas"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    nombre = Column(String(100), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)


class Mesa(Base):
    __tablename__ = "mesas"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"))
    numero = Column(String(10), nullable=False)
    capacidad = Column(SmallInteger, nullable=False, default=4)
    estado = Column(String(20), nullable=False, default="disponible")
    qr_code = Column(String(200))

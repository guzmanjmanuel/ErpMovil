from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.sql import func
from database import Base


class TurnoCaja(Base):
    __tablename__ = "turnos_caja"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    estado = Column(String(20), nullable=False, default="abierto")
    fondo_inicial = Column(Numeric, nullable=False, default=0)
    total_efectivo = Column(Numeric)
    total_tarjeta = Column(Numeric)
    total_qr = Column(Numeric)
    total_ventas = Column(Numeric)
    total_descuentos = Column(Numeric)
    diferencia_caja = Column(Numeric)
    observaciones = Column(String(500))
    abierto_en = Column(DateTime(timezone=True), server_default=func.now())
    cerrado_en = Column(DateTime(timezone=True))


class CajaMovimiento(Base):
    __tablename__ = "caja_movimientos"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    turno_id = Column(Integer, ForeignKey("turnos_caja.id"), nullable=False)
    tipo = Column(String(20), nullable=False)       # ingreso / egreso
    motivo = Column(String(200), nullable=False)    # nombre real en la BD
    monto = Column(Numeric, nullable=False)
    referencia = Column(String(200))
    notas = Column(String(500))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

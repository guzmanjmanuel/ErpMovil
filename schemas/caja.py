from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime


class TurnoAbrirRequest(BaseModel):
    fondo_inicial: Decimal = Decimal("0")


class TurnoCerrarRequest(BaseModel):
    total_efectivo: Optional[Decimal] = None
    total_tarjeta: Optional[Decimal] = None
    total_qr: Optional[Decimal] = None
    observaciones: Optional[str] = None


class TurnoOut(BaseModel):
    id: int
    usuario_id: int
    estado: str
    fondo_inicial: Decimal
    total_efectivo: Optional[Decimal] = None
    total_tarjeta: Optional[Decimal] = None
    total_qr: Optional[Decimal] = None
    total_ventas: Optional[Decimal] = None
    total_descuentos: Optional[Decimal] = None
    diferencia_caja: Optional[Decimal] = None
    observaciones: Optional[str] = None
    abierto_en: datetime
    cerrado_en: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MovimientoCreate(BaseModel):
    tipo: str           # ingreso / egreso
    concepto: str
    monto: Decimal


class MovimientoOut(BaseModel):
    id: int
    turno_id: int
    tipo: str
    concepto: str
    monto: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}

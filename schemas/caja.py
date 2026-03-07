from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class TurnoAbrirRequest(BaseModel):
    fondo_inicial: Decimal = Decimal("0")


class TurnoCerrarRequest(BaseModel):
    efectivo_contado: Decimal = Decimal("0")
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
    tipo: str                       # ingreso / egreso
    motivo: str                     # nombre real de la columna en BD
    monto: Decimal
    referencia: Optional[str] = None
    notas: Optional[str] = None


class MovimientoOut(BaseModel):
    id: int
    turno_id: int
    tipo: str
    motivo: str
    monto: Decimal
    referencia: Optional[str] = None
    notas: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DesglosePago(BaseModel):
    forma_pago_codigo: str
    forma_pago_descripcion: str
    cantidad_transacciones: int
    total: Decimal


class TurnoResumen(BaseModel):
    turno_id: int
    estado: str
    fondo_inicial: Decimal
    abierto_en: datetime
    cerrado_en: Optional[datetime] = None
    desglose_pagos: List[DesglosePago]
    total_ventas_sistema: Decimal
    total_descuentos: Decimal
    total_ingresos_manuales: Decimal
    total_egresos_manuales: Decimal
    efectivo_esperado_caja: Decimal
    efectivo_contado: Optional[Decimal] = None
    diferencia_caja: Optional[Decimal] = None
    cantidad_pedidos: int


class ResumenDia(BaseModel):
    fecha: str
    cantidad_turnos: int
    desglose_pagos: List[DesglosePago]
    ventas_total: Decimal
    descuentos_total: Decimal
    cantidad_pedidos: int

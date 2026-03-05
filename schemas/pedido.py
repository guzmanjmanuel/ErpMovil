from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime


class PedidoItemCreate(BaseModel):
    menu_item_id: int
    variante_id: Optional[int] = None
    cantidad: Decimal = Decimal("1")
    precio_unitario: Decimal
    descuento: Decimal = Decimal("0")
    notas: Optional[str] = None


class PedidoItemOut(BaseModel):
    id: int
    menu_item_id: int
    variante_id: Optional[int] = None
    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal
    subtotal: Decimal
    estado: str
    notas: Optional[str] = None
    num_item: int

    model_config = {"from_attributes": True}


class PedidoCreate(BaseModel):
    canal: str                              # mesa / delivery / pickup
    mesa_id: Optional[int] = None
    nombre_pickup: Optional[str] = None
    direccion_entrega: Optional[str] = None
    referencia_entrega: Optional[str] = None
    nit_cliente: Optional[str] = None
    nombre_cliente: Optional[str] = None
    notas: Optional[str] = None
    items: List[PedidoItemCreate] = []


class PedidoOut(BaseModel):
    id: int
    canal: str
    estado: str
    mesa_id: Optional[int] = None
    nombre_pickup: Optional[str] = None
    nit_cliente: Optional[str] = None
    nombre_cliente: Optional[str] = None
    subtotal: Decimal
    descuento: Decimal
    total: Decimal
    numero_pedido: Optional[str] = None
    notas: Optional[str] = None
    usuario_id: Optional[int] = None
    created_at: datetime
    items: List[PedidoItemOut] = []

    model_config = {"from_attributes": True}


class PedidoEstadoUpdate(BaseModel):
    estado: str  # borrador / confirmado / en_preparacion / listo / entregado / pagado / anulado


class PagoCreate(BaseModel):
    forma_pago: str         # efectivo / tarjeta / qr
    monto: Decimal
    monto_recibido: Optional[Decimal] = None
    referencia_pos: Optional[str] = None
    ultimos_4: Optional[str] = None
    turno_id: Optional[int] = None


class PagoOut(BaseModel):
    id: int
    pedido_id: int
    forma_pago: str
    monto: Decimal
    monto_recibido: Optional[Decimal] = None
    cambio: Optional[Decimal] = None
    anulado: bool
    created_at: datetime

    model_config = {"from_attributes": True}

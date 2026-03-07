from pydantic import BaseModel, model_validator
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

# Códigos válidos CAT-017 — Forma de Pago
FORMAS_PAGO_CAT017 = {
    "01": "Billetes y monedas",
    "02": "Tarjeta Débito",
    "03": "Tarjeta Crédito",
    "04": "Cheque",
    "05": "Transferencia-Depósito Bancario",
    "08": "Dinero electrónico",
    "09": "Monedero electrónico",
    "11": "Bitcoin",
    "12": "Otras Criptomonedas",
    "13": "Cuentas por pagar del receptor",
    "14": "Giro bancario",
    "99": "Otros",
}

# Códigos válidos CAT-016 — Condición de la Operación
CONDICIONES_OPERACION = {1, 2, 3}


class ComponenteElegidoIn(BaseModel):
    grupo_id: int
    opcion_original_id: Optional[int] = None
    opcion_elegida_id: Optional[int] = None   # None = rechazado
    cantidad: Decimal = Decimal("1")
    accion: str = "INCLUIDO"                  # INCLUIDO | RECHAZADO | SUSTITUIDO
    precio_extra: Decimal = Decimal("0")


class PedidoItemCreate(BaseModel):
    menu_item_id: int
    variante_id: Optional[int] = None
    cantidad: Decimal = Decimal("1")
    precio_unitario: Decimal
    descuento: Decimal = Decimal("0")
    notas: Optional[str] = None
    componentes: List[ComponenteElegidoIn] = []


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
    # CAT-016: 1=Contado (default), 2=A crédito, 3=Otro
    condicion_operacion: int = 1
    items: List[PedidoItemCreate] = []

    @model_validator(mode="after")
    def validar_condicion(self):
        if self.condicion_operacion not in CONDICIONES_OPERACION:
            raise ValueError("condicion_operacion debe ser 1 (Contado), 2 (A crédito) o 3 (Otro)")
        return self


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
    condicion_operacion: int = 1
    numero_pedido: Optional[str] = None
    notas: Optional[str] = None
    usuario_id: Optional[int] = None
    created_at: datetime
    items: List[PedidoItemOut] = []

    model_config = {"from_attributes": True}


class PedidoEstadoUpdate(BaseModel):
    estado: str  # borrador / confirmado / en_preparacion / listo / entregado / pagado / anulado


class DescuentoUpdate(BaseModel):
    descuento: Decimal

    @model_validator(mode="after")
    def validar_descuento(self):
        if self.descuento < 0:
            raise ValueError("El descuento no puede ser negativo")
        return self


class PagoCreate(BaseModel):
    # CAT-017: "01"=Billetes y monedas, "02"=Tarjeta Débito, "03"=Tarjeta Crédito, etc.
    forma_pago: str
    # Requerido si forma_pago = "99" (Otros)
    forma_pago_referencia: Optional[str] = None
    monto: Decimal
    monto_recibido: Optional[Decimal] = None
    referencia_pos: Optional[str] = None
    ultimos_4: Optional[str] = None
    turno_id: Optional[int] = None

    @model_validator(mode="after")
    def validar_forma_pago(self):
        if self.forma_pago not in FORMAS_PAGO_CAT017:
            codigos = ", ".join(sorted(FORMAS_PAGO_CAT017.keys()))
            raise ValueError(f"forma_pago inválida. Códigos CAT-017 válidos: {codigos}")
        if self.forma_pago == "99" and not self.forma_pago_referencia:
            raise ValueError("forma_pago_referencia es requerida cuando forma_pago = '99' (Otros)")
        return self


class PagoOut(BaseModel):
    id: int
    pedido_id: int
    turno_id: Optional[int] = None
    forma_pago: str
    forma_pago_referencia: Optional[str] = None
    monto: Decimal
    monto_recibido: Optional[Decimal] = None
    cambio: Optional[Decimal] = None
    referencia_pos: Optional[str] = None
    ultimos_4: Optional[str] = None
    anulado: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class VentaRapidaPago(BaseModel):
    """Un pago dentro de una venta rápida (admite split payment)."""
    # CAT-017
    forma_pago: str
    forma_pago_referencia: Optional[str] = None
    monto: Decimal
    monto_recibido: Optional[Decimal] = None
    referencia_pos: Optional[str] = None
    ultimos_4: Optional[str] = None

    @model_validator(mode="after")
    def validar_forma_pago(self):
        if self.forma_pago not in FORMAS_PAGO_CAT017:
            codigos = ", ".join(sorted(FORMAS_PAGO_CAT017.keys()))
            raise ValueError(f"forma_pago inválida. Códigos CAT-017 válidos: {codigos}")
        if self.forma_pago == "99" and not self.forma_pago_referencia:
            raise ValueError("forma_pago_referencia es requerida cuando forma_pago = '99' (Otros)")
        return self


class VentaRapidaCreate(BaseModel):
    """Crea un pedido y lo paga en una sola llamada (flujo POS directo)."""
    canal: str = "pickup"
    mesa_id: Optional[int] = None
    nombre_pickup: Optional[str] = None
    nit_cliente: Optional[str] = None
    nombre_cliente: Optional[str] = None
    notas: Optional[str] = None
    condicion_operacion: int = 1
    items: List[PedidoItemCreate]
    pagos: List[VentaRapidaPago]

    @model_validator(mode="after")
    def validar(self):
        if not self.items:
            raise ValueError("Se requiere al menos un ítem")
        if not self.pagos:
            raise ValueError("Se requiere al menos un pago")
        if self.condicion_operacion not in CONDICIONES_OPERACION:
            raise ValueError("condicion_operacion debe ser 1, 2 o 3")
        return self


class VentaRapidaOut(BaseModel):
    pedido: PedidoOut
    pagos: List[PagoOut]
    cambio_total: Decimal

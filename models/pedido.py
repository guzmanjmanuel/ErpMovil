from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, SmallInteger, Text
from sqlalchemy.sql import func
from database import Base


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    canal = Column(String(20), nullable=False)          # mesa / delivery / pickup
    estado = Column(String(20), nullable=False, default="borrador")
    mesa_id = Column(Integer, ForeignKey("mesas.id"))
    cliente_id = Column(Integer)
    direccion_entrega = Column(String(300))
    referencia_entrega = Column(String(200))
    nombre_pickup = Column(String(150))
    nit_cliente = Column(String(14))
    nombre_cliente = Column(String(250))
    subtotal = Column(Numeric, nullable=False, default=0)
    descuento = Column(Numeric, nullable=False, default=0)
    total = Column(Numeric, nullable=False, default=0)
    dte_id = Column(Integer)
    numero_pedido = Column(String(20))
    notas = Column(String(500))
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PedidoItem(Base):
    __tablename__ = "pedido_items"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    variante_id = Column(Integer, ForeignKey("menu_variantes.id"))
    cantidad = Column(Numeric, nullable=False, default=1)
    precio_unitario = Column(Numeric, nullable=False)
    descuento = Column(Numeric, nullable=False, default=0)
    subtotal = Column(Numeric, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="pendiente")
    notas = Column(String(300))
    num_item = Column(SmallInteger, nullable=False)


class PedidoItemComponente(Base):
    """Decisión del cliente sobre un componente de un combo (incluido / rechazado / sustituido)."""
    __tablename__ = "pedido_item_componentes"

    id                 = Column(Integer, primary_key=True)
    pedido_item_id     = Column(Integer, ForeignKey("pedido_items.id"), nullable=False)
    tenant_id          = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    grupo_id           = Column(Integer, nullable=False)   # combo_grupos.id
    opcion_original_id = Column(Integer)                   # combo_grupo_opciones.id (la default)
    opcion_elegida_id  = Column(Integer)                   # combo_grupo_opciones.id (la elegida; NULL=rechazada)
    cantidad           = Column(Numeric(14, 4), nullable=False, default=1)
    accion             = Column(String(20), nullable=False, default="INCLUIDO")  # INCLUIDO | RECHAZADO | SUSTITUIDO
    precio_extra       = Column(Numeric(14, 4), nullable=False, default=0)


class PedidoPago(Base):
    __tablename__ = "pedido_pagos"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id"), nullable=False)
    turno_id = Column(Integer, ForeignKey("turnos_caja.id"))
    forma_pago = Column(String(20), nullable=False)     # efectivo / tarjeta / qr
    monto = Column(Numeric, nullable=False)
    monto_recibido = Column(Numeric)
    cambio = Column(Numeric)
    referencia_pos = Column(String(100))
    ultimos_4 = Column(String(4))
    anulado = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

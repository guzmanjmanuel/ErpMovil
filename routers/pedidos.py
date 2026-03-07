from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from database import get_db
from models.pedido import Pedido, PedidoItem, PedidoPago, PedidoItemComponente
from models.mesa import Mesa
from models.menu import MenuItem
from models.caja import TurnoCaja
from models.inventario import RecetaItem, ComboGrupoOpcion, InventarioStock, InventarioMovimiento
from schemas.pedido import (
    PedidoCreate, PedidoOut, PedidoItemOut,
    PedidoEstadoUpdate, DescuentoUpdate,
    PagoCreate, PagoOut,
    VentaRapidaCreate, VentaRapidaOut,
    FORMAS_PAGO_CAT017,
)
from auth.deps import get_current_user, get_tenant_user
from models.usuario import Usuario

router = APIRouter(prefix="/tenants/{tenant_id}/pedidos", tags=["Pedidos"])

ESTADOS_VALIDOS = {
    "borrador", "confirmado", "en_preparacion",
    "listo", "entregado", "pagado", "anulado",
}


# ── Helpers de inventario ──────────────────────────────────────────────────────

def _descontar_producto(db: Session, producto_id: int, cantidad: Decimal, tenant_id: int, pedido_id: int, usuario_id: int):
    receta = db.query(RecetaItem).filter(
        RecetaItem.tenant_id == tenant_id,
        RecetaItem.producto_id == producto_id,
    ).all()

    items_a_descontar = [
        (ri.insumo_id, ri.cantidad * cantidad)
        for ri in receta
    ] if receta else [(producto_id, cantidad)]

    for insumo_id, qty in items_a_descontar:
        stock = db.query(InventarioStock).filter(
            InventarioStock.tenant_id == tenant_id,
            InventarioStock.producto_id == insumo_id,
            InventarioStock.cantidad > 0,
        ).order_by(InventarioStock.updated_at).first()

        if not stock or stock.cantidad < qty:
            continue

        costo = stock.costo_promedio or Decimal("0")
        mov = InventarioMovimiento(
            tenant_id=tenant_id,
            tipo_movimiento="VENTA",
            producto_id=insumo_id,
            ubicacion_origen_id=stock.ubicacion_id,
            cantidad=qty,
            costo_unitario=costo,
            referencia_tipo="PEDIDO",
            referencia_id=pedido_id,
            usuario_id=usuario_id,
            notas=f"Venta automática pedido #{pedido_id}",
        )
        db.add(mov)
        stock.cantidad -= qty


def _descontar_inventario_pedido(db: Session, pedido: Pedido, tenant_id: int, usuario_id: int):
    items = db.query(PedidoItem).filter(PedidoItem.pedido_id == pedido.id).all()
    for item in items:
        componentes = db.query(PedidoItemComponente).filter(
            PedidoItemComponente.pedido_item_id == item.id
        ).all()
        if componentes:
            for comp in componentes:
                if comp.accion == "RECHAZADO" or not comp.opcion_elegida_id:
                    continue
                opcion = db.query(ComboGrupoOpcion).get(comp.opcion_elegida_id)
                if not opcion:
                    continue
                _descontar_producto(
                    db, opcion.producto_id,
                    Decimal(str(comp.cantidad)) * Decimal(str(item.cantidad)),
                    tenant_id, pedido.id, usuario_id,
                )
        else:
            menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
            if menu_item and menu_item.producto_id:
                _descontar_producto(
                    db, menu_item.producto_id, Decimal(str(item.cantidad)),
                    tenant_id, pedido.id, usuario_id,
                )


def _calcular_totales(items_data) -> Decimal:
    return sum(
        (it.precio_unitario * it.cantidad) - it.descuento
        for it in items_data
    )


def _get_turno_abierto(db: Session, tenant_id: int, usuario_id: int) -> TurnoCaja | None:
    return db.query(TurnoCaja).filter(
        TurnoCaja.tenant_id == tenant_id,
        TurnoCaja.usuario_id == usuario_id,
        TurnoCaja.estado == "abierto",
    ).first()


def _construir_pedido_out(db: Session, pedido: Pedido) -> PedidoOut:
    items = db.query(PedidoItem).filter(PedidoItem.pedido_id == pedido.id).all()
    po = PedidoOut.model_validate(pedido)
    po.items = [PedidoItemOut.model_validate(i) for i in items]
    return po


def _insertar_items(db: Session, pedido_id: int, tenant_id: int, items_data) -> list:
    items_db = []
    for idx, it in enumerate(items_data, start=1):
        item_subtotal = (it.precio_unitario * it.cantidad) - it.descuento
        pi = PedidoItem(
            tenant_id=tenant_id,
            pedido_id=pedido_id,
            menu_item_id=it.menu_item_id,
            variante_id=it.variante_id,
            cantidad=it.cantidad,
            precio_unitario=it.precio_unitario,
            descuento=it.descuento,
            subtotal=item_subtotal,
            estado="pendiente",
            notas=it.notas,
            num_item=idx,
        )
        db.add(pi)
        db.flush()
        for comp in it.componentes:
            db.add(PedidoItemComponente(
                pedido_item_id=pi.id,
                tenant_id=tenant_id,
                grupo_id=comp.grupo_id,
                opcion_original_id=comp.opcion_original_id,
                opcion_elegida_id=comp.opcion_elegida_id,
                cantidad=comp.cantidad,
                accion=comp.accion,
                precio_extra=comp.precio_extra,
            ))
        items_db.append(pi)
    return items_db


def _crear_pago(
    db: Session,
    tenant_id: int,
    pedido_id: int,
    turno_id: int | None,
    pago_data,
) -> PedidoPago:
    cambio = None
    if pago_data.monto_recibido is not None:
        cambio = pago_data.monto_recibido - pago_data.monto

    pago = PedidoPago(
        tenant_id=tenant_id,
        pedido_id=pedido_id,
        turno_id=turno_id,
        forma_pago=pago_data.forma_pago,
        forma_pago_referencia=getattr(pago_data, "forma_pago_referencia", None),
        monto=pago_data.monto,
        monto_recibido=pago_data.monto_recibido,
        cambio=cambio,
        referencia_pos=getattr(pago_data, "referencia_pos", None),
        ultimos_4=getattr(pago_data, "ultimos_4", None),
    )
    db.add(pago)
    return pago


# ── Pedidos CRUD ───────────────────────────────────────────────────────────────

@router.get("", response_model=List[PedidoOut])
def listar_pedidos(
    tenant_id: int,
    estado: str | None = None,
    canal: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(Pedido).filter(Pedido.tenant_id == tenant_id)
    if estado:
        q = q.filter(Pedido.estado == estado)
    if canal:
        q = q.filter(Pedido.canal == canal)
    return [_construir_pedido_out(db, p) for p in q.order_by(Pedido.created_at.desc()).limit(limit)]


@router.get("/{pedido_id}", response_model=PedidoOut)
def obtener_pedido(
    tenant_id: int,
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    pedido = db.query(Pedido).filter(
        Pedido.id == pedido_id, Pedido.tenant_id == tenant_id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    return _construir_pedido_out(db, pedido)


@router.post("", response_model=PedidoOut, status_code=201)
def crear_pedido(
    tenant_id: int,
    data: PedidoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    if data.canal not in {"mesa", "delivery", "pickup"}:
        raise HTTPException(400, "Canal inválido. Use: mesa, delivery, pickup")

    subtotal = _calcular_totales(data.items)

    pedido = Pedido(
        tenant_id=tenant_id,
        canal=data.canal,
        estado="borrador",
        mesa_id=data.mesa_id,
        nombre_pickup=data.nombre_pickup,
        direccion_entrega=data.direccion_entrega,
        referencia_entrega=data.referencia_entrega,
        nit_cliente=data.nit_cliente,
        nombre_cliente=data.nombre_cliente,
        notas=data.notas,
        condicion_operacion=data.condicion_operacion,
        subtotal=subtotal,
        descuento=Decimal("0"),
        total=subtotal,
        usuario_id=current_user.id,
    )
    db.add(pedido)
    db.flush()

    _insertar_items(db, pedido.id, tenant_id, data.items)
    pedido.numero_pedido = f"P-{pedido.id:06d}"

    if data.mesa_id:
        mesa = db.query(Mesa).filter(Mesa.id == data.mesa_id).first()
        if mesa:
            mesa.estado = "ocupada"

    db.commit()
    db.refresh(pedido)
    return _construir_pedido_out(db, pedido)


@router.patch("/{pedido_id}/estado", response_model=PedidoOut)
def actualizar_estado(
    tenant_id: int,
    pedido_id: int,
    data: PedidoEstadoUpdate,
    db: Session = Depends(get_db),
    tu=Depends(get_tenant_user),
):
    if data.estado not in ESTADOS_VALIDOS:
        raise HTTPException(400, f"Estado inválido. Use: {', '.join(ESTADOS_VALIDOS)}")
    pedido = db.query(Pedido).filter(
        Pedido.id == pedido_id, Pedido.tenant_id == tenant_id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")

    estado_anterior = pedido.estado
    pedido.estado = data.estado

    if data.estado == "entregado" and estado_anterior != "entregado":
        _descontar_inventario_pedido(db, pedido, tenant_id, tu.usuario_id)

    if data.estado in {"pagado", "anulado"} and pedido.mesa_id:
        mesa = db.query(Mesa).filter(Mesa.id == pedido.mesa_id).first()
        if mesa:
            mesa.estado = "disponible"

    db.commit()
    db.refresh(pedido)
    return _construir_pedido_out(db, pedido)


@router.patch("/{pedido_id}/descuento", response_model=PedidoOut)
def aplicar_descuento(
    tenant_id: int,
    pedido_id: int,
    data: DescuentoUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    pedido = db.query(Pedido).filter(
        Pedido.id == pedido_id, Pedido.tenant_id == tenant_id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    if pedido.estado in {"pagado", "anulado"}:
        raise HTTPException(400, "No se puede modificar un pedido pagado o anulado")
    if data.descuento > pedido.subtotal:
        raise HTTPException(400, "El descuento no puede superar el subtotal")

    pedido.descuento = data.descuento
    pedido.total = pedido.subtotal - data.descuento

    db.commit()
    db.refresh(pedido)
    return _construir_pedido_out(db, pedido)


# ── Pagos ──────────────────────────────────────────────────────────────────────

@router.get("/{pedido_id}/pagos", response_model=List[PagoOut])
def listar_pagos(
    tenant_id: int,
    pedido_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    return db.query(PedidoPago).filter(
        PedidoPago.pedido_id == pedido_id,
        PedidoPago.tenant_id == tenant_id,
        PedidoPago.anulado == False,
    ).all()


@router.post("/{pedido_id}/pagos", response_model=PagoOut, status_code=201)
def registrar_pago(
    tenant_id: int,
    pedido_id: int,
    data: PagoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    pedido = db.query(Pedido).filter(
        Pedido.id == pedido_id, Pedido.tenant_id == tenant_id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    if pedido.estado == "anulado":
        raise HTTPException(400, "No se puede pagar un pedido anulado")

    # Vincular automáticamente al turno abierto si no se especificó
    turno_id = data.turno_id
    if turno_id is None:
        turno = _get_turno_abierto(db, tenant_id, current_user.id)
        if turno:
            turno_id = turno.id

    pago = _crear_pago(db, tenant_id, pedido_id, turno_id, data)

    # Marcar pedido como pagado si el acumulado cubre el total
    pagos_previos = db.query(PedidoPago).filter(
        PedidoPago.pedido_id == pedido_id,
        PedidoPago.anulado == False,
    ).all()
    total_pagado = sum(p.monto for p in pagos_previos) + data.monto
    if total_pagado >= pedido.total:
        pedido.estado = "pagado"
        if pedido.mesa_id:
            mesa = db.query(Mesa).filter(Mesa.id == pedido.mesa_id).first()
            if mesa:
                mesa.estado = "disponible"

    db.commit()
    db.refresh(pago)
    return pago


@router.delete("/{pedido_id}/pagos/{pago_id}", status_code=204)
def anular_pago(
    tenant_id: int,
    pedido_id: int,
    pago_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    pago = db.query(PedidoPago).filter(
        PedidoPago.id == pago_id,
        PedidoPago.pedido_id == pedido_id,
        PedidoPago.tenant_id == tenant_id,
        PedidoPago.anulado == False,
    ).first()
    if not pago:
        raise HTTPException(404, "Pago no encontrado o ya anulado")

    pago.anulado = True

    # Revertir estado del pedido si estaba pagado
    pedido = db.query(Pedido).filter(Pedido.id == pedido_id).first()
    if pedido and pedido.estado == "pagado":
        pedido.estado = "entregado"

    db.commit()


# ── Venta Rápida (POS directo) ─────────────────────────────────────────────────

@router.post("/venta-rapida", response_model=VentaRapidaOut, status_code=201)
def venta_rapida(
    tenant_id: int,
    data: VentaRapidaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    """
    Crea un pedido y lo paga en una sola llamada.
    Ideal para ventas de mostrador/POS sin estados intermedios.
    Soporta split payment (múltiples formas de pago CAT-017).
    """
    if data.canal not in {"mesa", "delivery", "pickup"}:
        raise HTTPException(400, "Canal inválido. Use: mesa, delivery, pickup")

    subtotal = _calcular_totales(data.items)

    # Validar que los pagos cubran el total
    total_pagos = sum(p.monto for p in data.pagos)
    if total_pagos < subtotal:
        raise HTTPException(
            400,
            f"Monto de pagos insuficiente. Total: {subtotal}, Pagado: {total_pagos}"
        )

    turno = _get_turno_abierto(db, tenant_id, current_user.id)

    pedido = Pedido(
        tenant_id=tenant_id,
        canal=data.canal,
        estado="pagado",
        mesa_id=data.mesa_id,
        nombre_pickup=data.nombre_pickup,
        nit_cliente=data.nit_cliente,
        nombre_cliente=data.nombre_cliente,
        notas=data.notas,
        condicion_operacion=data.condicion_operacion,
        subtotal=subtotal,
        descuento=Decimal("0"),
        total=subtotal,
        usuario_id=current_user.id,
    )
    db.add(pedido)
    db.flush()

    _insertar_items(db, pedido.id, tenant_id, data.items)
    pedido.numero_pedido = f"P-{pedido.id:06d}"

    _descontar_inventario_pedido(db, pedido, tenant_id, current_user.id)

    pagos_db = [
        _crear_pago(db, tenant_id, pedido.id, turno.id if turno else None, p)
        for p in data.pagos
    ]

    db.commit()
    db.refresh(pedido)
    for p in pagos_db:
        db.refresh(p)

    total_recibido = sum(
        p.monto_recibido for p in data.pagos if p.monto_recibido is not None
    )
    cambio_total = max(Decimal("0"), total_recibido - subtotal)

    return VentaRapidaOut(
        pedido=_construir_pedido_out(db, pedido),
        pagos=[PagoOut.model_validate(p) for p in pagos_db],
        cambio_total=cambio_total,
    )

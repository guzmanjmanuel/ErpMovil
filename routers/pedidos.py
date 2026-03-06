from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from database import get_db
from models.pedido import Pedido, PedidoItem, PedidoPago, PedidoItemComponente
from models.mesa import Mesa
from models.menu import MenuItem
from models.inventario import RecetaItem, ComboGrupoOpcion, InventarioStock, InventarioMovimiento
from schemas.pedido import (
    PedidoCreate, PedidoOut, PedidoItemOut,
    PedidoEstadoUpdate, PagoCreate, PagoOut,
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
    """Descuenta los insumos de la receta del producto. Si no tiene receta, descuenta el producto directamente."""
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
            continue  # stock insuficiente: registrar movimiento de todas formas por trazabilidad

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
    """Descuenta inventario al entregar un pedido, respetando las elecciones del cliente en combos."""
    items = db.query(PedidoItem).filter(PedidoItem.pedido_id == pedido.id).all()

    for item in items:
        componentes = db.query(PedidoItemComponente).filter(
            PedidoItemComponente.pedido_item_id == item.id
        ).all()

        if componentes:
            # Es un combo: descontar según lo que eligió el cliente
            for comp in componentes:
                if comp.accion == "RECHAZADO":
                    continue
                if not comp.opcion_elegida_id:
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
            # Producto simple: obtener producto_id desde menu_item
            menu_item = db.query(MenuItem).filter(MenuItem.id == item.menu_item_id).first()
            if menu_item and menu_item.producto_id:
                _descontar_producto(
                    db, menu_item.producto_id, Decimal(str(item.cantidad)),
                    tenant_id, pedido.id, usuario_id,
                )


def _calcular_totales(items_data):
    subtotal = Decimal("0")
    for it in items_data:
        subtotal += (it.precio_unitario * it.cantidad) - it.descuento
    return subtotal


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
    pedidos = q.order_by(Pedido.created_at.desc()).limit(limit).all()
    result = []
    for p in pedidos:
        items = db.query(PedidoItem).filter(PedidoItem.pedido_id == p.id).all()
        po = PedidoOut.model_validate(p)
        po.items = [PedidoItemOut.model_validate(i) for i in items]
        result.append(po)
    return result


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
    items = db.query(PedidoItem).filter(PedidoItem.pedido_id == pedido_id).all()
    po = PedidoOut.model_validate(pedido)
    po.items = [PedidoItemOut.model_validate(i) for i in items]
    return po


@router.post("", response_model=PedidoOut, status_code=201)
def crear_pedido(
    tenant_id: int,
    data: PedidoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    canales_validos = {"mesa", "delivery", "pickup"}
    if data.canal not in canales_validos:
        raise HTTPException(400, f"Canal inválido. Use: {', '.join(canales_validos)}")

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
        subtotal=subtotal,
        descuento=Decimal("0"),
        total=subtotal,
        usuario_id=current_user.id,
    )
    db.add(pedido)
    db.flush()

    items_db = []
    for idx, it in enumerate(data.items, start=1):
        item_subtotal = (it.precio_unitario * it.cantidad) - it.descuento
        pi = PedidoItem(
            tenant_id=tenant_id,
            pedido_id=pedido.id,
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
        db.flush()  # obtener pi.id

        # Guardar elecciones de componentes para combos
        for comp in it.componentes:
            pic = PedidoItemComponente(
                pedido_item_id=pi.id,
                tenant_id=tenant_id,
                grupo_id=comp.grupo_id,
                opcion_original_id=comp.opcion_original_id,
                opcion_elegida_id=comp.opcion_elegida_id,
                cantidad=comp.cantidad,
                accion=comp.accion,
                precio_extra=comp.precio_extra,
            )
            db.add(pic)

        items_db.append(pi)

    # Marcar mesa como ocupada
    if data.mesa_id:
        mesa = db.query(Mesa).filter(Mesa.id == data.mesa_id).first()
        if mesa:
            mesa.estado = "ocupada"

    db.commit()
    db.refresh(pedido)

    po = PedidoOut.model_validate(pedido)
    po.items = [PedidoItemOut.model_validate(i) for i in items_db]
    return po


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

    # Descontar inventario al marcar como entregado (solo una vez)
    if data.estado == "entregado" and estado_anterior != "entregado":
        _descontar_inventario_pedido(db, pedido, tenant_id, tu.usuario_id)

    # Liberar mesa si el pedido se cierra
    if data.estado in {"pagado", "anulado"} and pedido.mesa_id:
        mesa = db.query(Mesa).filter(Mesa.id == pedido.mesa_id).first()
        if mesa:
            mesa.estado = "disponible"

    db.commit()
    db.refresh(pedido)
    items = db.query(PedidoItem).filter(PedidoItem.pedido_id == pedido_id).all()
    po = PedidoOut.model_validate(pedido)
    po.items = [PedidoItemOut.model_validate(i) for i in items]
    return po


# ── Pagos ─────────────────────────────────────────────────────────────────────

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
    _=Depends(get_tenant_user),
):
    pedido = db.query(Pedido).filter(
        Pedido.id == pedido_id, Pedido.tenant_id == tenant_id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")

    cambio = None
    if data.monto_recibido is not None:
        cambio = data.monto_recibido - data.monto

    pago = PedidoPago(
        tenant_id=tenant_id,
        pedido_id=pedido_id,
        turno_id=data.turno_id,
        forma_pago=data.forma_pago,
        monto=data.monto,
        monto_recibido=data.monto_recibido,
        cambio=cambio,
        referencia_pos=data.referencia_pos,
        ultimos_4=data.ultimos_4,
    )
    db.add(pago)

    # Marcar pedido como pagado si el monto cubre el total
    pagos_anteriores = db.query(PedidoPago).filter(
        PedidoPago.pedido_id == pedido_id,
        PedidoPago.anulado == False,
    ).all()
    total_pagado = sum(p.monto for p in pagos_anteriores) + data.monto
    if total_pagado >= pedido.total:
        pedido.estado = "pagado"
        if pedido.mesa_id:
            mesa = db.query(Mesa).filter(Mesa.id == pedido.mesa_id).first()
            if mesa:
                mesa.estado = "disponible"

    db.commit()
    db.refresh(pago)
    return pago

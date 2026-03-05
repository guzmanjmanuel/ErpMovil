from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from database import get_db
from models.pedido import Pedido, PedidoItem, PedidoPago
from models.mesa import Mesa
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
    _=Depends(get_tenant_user),
):
    if data.estado not in ESTADOS_VALIDOS:
        raise HTTPException(400, f"Estado inválido. Use: {', '.join(ESTADOS_VALIDOS)}")
    pedido = db.query(Pedido).filter(
        Pedido.id == pedido_id, Pedido.tenant_id == tenant_id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido no encontrado")
    pedido.estado = data.estado

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

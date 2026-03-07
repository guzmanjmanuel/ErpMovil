from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List
from decimal import Decimal
from datetime import datetime, timezone, date
from database import get_db
from models.caja import TurnoCaja, CajaMovimiento
from models.pedido import PedidoPago, Pedido
from schemas.caja import (
    TurnoAbrirRequest, TurnoCerrarRequest, TurnoOut,
    MovimientoCreate, MovimientoOut,
    DesglosePago, TurnoResumen, ResumenDia,
)
from auth.deps import get_current_user, get_tenant_user
from models.usuario import Usuario

router = APIRouter(prefix="/tenants/{tenant_id}/caja", tags=["Caja"])

_CAT017_DESC: dict[str, str] = {
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
_COD_EFECTIVO = "01"


# ── Helper: resumen en 3 queries en vez de 6 ──────────────────────────────────

def _calcular_resumen_turno(db: Session, turno: TurnoCaja, tenant_id: int) -> TurnoResumen:

    # Query 1: desglose de pagos por forma CAT-017
    filas_pagos = db.query(
        PedidoPago.forma_pago,
        func.count(PedidoPago.id).label("cantidad"),
        func.coalesce(func.sum(PedidoPago.monto), 0).label("total"),
    ).filter(
        PedidoPago.turno_id == turno.id,
        PedidoPago.tenant_id == tenant_id,
        PedidoPago.anulado == False,
    ).group_by(PedidoPago.forma_pago).order_by(PedidoPago.forma_pago).all()

    desglose: list[DesglosePago] = []
    total_sistema = Decimal("0")
    pagos_efectivo = Decimal("0")
    pedido_ids_set: set[int] = set()

    for fila in filas_pagos:
        total = Decimal(str(fila.total))
        total_sistema += total
        if fila.forma_pago == _COD_EFECTIVO:
            pagos_efectivo = total
        desglose.append(DesglosePago(
            forma_pago_codigo=fila.forma_pago,
            forma_pago_descripcion=_CAT017_DESC.get(fila.forma_pago, fila.forma_pago),
            cantidad_transacciones=fila.cantidad,
            total=total,
        ))

    # Query 2: descuentos + cantidad de pedidos en una sola pasada
    # Usa subquery de pedido_pagos para obtener los pedido_ids del turno
    fila_pedidos = db.query(
        func.count(func.distinct(PedidoPago.pedido_id)).label("cantidad_pedidos"),
        func.coalesce(
            func.sum(
                db.query(Pedido.descuento)
                  .filter(Pedido.id == PedidoPago.pedido_id)
                  .correlate(PedidoPago)
                  .scalar_subquery()
            ), 0
        ).label("total_descuentos"),
    ).filter(
        PedidoPago.turno_id == turno.id,
        PedidoPago.tenant_id == tenant_id,
        PedidoPago.anulado == False,
    ).first()

    cantidad_pedidos  = fila_pedidos.cantidad_pedidos if fila_pedidos else 0
    total_descuentos  = Decimal(str(fila_pedidos.total_descuentos if fila_pedidos else 0))

    # Query 3: ingresos y egresos manuales en una sola query con CASE
    fila_movs = db.query(
        func.coalesce(
            func.sum(case((CajaMovimiento.tipo == "ingreso", CajaMovimiento.monto), else_=0)), 0
        ).label("ingresos"),
        func.coalesce(
            func.sum(case((CajaMovimiento.tipo == "egreso", CajaMovimiento.monto), else_=0)), 0
        ).label("egresos"),
    ).filter(
        CajaMovimiento.turno_id == turno.id,
        CajaMovimiento.tenant_id == tenant_id,
    ).first()

    mov_ingresos = Decimal(str(fila_movs.ingresos if fila_movs else 0))
    mov_egresos  = Decimal(str(fila_movs.egresos  if fila_movs else 0))

    efectivo_esperado = turno.fondo_inicial + pagos_efectivo + mov_ingresos - mov_egresos

    return TurnoResumen(
        turno_id=turno.id,
        estado=turno.estado,
        fondo_inicial=turno.fondo_inicial,
        abierto_en=turno.abierto_en,
        cerrado_en=turno.cerrado_en,
        desglose_pagos=desglose,
        total_ventas_sistema=total_sistema,
        total_descuentos=total_descuentos,
        total_ingresos_manuales=mov_ingresos,
        total_egresos_manuales=mov_egresos,
        efectivo_esperado_caja=efectivo_esperado,
        efectivo_contado=turno.total_efectivo,
        diferencia_caja=turno.diferencia_caja,
        cantidad_pedidos=cantidad_pedidos,
    )


def _desglose_multi_turno(db: Session, turno_ids: list[int], tenant_id: int):
    """Desglose y totales para múltiples turnos (usado en corte Z)."""
    filas = db.query(
        PedidoPago.forma_pago,
        func.count(PedidoPago.id).label("cantidad"),
        func.coalesce(func.sum(PedidoPago.monto), 0).label("total"),
    ).filter(
        PedidoPago.turno_id.in_(turno_ids),
        PedidoPago.tenant_id == tenant_id,
        PedidoPago.anulado == False,
    ).group_by(PedidoPago.forma_pago).order_by(PedidoPago.forma_pago).all()

    desglose: list[DesglosePago] = []
    ventas_total = Decimal("0")
    for fila in filas:
        total = Decimal(str(fila.total))
        ventas_total += total
        desglose.append(DesglosePago(
            forma_pago_codigo=fila.forma_pago,
            forma_pago_descripcion=_CAT017_DESC.get(fila.forma_pago, fila.forma_pago),
            cantidad_transacciones=fila.cantidad,
            total=total,
        ))
    return desglose, ventas_total


# ── Turno ──────────────────────────────────────────────────────────────────────

@router.get("/turno-actual", response_model=TurnoOut | None)
def turno_actual(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    return db.query(TurnoCaja).filter(
        TurnoCaja.tenant_id == tenant_id,
        TurnoCaja.usuario_id == current_user.id,
        TurnoCaja.estado == "abierto",
    ).first()


@router.get("/turno-actual/resumen", response_model=TurnoResumen)
def resumen_turno_actual(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    turno = db.query(TurnoCaja).filter(
        TurnoCaja.tenant_id == tenant_id,
        TurnoCaja.usuario_id == current_user.id,
        TurnoCaja.estado == "abierto",
    ).first()
    if not turno:
        raise HTTPException(404, "No tienes un turno abierto")
    return _calcular_resumen_turno(db, turno, tenant_id)


@router.post("/abrir-turno", response_model=TurnoOut, status_code=201)
def abrir_turno(
    tenant_id: int,
    data: TurnoAbrirRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    existente = db.query(TurnoCaja).filter(
        TurnoCaja.tenant_id == tenant_id,
        TurnoCaja.usuario_id == current_user.id,
        TurnoCaja.estado == "abierto",
    ).first()
    if existente:
        raise HTTPException(400, "Ya tienes un turno abierto")

    turno = TurnoCaja(
        tenant_id=tenant_id,
        usuario_id=current_user.id,
        fondo_inicial=data.fondo_inicial,
        estado="abierto",
    )
    db.add(turno)
    db.commit()
    db.refresh(turno)
    return turno


@router.post("/cerrar-turno/{turno_id}", response_model=TurnoResumen)
def cerrar_turno(
    tenant_id: int,
    turno_id: int,
    data: TurnoCerrarRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    turno = db.query(TurnoCaja).filter(
        TurnoCaja.id == turno_id,
        TurnoCaja.tenant_id == tenant_id,
        TurnoCaja.usuario_id == current_user.id,
        TurnoCaja.estado == "abierto",
    ).first()
    if not turno:
        raise HTTPException(404, "Turno no encontrado o ya cerrado")

    resumen = _calcular_resumen_turno(db, turno, tenant_id)

    turno.total_ventas     = resumen.total_ventas_sistema
    turno.total_descuentos = resumen.total_descuentos
    turno.total_efectivo   = data.efectivo_contado
    turno.diferencia_caja  = data.efectivo_contado - resumen.efectivo_esperado_caja
    turno.estado           = "cerrado"
    turno.cerrado_en       = datetime.now(timezone.utc)
    turno.observaciones    = data.observaciones

    db.commit()
    db.refresh(turno)
    return _calcular_resumen_turno(db, turno, tenant_id)


@router.get("/turnos", response_model=List[TurnoOut])
def historial_turnos(
    tenant_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    return db.query(TurnoCaja).filter(
        TurnoCaja.tenant_id == tenant_id,
    ).order_by(TurnoCaja.abierto_en.desc()).limit(limit).all()


@router.get("/turnos/{turno_id}", response_model=TurnoOut)
def obtener_turno(
    tenant_id: int,
    turno_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    turno = db.query(TurnoCaja).filter(
        TurnoCaja.id == turno_id,
        TurnoCaja.tenant_id == tenant_id,
    ).first()
    if not turno:
        raise HTTPException(404, "Turno no encontrado")
    return turno


@router.get("/turnos/{turno_id}/resumen", response_model=TurnoResumen)
def resumen_turno(
    tenant_id: int,
    turno_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    turno = db.query(TurnoCaja).filter(
        TurnoCaja.id == turno_id,
        TurnoCaja.tenant_id == tenant_id,
    ).first()
    if not turno:
        raise HTTPException(404, "Turno no encontrado")
    return _calcular_resumen_turno(db, turno, tenant_id)


# ── Movimientos manuales ───────────────────────────────────────────────────────

@router.get("/turnos/{turno_id}/movimientos", response_model=List[MovimientoOut])
def listar_movimientos(
    tenant_id: int,
    turno_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    return db.query(CajaMovimiento).filter(
        CajaMovimiento.turno_id == turno_id,
        CajaMovimiento.tenant_id == tenant_id,
    ).order_by(CajaMovimiento.created_at).all()


@router.post("/turnos/{turno_id}/movimientos", response_model=MovimientoOut, status_code=201)
def registrar_movimiento(
    tenant_id: int,
    turno_id: int,
    data: MovimientoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    turno = db.query(TurnoCaja).filter(
        TurnoCaja.id == turno_id,
        TurnoCaja.tenant_id == tenant_id,
        TurnoCaja.estado == "abierto",
    ).first()
    if not turno:
        raise HTTPException(404, "Turno no encontrado o cerrado")
    if data.tipo not in {"ingreso", "egreso"}:
        raise HTTPException(400, "Tipo debe ser: ingreso o egreso")

    mov = CajaMovimiento(
        tenant_id=tenant_id,
        turno_id=turno_id,
        tipo=data.tipo,
        motivo=data.motivo,
        monto=data.monto,
        referencia=data.referencia,
        notas=data.notas,
        usuario_id=current_user.id,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov


# ── Corte Z ────────────────────────────────────────────────────────────────────

@router.get("/resumen-dia", response_model=ResumenDia)
def resumen_dia(
    tenant_id: int,
    fecha: str | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    if fecha:
        try:
            dia = date.fromisoformat(fecha)
        except ValueError:
            raise HTTPException(400, "Formato de fecha inválido. Use YYYY-MM-DD")
    else:
        dia = date.today()

    turno_ids = [
        t.id for t in db.query(TurnoCaja.id).filter(
            TurnoCaja.tenant_id == tenant_id,
            func.date(TurnoCaja.abierto_en) == dia,
        ).all()
    ]

    if not turno_ids:
        return ResumenDia(
            fecha=dia.isoformat(), cantidad_turnos=0, desglose_pagos=[],
            ventas_total=Decimal("0"), descuentos_total=Decimal("0"), cantidad_pedidos=0,
        )

    desglose, ventas_total = _desglose_multi_turno(db, turno_ids, tenant_id)

    # Descuentos + cantidad de pedidos en 1 query
    fila = db.query(
        func.count(func.distinct(PedidoPago.pedido_id)).label("cantidad_pedidos"),
        func.coalesce(
            func.sum(
                db.query(Pedido.descuento)
                  .filter(Pedido.id == PedidoPago.pedido_id)
                  .correlate(PedidoPago)
                  .scalar_subquery()
            ), 0
        ).label("total_descuentos"),
    ).filter(
        PedidoPago.turno_id.in_(turno_ids),
        PedidoPago.tenant_id == tenant_id,
        PedidoPago.anulado == False,
    ).first()

    return ResumenDia(
        fecha=dia.isoformat(),
        cantidad_turnos=len(turno_ids),
        desglose_pagos=desglose,
        ventas_total=ventas_total,
        descuentos_total=Decimal(str(fila.total_descuentos if fila else 0)),
        cantidad_pedidos=fila.cantidad_pedidos if fila else 0,
    )

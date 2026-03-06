from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel
from datetime import date, datetime

from database import get_db
from models.inventario import (
    Lote, Ubicacion, InventarioStock, InventarioMovimiento, Producto,
)
from auth.deps import get_current_user, get_tenant_user
from models.usuario import Usuario

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["Inventario"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class UbicacionCreate(BaseModel):
    establecimiento_id: int
    nombre: str
    codigo: Optional[str] = None
    tipo: str = "BODEGA"
    padre_id: Optional[int] = None
    permite_picking: bool = True


class UbicacionOut(BaseModel):
    id: int
    establecimiento_id: int
    nombre: str
    codigo: Optional[str] = None
    tipo: str
    padre_id: Optional[int] = None
    permite_picking: bool
    activo: bool
    model_config = {"from_attributes": True}


class LoteCreate(BaseModel):
    producto_id: int
    numero_lote: str
    fecha_fabricacion: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    notas: Optional[str] = None


class LoteOut(BaseModel):
    id: int
    producto_id: int
    numero_lote: str
    fecha_fabricacion: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    notas: Optional[str] = None
    activo: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class StockOut(BaseModel):
    id: int
    producto_id: int
    producto_nombre: str
    producto_codigo: str
    ubicacion_id: int
    ubicacion_nombre: str
    lote_id: Optional[int] = None
    numero_lote: Optional[str] = None
    cantidad: Decimal
    cantidad_reservada: Decimal
    costo_promedio: Optional[Decimal] = None


class AjusteIn(BaseModel):
    producto_id: int
    ubicacion_id: int
    lote_id: Optional[int] = None
    cantidad: Decimal          # positivo = entrada, negativo = salida
    costo_unitario: Decimal = Decimal("0")
    notas: Optional[str] = None


class TransferenciaIn(BaseModel):
    producto_id: int
    ubicacion_origen_id: int
    ubicacion_destino_id: int
    lote_id: Optional[int] = None
    cantidad: Decimal
    notas: Optional[str] = None


class MovimientoOut(BaseModel):
    id: int
    tipo_movimiento: str
    producto_id: int
    ubicacion_origen_id: Optional[int] = None
    ubicacion_destino_id: Optional[int] = None
    lote_id: Optional[int] = None
    cantidad: Decimal
    costo_unitario: Decimal
    notas: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Ubicaciones ────────────────────────────────────────────────────────────────

@router.get("/ubicaciones", response_model=List[UbicacionOut])
def listar_ubicaciones(
    tenant_id: int,
    establecimiento_id: Optional[int] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(Ubicacion).filter(Ubicacion.tenant_id == tenant_id, Ubicacion.activo == True)
    if establecimiento_id:
        q = q.filter(Ubicacion.establecimiento_id == establecimiento_id)
    if tipo:
        q = q.filter(Ubicacion.tipo == tipo.upper())
    return q.order_by(Ubicacion.nombre).all()


@router.post("/ubicaciones", response_model=UbicacionOut, status_code=201)
def crear_ubicacion(
    tenant_id: int,
    data: UbicacionCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    ub = Ubicacion(tenant_id=tenant_id, **data.model_dump())
    db.add(ub)
    db.commit()
    db.refresh(ub)
    return ub


@router.patch("/ubicaciones/{ub_id}", response_model=UbicacionOut)
def actualizar_ubicacion(
    tenant_id: int,
    ub_id: int,
    data: UbicacionCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    ub = db.query(Ubicacion).filter(Ubicacion.id == ub_id, Ubicacion.tenant_id == tenant_id).first()
    if not ub:
        raise HTTPException(404, "Ubicación no encontrada")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(ub, field, val)
    db.commit()
    db.refresh(ub)
    return ub


@router.delete("/ubicaciones/{ub_id}", status_code=204)
def eliminar_ubicacion(
    tenant_id: int,
    ub_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    ub = db.query(Ubicacion).filter(Ubicacion.id == ub_id, Ubicacion.tenant_id == tenant_id).first()
    if not ub:
        raise HTTPException(404, "Ubicación no encontrada")
    stock = db.query(InventarioStock).filter(
        InventarioStock.ubicacion_id == ub_id,
        InventarioStock.cantidad > 0,
    ).first()
    if stock:
        raise HTTPException(409, "No se puede eliminar: la ubicación tiene stock")
    # Desvincular hijos
    db.query(Ubicacion).filter(Ubicacion.padre_id == ub_id).update({"padre_id": None})
    ub.activo = False
    db.commit()


# ── Lotes ─────────────────────────────────────────────────────────────────────

@router.get("/lotes", response_model=List[LoteOut])
def listar_lotes(
    tenant_id: int,
    producto_id: Optional[int] = None,
    solo_activos: bool = True,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    q = db.query(Lote).filter(Lote.tenant_id == tenant_id)
    if solo_activos:
        q = q.filter(Lote.activo == True)
    if producto_id:
        q = q.filter(Lote.producto_id == producto_id)
    return q.order_by(Lote.fecha_vencimiento.asc().nullslast(), Lote.created_at.desc()).all()


@router.post("/lotes", response_model=LoteOut, status_code=201)
def crear_lote(
    tenant_id: int,
    data: LoteCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    # Verificar que el número de lote no exista para el mismo producto
    existe = db.query(Lote).filter(
        Lote.tenant_id == tenant_id,
        Lote.producto_id == data.producto_id,
        Lote.numero_lote == data.numero_lote,
    ).first()
    if existe:
        raise HTTPException(409, f"El lote '{data.numero_lote}' ya existe para este producto")
    lote = Lote(tenant_id=tenant_id, **data.model_dump())
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return lote


@router.patch("/lotes/{lote_id}", response_model=LoteOut)
def actualizar_lote(
    tenant_id: int,
    lote_id: int,
    data: LoteCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    lote = db.query(Lote).filter(Lote.id == lote_id, Lote.tenant_id == tenant_id).first()
    if not lote:
        raise HTTPException(404, "Lote no encontrado")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(lote, field, val)
    db.commit()
    db.refresh(lote)
    return lote


@router.delete("/lotes/{lote_id}", status_code=204)
def eliminar_lote(
    tenant_id: int,
    lote_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    lote = db.query(Lote).filter(Lote.id == lote_id, Lote.tenant_id == tenant_id).first()
    if not lote:
        raise HTTPException(404, "Lote no encontrado")
    stock = db.query(InventarioStock).filter(
        InventarioStock.lote_id == lote_id,
        InventarioStock.cantidad > 0,
    ).first()
    if stock:
        raise HTTPException(409, "No se puede eliminar: el lote tiene stock activo")
    lote.activo = False
    db.commit()


# ── Stock general ──────────────────────────────────────────────────────────────

@router.get("/stock", response_model=List[StockOut])
def stock_general(
    tenant_id: int,
    producto_id: Optional[int] = None,
    ubicacion_id: Optional[int] = None,
    buscar: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    rows = db.execute(text("""
        SELECT
            s.id, s.producto_id, p.nombre AS producto_nombre, p.codigo AS producto_codigo,
            s.ubicacion_id, u.nombre AS ubicacion_nombre,
            s.lote_id, l.numero_lote,
            s.cantidad, s.cantidad_reservada, s.costo_promedio
        FROM inventario_stock s
        JOIN productos p ON p.id = s.producto_id
        JOIN ubicaciones u ON u.id = s.ubicacion_id
        LEFT JOIN lotes l ON l.id = s.lote_id
        WHERE s.tenant_id = :tenant
          AND (:prod IS NULL OR s.producto_id = :prod)
          AND (:ubic IS NULL OR s.ubicacion_id = :ubic)
          AND (:buscar IS NULL OR p.nombre ILIKE :buscar OR p.codigo ILIKE :buscar)
        ORDER BY p.nombre, u.nombre, l.numero_lote
    """), {
        "tenant": tenant_id,
        "prod": producto_id,
        "ubic": ubicacion_id,
        "buscar": f"%{buscar}%" if buscar else None,
    }).fetchall()

    return [StockOut(
        id=r.id, producto_id=r.producto_id,
        producto_nombre=r.producto_nombre, producto_codigo=r.producto_codigo,
        ubicacion_id=r.ubicacion_id, ubicacion_nombre=r.ubicacion_nombre,
        lote_id=r.lote_id, numero_lote=r.numero_lote,
        cantidad=r.cantidad, cantidad_reservada=r.cantidad_reservada,
        costo_promedio=r.costo_promedio,
    ) for r in rows]


# ── Ajuste de inventario ───────────────────────────────────────────────────────

@router.post("/stock/ajuste", response_model=MovimientoOut, status_code=201)
def ajustar_stock(
    tenant_id: int,
    data: AjusteIn,
    db: Session = Depends(get_db),
    tu=Depends(get_tenant_user),
):
    tipo = "AJUSTE_POSITIVO" if data.cantidad > 0 else "AJUSTE_NEGATIVO"
    cantidad_abs = abs(data.cantidad)

    # Verificar stock suficiente para salida
    if data.cantidad < 0:
        stock = db.query(InventarioStock).filter(
            InventarioStock.tenant_id == tenant_id,
            InventarioStock.producto_id == data.producto_id,
            InventarioStock.ubicacion_id == data.ubicacion_id,
            InventarioStock.lote_id == data.lote_id,
        ).first()
        disponible = (stock.cantidad - stock.cantidad_reservada) if stock else Decimal("0")
        if disponible < cantidad_abs:
            raise HTTPException(409, f"Stock insuficiente. Disponible: {disponible}")

    # Crear movimiento
    mov = InventarioMovimiento(
        tenant_id=tenant_id,
        tipo_movimiento=tipo,
        producto_id=data.producto_id,
        ubicacion_destino_id=data.ubicacion_id if data.cantidad > 0 else None,
        ubicacion_origen_id=data.ubicacion_id if data.cantidad < 0 else None,
        lote_id=data.lote_id,
        cantidad=cantidad_abs,
        costo_unitario=data.costo_unitario,
        usuario_id=tu.usuario_id,
        notas=data.notas,
    )
    db.add(mov)
    db.flush()

    # Upsert inventario_stock
    stock = db.query(InventarioStock).filter(
        InventarioStock.tenant_id == tenant_id,
        InventarioStock.producto_id == data.producto_id,
        InventarioStock.ubicacion_id == data.ubicacion_id,
        InventarioStock.lote_id == data.lote_id,
    ).first()

    if stock:
        if data.cantidad > 0:
            # Recalcular costo promedio ponderado
            total_actual = stock.cantidad * (stock.costo_promedio or Decimal("0"))
            total_nuevo  = cantidad_abs * data.costo_unitario
            nuevo_total  = stock.cantidad + cantidad_abs
            stock.costo_promedio = (total_actual + total_nuevo) / nuevo_total if nuevo_total else Decimal("0")
        stock.cantidad += data.cantidad
    else:
        stock = InventarioStock(
            tenant_id=tenant_id,
            producto_id=data.producto_id,
            ubicacion_id=data.ubicacion_id,
            lote_id=data.lote_id,
            cantidad=data.cantidad,
            cantidad_reservada=Decimal("0"),
            costo_promedio=data.costo_unitario,
        )
        db.add(stock)

    db.commit()
    db.refresh(mov)
    return mov


# ── Transferencia entre ubicaciones ───────────────────────────────────────────

@router.post("/stock/transferencia", response_model=List[MovimientoOut], status_code=201)
def transferir_stock(
    tenant_id: int,
    data: TransferenciaIn,
    db: Session = Depends(get_db),
    tu=Depends(get_tenant_user),
):
    if data.ubicacion_origen_id == data.ubicacion_destino_id:
        raise HTTPException(400, "Origen y destino deben ser distintos")

    # Verificar stock en origen
    stock_origen = db.query(InventarioStock).filter(
        InventarioStock.tenant_id == tenant_id,
        InventarioStock.producto_id == data.producto_id,
        InventarioStock.ubicacion_id == data.ubicacion_origen_id,
        InventarioStock.lote_id == data.lote_id,
    ).first()

    disponible = (stock_origen.cantidad - stock_origen.cantidad_reservada) if stock_origen else Decimal("0")
    if disponible < data.cantidad:
        raise HTTPException(409, f"Stock insuficiente en origen. Disponible: {disponible}")

    costo = stock_origen.costo_promedio or Decimal("0")

    # Movimiento salida
    sal = InventarioMovimiento(
        tenant_id=tenant_id,
        tipo_movimiento="TRANSFERENCIA_SALIDA",
        producto_id=data.producto_id,
        ubicacion_origen_id=data.ubicacion_origen_id,
        lote_id=data.lote_id,
        cantidad=data.cantidad,
        costo_unitario=costo,
        usuario_id=tu.usuario_id,
        notas=data.notas,
    )
    db.add(sal)

    # Movimiento entrada
    ent = InventarioMovimiento(
        tenant_id=tenant_id,
        tipo_movimiento="TRANSFERENCIA_ENTRADA",
        producto_id=data.producto_id,
        ubicacion_destino_id=data.ubicacion_destino_id,
        lote_id=data.lote_id,
        cantidad=data.cantidad,
        costo_unitario=costo,
        usuario_id=tu.usuario_id,
        notas=data.notas,
    )
    db.add(ent)
    db.flush()

    # Actualizar stock origen
    stock_origen.cantidad -= data.cantidad

    # Upsert stock destino
    stock_destino = db.query(InventarioStock).filter(
        InventarioStock.tenant_id == tenant_id,
        InventarioStock.producto_id == data.producto_id,
        InventarioStock.ubicacion_id == data.ubicacion_destino_id,
        InventarioStock.lote_id == data.lote_id,
    ).first()

    if stock_destino:
        total_actual = stock_destino.cantidad * (stock_destino.costo_promedio or Decimal("0"))
        total_nuevo  = data.cantidad * costo
        nuevo_total  = stock_destino.cantidad + data.cantidad
        stock_destino.costo_promedio = (total_actual + total_nuevo) / nuevo_total if nuevo_total else Decimal("0")
        stock_destino.cantidad += data.cantidad
    else:
        stock_destino = InventarioStock(
            tenant_id=tenant_id,
            producto_id=data.producto_id,
            ubicacion_id=data.ubicacion_destino_id,
            lote_id=data.lote_id,
            cantidad=data.cantidad,
            cantidad_reservada=Decimal("0"),
            costo_promedio=costo,
        )
        db.add(stock_destino)

    db.commit()
    db.refresh(sal)
    db.refresh(ent)
    return [sal, ent]


# ── Historial de movimientos ───────────────────────────────────────────────────

@router.get("/stock/movimientos", response_model=List[dict])
def historial_movimientos(
    tenant_id: int,
    producto_id: Optional[int] = None,
    ubicacion_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    rows = db.execute(text("""
        SELECT
            m.id, m.tipo_movimiento, m.cantidad, m.costo_unitario, m.notas, m.created_at,
            p.nombre AS producto_nombre, p.codigo AS producto_codigo,
            uo.nombre AS ubicacion_origen, ud.nombre AS ubicacion_destino,
            l.numero_lote
        FROM inventario_movimientos m
        JOIN productos p ON p.id = m.producto_id
        LEFT JOIN ubicaciones uo ON uo.id = m.ubicacion_origen_id
        LEFT JOIN ubicaciones ud ON ud.id = m.ubicacion_destino_id
        LEFT JOIN lotes l ON l.id = m.lote_id
        WHERE m.tenant_id = :tenant
          AND (:prod IS NULL OR m.producto_id = :prod)
          AND (:ubic IS NULL OR m.ubicacion_origen_id = :ubic OR m.ubicacion_destino_id = :ubic)
        ORDER BY m.created_at DESC
        LIMIT :limit
    """), {"tenant": tenant_id, "prod": producto_id, "ubic": ubicacion_id, "limit": limit}).fetchall()

    return [dict(r._mapping) for r in rows]

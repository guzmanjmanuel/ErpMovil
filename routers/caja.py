from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from database import get_db
from models.caja import TurnoCaja, CajaMovimiento
from schemas.caja import (
    TurnoAbrirRequest, TurnoCerrarRequest, TurnoOut,
    MovimientoCreate, MovimientoOut,
)
from auth.deps import get_current_user, get_tenant_user
from models.usuario import Usuario

router = APIRouter(prefix="/tenants/{tenant_id}/caja", tags=["Caja"])


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


@router.post("/cerrar-turno/{turno_id}", response_model=TurnoOut)
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

    turno.estado = "cerrado"
    turno.cerrado_en = datetime.now(timezone.utc)
    turno.total_efectivo = data.total_efectivo
    turno.total_tarjeta = data.total_tarjeta
    turno.total_qr = data.total_qr
    turno.observaciones = data.observaciones

    total_declarado = (data.total_efectivo or 0) + (data.total_tarjeta or 0) + (data.total_qr or 0)
    turno.total_ventas = total_declarado

    db.commit()
    db.refresh(turno)
    return turno


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


# ── Movimientos ───────────────────────────────────────────────────────────────

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
        concepto=data.concepto,
        monto=data.monto,
        usuario_id=current_user.id,
    )
    db.add(mov)
    db.commit()
    db.refresh(mov)
    return mov

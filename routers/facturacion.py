from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import date

from database import get_db
from models.dte import (
    DteIdentificacion, DteItem, DteResumen,
    DteResumenPago, DteTipo, DteAuditLog, MhAnulacion,
)
from models.contribuyente import Contribuyente
from schemas.dte import (
    DteCreate, DteOut, DteListItem, DteItemOut,
    DteResumenOut, DtePagoOut, DteTipoOut, AnulacionCreate,
)
from services.dte_service import crear_dte, emitir_dte
from auth.deps import get_current_user, get_tenant_user
from models.usuario import Usuario

router = APIRouter(prefix="/tenants/{tenant_id}/facturacion", tags=["Facturación DTE"])


# ── Catálogos ─────────────────────────────────────────────────────────────────

@router.get("/tipos-dte", response_model=List[DteTipoOut])
def tipos_dte(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    return db.query(DteTipo).all()


@router.get("/emisor", summary="Datos del emisor configurado para este tenant")
def obtener_emisor(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    row = db.execute(
        text("SELECT * FROM v_emisores WHERE tenant_id = :t LIMIT 1"),
        {"t": tenant_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, "Emisor no configurado para este tenant")
    return dict(row._mapping)


# ── CRUD DTEs ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[DteListItem])
def listar_dtes(
    tenant_id: int,
    tipo_dte: Optional[str] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    rows = db.execute(
        text("""
            SELECT
                d.id, d.tipo_dte, d.numero_control, d.codigo_generacion,
                d.fec_emi, d.estado, d.created_at,
                rc.nombre  AS receptor_nombre,
                rc.nit     AS receptor_nit,
                r.monto_total_operacion,
                r.total_pagar
            FROM dte_identificacion d
            LEFT JOIN contribuyentes rc ON rc.id = d.receptor_id
            LEFT JOIN dte_resumen r ON r.dte_id = d.id
            WHERE d.tenant_id = :t
              AND (:tipo   IS NULL OR d.tipo_dte = :tipo)
              AND (:estado IS NULL OR d.estado   = :estado)
              AND (:desde  IS NULL OR d.fec_emi >= :desde)
              AND (:hasta  IS NULL OR d.fec_emi <= :hasta)
            ORDER BY d.id DESC
            LIMIT :lim
        """),
        {
            "t": tenant_id,
            "tipo": tipo_dte,
            "estado": estado,
            "desde": fecha_desde,
            "hasta": fecha_hasta,
            "lim": limit,
        },
    ).fetchall()
    return [DteListItem(**dict(r._mapping)) for r in rows]


@router.get("/{dte_id}", response_model=DteOut)
def obtener_dte(
    tenant_id: int,
    dte_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    dte = db.query(DteIdentificacion).filter(
        DteIdentificacion.id == dte_id,
        DteIdentificacion.tenant_id == tenant_id,
    ).first()
    if not dte:
        raise HTTPException(404, "DTE no encontrado")

    tipo_desc = db.query(DteTipo).filter(DteTipo.codigo == dte.tipo_dte).first()
    items = db.query(DteItem).filter(DteItem.dte_id == dte_id).order_by(DteItem.num_item).all()
    resumen = db.query(DteResumen).filter(DteResumen.dte_id == dte_id).first()
    pagos = db.query(DteResumenPago).filter(
        DteResumenPago.resumen_id == resumen.id
    ).all() if resumen else []

    out = DteOut.model_validate(dte)
    out.tipo_dte_desc = tipo_desc.descripcion if tipo_desc else None
    out.items = [DteItemOut.model_validate(i) for i in items]
    out.resumen = DteResumenOut.model_validate(resumen) if resumen else None
    out.pagos = [DtePagoOut.model_validate(p) for p in pagos]
    return out


@router.post("", response_model=DteOut, status_code=201)
def crear_nuevo_dte(
    tenant_id: int,
    data: DteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    # Obtener emisor del tenant
    emisor_row = db.execute(
        text("SELECT id FROM v_emisores WHERE tenant_id = :t LIMIT 1"),
        {"t": tenant_id},
    ).fetchone()
    if not emisor_row:
        raise HTTPException(400, "El tenant no tiene emisor configurado")

    emisor_id = emisor_row[0]

    dte = crear_dte(db, tenant_id, current_user.id, data, emisor_id)
    return obtener_dte(tenant_id, dte.id, db, _)


@router.post("/{dte_id}/emitir", response_model=DteOut)
def emitir(
    tenant_id: int,
    dte_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    dte = db.query(DteIdentificacion).filter(
        DteIdentificacion.id == dte_id,
        DteIdentificacion.tenant_id == tenant_id,
    ).first()
    if not dte:
        raise HTTPException(404, "DTE no encontrado")

    dte = emitir_dte(db, tenant_id, current_user.id, dte)
    return obtener_dte(tenant_id, dte.id, db, _)


@router.post("/{dte_id}/anular", response_model=dict, status_code=202)
def anular_dte(
    tenant_id: int,
    dte_id: int,
    data: AnulacionCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
    _=Depends(get_tenant_user),
):
    dte = db.query(DteIdentificacion).filter(
        DteIdentificacion.id == dte_id,
        DteIdentificacion.tenant_id == tenant_id,
    ).first()
    if not dte:
        raise HTTPException(404, "DTE no encontrado")
    if dte.estado not in ("EMITIDO", "RECIBIDO"):
        raise HTTPException(400, f"No se puede anular un DTE en estado '{dte.estado}'")

    anulacion = MhAnulacion(
        tenant_id=tenant_id,
        dte_id=dte_id,
        motivo_anulacion=data.motivo_anulacion,
        nombre_responsable=data.nombre_responsable,
        tipo_doc_responsable=data.tipo_doc_responsable,
        num_doc_responsable=data.num_doc_responsable,
        nombre_solicita=data.nombre_solicita,
        tipo_doc_solicita=data.tipo_doc_solicita,
        num_doc_solicita=data.num_doc_solicita,
        estado="pendiente",
    )
    db.add(anulacion)

    dte.estado = "ANULADO"
    db.add(DteAuditLog(
        tenant_id=tenant_id,
        dte_id=dte_id,
        accion="ANULAR",
        usuario_id=current_user.id,
        detalle={"motivo": data.motivo_anulacion},
    ))

    db.commit()
    return {"mensaje": "Solicitud de anulación registrada", "dte_id": dte_id, "estado": "ANULADO"}


@router.get("/{dte_id}/auditoria", response_model=List[dict])
def auditoria_dte(
    tenant_id: int,
    dte_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    logs = db.query(DteAuditLog).filter(
        DteAuditLog.dte_id == dte_id,
        DteAuditLog.tenant_id == tenant_id,
    ).order_by(DteAuditLog.created_at).all()
    return [
        {
            "id": l.id,
            "accion": l.accion,
            "usuario_id": l.usuario_id,
            "detalle": l.detalle,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


# ── Estadísticas ──────────────────────────────────────────────────────────────

@router.get("/estadisticas/resumen", summary="Totales de facturación por tipo y estado")
def estadisticas(
    tenant_id: int,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    rows = db.execute(
        text("""
            SELECT
                d.tipo_dte,
                t.descripcion        AS tipo_desc,
                d.estado,
                COUNT(*)             AS cantidad,
                SUM(r.total_pagar)   AS total_facturado
            FROM dte_identificacion d
            JOIN dte_tipos t ON t.codigo = d.tipo_dte
            LEFT JOIN dte_resumen r ON r.dte_id = d.id
            WHERE d.tenant_id = :tenant
              AND (:desde IS NULL OR d.fec_emi >= :desde)
              AND (:hasta IS NULL OR d.fec_emi <= :hasta)
            GROUP BY d.tipo_dte, t.descripcion, d.estado
            ORDER BY d.tipo_dte, d.estado
        """),
        {"tenant": tenant_id, "desde": fecha_desde, "hasta": fecha_hasta},
    ).fetchall()
    return [dict(r._mapping) for r in rows]

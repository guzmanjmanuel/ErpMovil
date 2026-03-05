import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from database import get_db
from models.tenant import Tenant
from models.usuario import Usuario, TenantUsuario
from models.contribuyente import Contribuyente, EmisorDetalle

router = APIRouter(prefix="/tenants", tags=["Tenants"])


class EmisorIn(BaseModel):
    nombre: str
    nombre_comercial: Optional[str] = None
    nit: Optional[str] = None
    nrc: Optional[str] = None
    cod_actividad: Optional[str] = None
    desc_actividad: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    # Detalle establecimiento DTE El Salvador
    tipo_establecimiento: str = "02"       # 01=Sucursal 02=Casa Matriz 20=Virtual
    cod_estable_mh: Optional[str] = None
    cod_estable: Optional[str] = None
    cod_punto_venta_mh: Optional[str] = None
    cod_punto_venta: Optional[str] = None
    regimen: str = "GEN"                   # GEN | EXE | EXP


class EmisorOut(BaseModel):
    contribuyente_id: int
    nombre: str
    nombre_comercial: Optional[str] = None
    nit: Optional[str] = None
    nrc: Optional[str] = None
    cod_actividad: Optional[str] = None
    desc_actividad: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    tipo_establecimiento: Optional[str] = None
    cod_estable_mh: Optional[str] = None
    cod_estable: Optional[str] = None
    cod_punto_venta_mh: Optional[str] = None
    cod_punto_venta: Optional[str] = None
    regimen: Optional[str] = None


class TenantCreate(BaseModel):
    nombre: str
    tipo: str = "restaurante"   # restaurante | pos
    plan: str = "profesional"   # basico | profesional | enterprise
    admin_nombre: str
    admin_email: EmailStr
    admin_password: str


class TenantListOut(BaseModel):
    id: int
    nombre: str
    tipo: str
    plan: str
    ambiente: str = "00"
    activo: bool
    total_usuarios: int = 0

    model_config = {"from_attributes": True}


@router.get("", response_model=List[TenantListOut])
def listar_tenants(db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT t.id, t.nombre, t.tipo, t.plan, t.ambiente, t.activo,
               COUNT(tu.usuario_id) AS total_usuarios
        FROM tenants t
        LEFT JOIN tenant_usuarios tu ON tu.tenant_id = t.id AND tu.activo = true
        GROUP BY t.id
        ORDER BY t.nombre
    """)).fetchall()

    return [
        TenantListOut(
            id=r.id, nombre=r.nombre, tipo=r.tipo, plan=r.plan,
            ambiente=r.ambiente, activo=r.activo, total_usuarios=r.total_usuarios,
        )
        for r in rows
    ]


@router.post("", response_model=TenantListOut, status_code=201)
def crear_tenant(data: TenantCreate, db: Session = Depends(get_db)):
    if data.tipo not in ("restaurante", "pos"):
        raise HTTPException(400, "tipo debe ser 'restaurante' o 'pos'")
    if data.plan not in ("basico", "profesional", "enterprise"):
        raise HTTPException(400, "plan debe ser 'basico', 'profesional' o 'enterprise'")

    tenant = Tenant(nombre=data.nombre, tipo=data.tipo, plan=data.plan, activo=True)
    db.add(tenant)
    db.flush()

    # Buscar o crear el usuario admin
    usuario = db.query(Usuario).filter(Usuario.email == data.admin_email).first()
    if not usuario:
        pw_hash = bcrypt.hashpw(data.admin_password.encode(), bcrypt.gensalt()).decode()
        usuario = Usuario(
            email=data.admin_email,
            password_hash=pw_hash,
            nombre=data.admin_nombre,
            activo=True,
        )
        db.add(usuario)
        db.flush()

    tu = TenantUsuario(tenant_id=tenant.id, usuario_id=usuario.id, rol="admin", activo=True)
    db.add(tu)
    db.commit()
    db.refresh(tenant)

    return TenantListOut(
        id=tenant.id, nombre=tenant.nombre, tipo=tenant.tipo,
        plan=tenant.plan, activo=tenant.activo, total_usuarios=1,
    )


@router.get("/{tenant_id}/emisor", response_model=EmisorOut)
def obtener_emisor(tenant_id: int, db: Session = Depends(get_db)):
    c = db.query(Contribuyente).filter(
        Contribuyente.tenant_id == tenant_id,
        Contribuyente.tipo == "emisor",
        Contribuyente.activo == True,
    ).first()
    if not c:
        raise HTTPException(404, "Emisor no configurado")

    det = db.query(EmisorDetalle).filter(
        EmisorDetalle.contribuyente_id == c.id,
        EmisorDetalle.tenant_id == tenant_id,
    ).first()

    return EmisorOut(
        contribuyente_id=c.id,
        nombre=c.nombre,
        nombre_comercial=c.nombre_comercial,
        nit=c.nit,
        nrc=c.nrc,
        cod_actividad=c.cod_actividad,
        desc_actividad=c.desc_actividad,
        telefono=c.telefono,
        correo=c.correo,
        tipo_establecimiento=det.tipo_establecimiento if det else None,
        cod_estable_mh=det.cod_estable_mh if det else None,
        cod_estable=det.cod_estable if det else None,
        cod_punto_venta_mh=det.cod_punto_venta_mh if det else None,
        cod_punto_venta=det.cod_punto_venta if det else None,
        regimen=det.regimen if det else None,
    )


def _solo_digitos(val: str | None) -> str | None:
    """Elimina guiones y espacios, retorna None si queda vacío."""
    if val is None:
        return None
    limpio = val.replace("-", "").replace(" ", "")
    return limpio if limpio else None


@router.post("/{tenant_id}/emisor", response_model=EmisorOut)
def guardar_emisor(tenant_id: int, data: EmisorIn, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Tenant no encontrado")

    nit = _solo_digitos(data.nit)
    nrc = _solo_digitos(data.nrc)

    if not nit:
        raise HTTPException(400, "El NIT es obligatorio para el emisor")
    if len(nit) not in (9, 14):
        raise HTTPException(400, f"NIT inválido: debe tener 9 o 14 dígitos (sin guiones). Recibido: '{nit}' ({len(nit)} dígitos)")
    if nrc and not (1 <= len(nrc) <= 8):
        raise HTTPException(400, f"NRC inválido: debe tener 1-8 dígitos (sin guiones). Recibido: '{nrc}'")

    # Crear o actualizar contribuyente emisor
    c = db.query(Contribuyente).filter(
        Contribuyente.tenant_id == tenant_id,
        Contribuyente.tipo == "emisor",
    ).first()

    if not c:
        c = Contribuyente(tenant_id=tenant_id, tipo="emisor", activo=True)
        db.add(c)

    c.nombre = data.nombre
    c.nombre_comercial = data.nombre_comercial
    c.nit = nit
    c.nrc = nrc
    c.cod_actividad = data.cod_actividad
    c.desc_actividad = data.desc_actividad
    c.telefono = data.telefono
    c.correo = data.correo
    db.flush()

    # Crear o actualizar detalle del establecimiento
    det = db.query(EmisorDetalle).filter(
        EmisorDetalle.contribuyente_id == c.id,
        EmisorDetalle.tenant_id == tenant_id,
    ).first()

    if not det:
        det = EmisorDetalle(contribuyente_id=c.id, tenant_id=tenant_id)
        db.add(det)

    det.tipo_establecimiento = data.tipo_establecimiento
    det.cod_estable_mh = data.cod_estable_mh
    det.cod_estable = data.cod_estable
    det.cod_punto_venta_mh = data.cod_punto_venta_mh
    det.cod_punto_venta = data.cod_punto_venta
    det.regimen = data.regimen
    db.commit()
    db.refresh(c)

    return EmisorOut(
        contribuyente_id=c.id,
        nombre=c.nombre,
        nombre_comercial=c.nombre_comercial,
        nit=c.nit,
        nrc=c.nrc,
        cod_actividad=c.cod_actividad,
        desc_actividad=c.desc_actividad,
        telefono=c.telefono,
        correo=c.correo,
        tipo_establecimiento=det.tipo_establecimiento,
        cod_estable_mh=det.cod_estable_mh,
        cod_estable=det.cod_estable,
        cod_punto_venta_mh=det.cod_punto_venta_mh,
        cod_punto_venta=det.cod_punto_venta,
        regimen=det.regimen,
    )


@router.patch("/{tenant_id}/ambiente", response_model=TenantListOut)
def cambiar_ambiente(tenant_id: int, db: Session = Depends(get_db)):
    """Alterna entre 00=prueba y 01=produccion (CAT-001)."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Negocio no encontrado")
    tenant.ambiente = "01" if tenant.ambiente == "00" else "00"
    db.commit()
    total = db.execute(
        text("SELECT COUNT(*) FROM tenant_usuarios WHERE tenant_id=:t AND activo=true"),
        {"t": tenant_id},
    ).scalar()
    return TenantListOut(
        id=tenant.id, nombre=tenant.nombre, tipo=tenant.tipo, plan=tenant.plan,
        ambiente=tenant.ambiente, activo=tenant.activo, total_usuarios=total,
    )


@router.patch("/{tenant_id}/toggle", response_model=TenantListOut)
def toggle_tenant(tenant_id: int, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Negocio no encontrado")
    tenant.activo = not tenant.activo
    db.commit()
    db.refresh(tenant)
    total = db.execute(
        text("SELECT COUNT(*) FROM tenant_usuarios WHERE tenant_id=:t AND activo=true"),
        {"t": tenant_id},
    ).scalar()
    return TenantListOut(
        id=tenant.id, nombre=tenant.nombre, tipo=tenant.tipo, plan=tenant.plan,
        ambiente=tenant.ambiente, activo=tenant.activo, total_usuarios=total,
    )

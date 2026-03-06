import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from database import get_db
from models.usuario import Usuario, TenantUsuario
from models.tenant import Tenant
from schemas.auth import LoginRequest, TokenResponse, UsuarioOut
from auth.jwt import crear_token
from auth.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])

SUPERADMIN_ROL = "superadmin"


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _permisos_del_usuario(db: Session, tenant_id: int, usuario_id: int, rol: str) -> list[str]:
    base = db.execute(
        text("SELECT p.codigo FROM rol_permisos rp JOIN permisos p ON p.id = rp.permiso_id WHERE rp.rol_id = :r"),
        {"r": rol},
    ).fetchall()
    permisos = {r[0] for r in base}

    overrides = db.execute(
        text("""
            SELECT p.codigo, tup.concedido
            FROM tenant_usuario_permisos tup
            JOIN permisos p ON p.id = tup.permiso_id
            WHERE tup.tenant_id = :t AND tup.usuario_id = :u
        """),
        {"t": tenant_id, "u": usuario_id},
    ).fetchall()

    for cod, concedido in overrides:
        if concedido:
            permisos.add(cod)
        else:
            permisos.discard(cod)

    return sorted(permisos)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(
        Usuario.email == data.email,
        Usuario.activo == True,
    ).first()

    if not usuario or not _verify_password(data.password, usuario.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")

    # ── Flujo superadmin ──────────────────────────────────────────────────────
    if usuario.is_superadmin:
        if not data.tenant_id:
            # Sin tenant_id: devuelve token sin tenant para que el frontend
            # muestre el selector de negocios.
            token = crear_token({
                "sub": usuario.id,
                "tenant_id": None,
                "rol": SUPERADMIN_ROL,
                "is_superadmin": True,
                "establecimiento_id": None,
            })
            return TokenResponse(
                access_token=token,
                usuario_id=usuario.id,
                nombre=usuario.nombre,
                email=usuario.email,
                rol=SUPERADMIN_ROL,
                tenant_id=None,
                tipo_negocio="restaurante",
                is_superadmin=True,
                permisos=[],
            )

        tenant = db.query(Tenant).filter(Tenant.id == data.tenant_id, Tenant.activo == True).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Negocio no encontrado")

        permisos = _permisos_del_usuario(db, data.tenant_id, usuario.id, "admin")
        token = crear_token({
            "sub": usuario.id,
            "tenant_id": data.tenant_id,
            "rol": SUPERADMIN_ROL,
            "is_superadmin": True,
            "establecimiento_id": None,
        })
        return TokenResponse(
            access_token=token,
            usuario_id=usuario.id,
            nombre=usuario.nombre,
            email=usuario.email,
            rol=SUPERADMIN_ROL,
            tenant_id=data.tenant_id,
            tipo_negocio=tenant.tipo,
            is_superadmin=True,
            permisos=permisos,
        )

    # ── Flujo normal ──────────────────────────────────────────────────────────
    if not data.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="tenant_id requerido")

    tu = db.query(TenantUsuario).filter(
        TenantUsuario.tenant_id == data.tenant_id,
        TenantUsuario.usuario_id == usuario.id,
        TenantUsuario.activo == True,
    ).first()

    if not tu:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a este negocio")

    tenant = db.query(Tenant).filter(Tenant.id == data.tenant_id).first()
    tipo_negocio = tenant.tipo if tenant else "restaurante"

    permisos = _permisos_del_usuario(db, data.tenant_id, usuario.id, tu.rol)
    token = crear_token({
        "sub": usuario.id,
        "tenant_id": data.tenant_id,
        "rol": tu.rol,
        "is_superadmin": False,
        "establecimiento_id": tu.establecimiento_id,
    })

    return TokenResponse(
        access_token=token,
        usuario_id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        rol=tu.rol,
        tenant_id=data.tenant_id,
        tipo_negocio=tipo_negocio,
        is_superadmin=False,
        establecimiento_id=tu.establecimiento_id,
        permisos=permisos,
    )


@router.get("/tenants", response_model=List[dict])
def listar_tenants_superadmin(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Solo accesible por superadmins. Devuelve todos los tenants activos."""
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Solo superadmins")
    tenants = db.query(Tenant).filter(Tenant.activo == True).order_by(Tenant.nombre).all()
    return [{"id": t.id, "nombre": t.nombre, "tipo": t.tipo} for t in tenants]


@router.get("/me", response_model=UsuarioOut)
def me(current_user: Usuario = Depends(get_current_user)):
    return current_user

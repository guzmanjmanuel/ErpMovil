import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from models.usuario import Usuario, TenantUsuario
from models.tenant import Tenant
from schemas.auth import LoginRequest, TokenResponse, UsuarioOut
from auth.jwt import crear_token
from auth.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


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
        establecimiento_id=tu.establecimiento_id,
        permisos=permisos,
    )


@router.get("/me", response_model=UsuarioOut)
def me(current_user: Usuario = Depends(get_current_user)):
    return current_user

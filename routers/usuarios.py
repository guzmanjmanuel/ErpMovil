import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from database import get_db
from models.usuario import Usuario, TenantUsuario
from models.tenant import Tenant
from models.rol import Rol, Permiso, RolPermiso, TenantUsuarioPermiso
from models.establecimiento import Establecimiento
from schemas.usuarios import (
    UsuarioCreate, UsuarioUpdate, UsuarioTenantOut,
    RolOut, PermisoOut, TenantOut, TenantUpdate,
)
from auth.deps import get_current_user, get_tenant_user, require_rol

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["Usuarios y Roles"])


def _permisos_del_rol(db: Session, rol: str) -> List[str]:
    rows = db.execute(
        text("SELECT p.codigo FROM rol_permisos rp JOIN permisos p ON p.id = rp.permiso_id WHERE rp.rol_id = :r"),
        {"r": rol},
    ).fetchall()
    return [r[0] for r in rows]


def _permisos_efectivos(db: Session, tenant_id: int, usuario_id: int, rol: str) -> List[str]:
    """Permisos del rol + overrides individuales."""
    base = set(_permisos_del_rol(db, rol))

    overrides = db.execute(
        text("""
            SELECT p.codigo, tup.concedido
            FROM tenant_usuario_permisos tup
            JOIN permisos p ON p.id = tup.permiso_id
            WHERE tup.tenant_id = :t AND tup.usuario_id = :u
        """),
        {"t": tenant_id, "u": usuario_id},
    ).fetchall()

    for codigo, concedido in overrides:
        if concedido:
            base.add(codigo)
        else:
            base.discard(codigo)

    return sorted(base)


# ── Tenant ────────────────────────────────────────────────────────────────────

@router.get("/info", response_model=TenantOut)
def info_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(404, "Tenant no encontrado")
    return t


@router.patch("/info", response_model=TenantOut)
def actualizar_tenant(
    tenant_id: int,
    data: TenantUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_rol("admin")),
):
    t = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not t:
        raise HTTPException(404, "Tenant no encontrado")
    if data.nombre is not None:
        t.nombre = data.nombre
    if data.tipo is not None:
        if data.tipo not in ("restaurante", "pos"):
            raise HTTPException(400, "tipo debe ser 'restaurante' o 'pos'")
        t.tipo = data.tipo
    db.commit()
    db.refresh(t)
    return t


# ── Roles ─────────────────────────────────────────────────────────────────────

@router.get("/roles", response_model=List[RolOut])
def listar_roles(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    tipo = tenant.tipo if tenant else "ambos"

    roles = db.query(Rol).filter(
        Rol.activo == True,
        Rol.tipo_negocio.in_([tipo, "ambos"]),
    ).all()

    result = []
    for r in roles:
        permisos = _permisos_del_rol(db, r.nombre)
        result.append(RolOut(
            id=r.id,
            nombre=r.nombre,
            descripcion=r.descripcion,
            tipo_negocio=r.tipo_negocio,
            permisos=permisos,
        ))
    return result


@router.get("/permisos", response_model=List[PermisoOut])
def listar_permisos(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    return db.query(Permiso).order_by(Permiso.modulo, Permiso.accion).all()


# ── Usuarios del tenant ───────────────────────────────────────────────────────

@router.get("/usuarios", response_model=List[UsuarioTenantOut])
def listar_usuarios(
    tenant_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    rows = db.execute(
        text("""
            SELECT u.id, u.email, u.nombre, u.activo, u.created_at,
                   tu.rol, tu.establecimiento_id, e.nombre AS establecimiento_nombre
            FROM tenant_usuarios tu
            JOIN usuarios u ON u.id = tu.usuario_id
            LEFT JOIN establecimientos e ON e.id = tu.establecimiento_id
            WHERE tu.tenant_id = :t
            ORDER BY u.nombre
        """),
        {"t": tenant_id},
    ).fetchall()

    result = []
    for r in rows:
        permisos = _permisos_efectivos(db, tenant_id, r.id, r.rol)
        result.append(UsuarioTenantOut(
            id=r.id,
            email=r.email,
            nombre=r.nombre,
            activo=r.activo,
            rol=r.rol,
            establecimiento_id=r.establecimiento_id,
            establecimiento_nombre=r.establecimiento_nombre,
            permisos=permisos,
            created_at=r.created_at,
        ))
    return result


@router.get("/usuarios/{usuario_id}", response_model=UsuarioTenantOut)
def obtener_usuario(
    tenant_id: int,
    usuario_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    row = db.execute(
        text("""
            SELECT u.id, u.email, u.nombre, u.activo, u.created_at, tu.rol
            FROM tenant_usuarios tu
            JOIN usuarios u ON u.id = tu.usuario_id
            WHERE tu.tenant_id = :t AND u.id = :u
        """),
        {"t": tenant_id, "u": usuario_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, "Usuario no encontrado en este tenant")

    permisos = _permisos_efectivos(db, tenant_id, row.id, row.rol)
    return UsuarioTenantOut(
        id=row.id, email=row.email, nombre=row.nombre,
        activo=row.activo, rol=row.rol, permisos=permisos,
        created_at=row.created_at,
    )


@router.post("/usuarios", response_model=UsuarioTenantOut, status_code=201)
def crear_usuario(
    tenant_id: int,
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    # Validar rol
    roles_validos = {"admin","supervisor","cajero","mesero","cocinero","vendedor","consulta"}
    if data.rol not in roles_validos:
        raise HTTPException(400, f"Rol inválido. Opciones: {', '.join(sorted(roles_validos))}")

    # Email duplicado global
    existente = db.query(Usuario).filter(Usuario.email == data.email).first()
    if existente:
        # Si ya existe, solo vincular al tenant si no está ya vinculado
        tu = db.query(TenantUsuario).filter(
            TenantUsuario.tenant_id == tenant_id,
            TenantUsuario.usuario_id == existente.id,
        ).first()
        if tu:
            raise HTTPException(409, "El usuario ya pertenece a este negocio")
        tu = TenantUsuario(tenant_id=tenant_id, usuario_id=existente.id, rol=data.rol,
                           activo=True, establecimiento_id=data.establecimiento_id)
        db.add(tu)
        db.commit()
        usuario = existente
    else:
        pw_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
        usuario = Usuario(email=data.email, password_hash=pw_hash, nombre=data.nombre, activo=True)
        db.add(usuario)
        db.flush()
        tu = TenantUsuario(tenant_id=tenant_id, usuario_id=usuario.id, rol=data.rol,
                           activo=True, establecimiento_id=data.establecimiento_id)
        db.add(tu)
        db.commit()

    db.refresh(usuario)
    estab = db.query(Establecimiento).filter(Establecimiento.id == data.establecimiento_id).first() if data.establecimiento_id else None
    permisos = _permisos_efectivos(db, tenant_id, usuario.id, data.rol)
    return UsuarioTenantOut(
        id=usuario.id, email=usuario.email, nombre=usuario.nombre,
        activo=usuario.activo, rol=data.rol,
        establecimiento_id=data.establecimiento_id,
        establecimiento_nombre=estab.nombre if estab else None,
        permisos=permisos, created_at=usuario.created_at,
    )


@router.patch("/usuarios/{usuario_id}", response_model=UsuarioTenantOut)
def actualizar_usuario(
    tenant_id: int,
    usuario_id: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    tu = db.query(TenantUsuario).filter(
        TenantUsuario.tenant_id == tenant_id,
        TenantUsuario.usuario_id == usuario_id,
    ).first()
    if not tu:
        raise HTTPException(404, "Usuario no encontrado en este tenant")

    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

    if data.nombre is not None:
        usuario.nombre = data.nombre
    if data.email is not None:
        usuario.email = data.email
    if data.password is not None:
        usuario.password_hash = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    if data.activo is not None:
        usuario.activo = data.activo
        tu.activo = data.activo
    if data.rol is not None:
        roles_validos = {"admin","supervisor","cajero","mesero","cocinero","vendedor","consulta"}
        if data.rol not in roles_validos:
            raise HTTPException(400, f"Rol inválido. Opciones: {', '.join(sorted(roles_validos))}")
        tu.rol = data.rol
    if "establecimiento_id" in data.model_fields_set:
        tu.establecimiento_id = data.establecimiento_id

    db.commit()
    db.refresh(usuario)

    estab = db.query(Establecimiento).filter(Establecimiento.id == tu.establecimiento_id).first() if tu.establecimiento_id else None
    permisos = _permisos_efectivos(db, tenant_id, usuario.id, tu.rol)
    return UsuarioTenantOut(
        id=usuario.id, email=usuario.email, nombre=usuario.nombre,
        activo=usuario.activo, rol=tu.rol,
        establecimiento_id=tu.establecimiento_id,
        establecimiento_nombre=estab.nombre if estab else None,
        permisos=permisos, created_at=usuario.created_at,
    )


@router.delete("/usuarios/{usuario_id}", status_code=204)
def eliminar_usuario(
    tenant_id: int,
    usuario_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    if usuario_id == current_user.id:
        raise HTTPException(400, "No puedes eliminarte a ti mismo")
    tu = db.query(TenantUsuario).filter(
        TenantUsuario.tenant_id == tenant_id,
        TenantUsuario.usuario_id == usuario_id,
    ).first()
    if not tu:
        raise HTTPException(404, "Usuario no encontrado en este tenant")
    tu.activo = False
    db.commit()


@router.post("/usuarios/{usuario_id}/permisos", response_model=UsuarioTenantOut)
def sobreescribir_permisos(
    tenant_id: int,
    usuario_id: int,
    permisos_conceder: List[str],
    db: Session = Depends(get_db),
    _=Depends(get_tenant_user),
):
    """Concede o revoca permisos individuales sobre los del rol base."""
    tu = db.query(TenantUsuario).filter(
        TenantUsuario.tenant_id == tenant_id,
        TenantUsuario.usuario_id == usuario_id,
    ).first()
    if not tu:
        raise HTTPException(404, "Usuario no encontrado")

    # Borrar overrides anteriores
    db.query(TenantUsuarioPermiso).filter(
        TenantUsuarioPermiso.tenant_id == tenant_id,
        TenantUsuarioPermiso.usuario_id == usuario_id,
    ).delete()

    # Obtener todos los permisos disponibles
    todos = {p.codigo: p.id for p in db.query(Permiso).all()}

    for cod in permisos_conceder:
        if cod in todos:
            db.add(TenantUsuarioPermiso(
                tenant_id=tenant_id,
                usuario_id=usuario_id,
                permiso_id=todos[cod],
                concedido=True,
            ))

    db.commit()
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    permisos = _permisos_efectivos(db, tenant_id, usuario_id, tu.rol)
    return UsuarioTenantOut(
        id=usuario.id, email=usuario.email, nombre=usuario.nombre,
        activo=usuario.activo, rol=tu.rol, permisos=permisos,
        created_at=usuario.created_at,
    )

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario, TenantUsuario
from auth.jwt import verificar_token
from typing import Optional


def get_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")
    return authorization.split(" ", 1)[1]


def get_current_user(token: str = Depends(get_token), db: Session = Depends(get_db)) -> Usuario:
    payload = verificar_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    user = db.query(Usuario).filter(Usuario.id == int(payload.get("sub")), Usuario.activo == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


def get_tenant_user(
    tenant_id: int,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantUsuario:
    tu = db.query(TenantUsuario).filter(
        TenantUsuario.tenant_id == tenant_id,
        TenantUsuario.usuario_id == current_user.id,
        TenantUsuario.activo == True,
    ).first()
    if not tu:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a este tenant")
    return tu


def require_rol(*roles: str):
    def dependency(
        tenant_id: int,
        current_user: Usuario = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> TenantUsuario:
        tu = db.query(TenantUsuario).filter(
            TenantUsuario.tenant_id == tenant_id,
            TenantUsuario.usuario_id == current_user.id,
            TenantUsuario.activo == True,
        ).first()
        if not tu:
            raise HTTPException(status_code=403, detail="Sin acceso a este tenant")
        if tu.rol not in roles:
            raise HTTPException(status_code=403, detail=f"Se requiere rol: {', '.join(roles)}")
        return tu
    return dependency

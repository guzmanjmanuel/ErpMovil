import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.usuario import Usuario, TenantUsuario
from schemas.auth import LoginRequest, TokenResponse, UsuarioOut
from auth.jwt import crear_token
from auth.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


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

    token = crear_token({"sub": usuario.id, "tenant_id": data.tenant_id, "rol": tu.rol})

    return TokenResponse(
        access_token=token,
        usuario_id=usuario.id,
        nombre=usuario.nombre,
        email=usuario.email,
        rol=tu.rol,
        tenant_id=data.tenant_id,
    )


@router.get("/me", response_model=UsuarioOut)
def me(current_user: Usuario = Depends(get_current_user)):
    return current_user

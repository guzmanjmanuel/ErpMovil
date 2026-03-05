from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario_id: int
    nombre: str
    email: str
    rol: str
    tenant_id: int


class UsuarioOut(BaseModel):
    id: int
    email: str
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}

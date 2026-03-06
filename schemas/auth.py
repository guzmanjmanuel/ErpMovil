from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: int | None = None   # Superadmin puede omitirlo para ver la lista de tenants


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario_id: int
    nombre: str
    email: str
    rol: str
    tenant_id: int | None = None
    tipo_negocio: str = "restaurante"
    establecimiento_id: int | None = None
    is_superadmin: bool = False
    permisos: list[str] = []


class UsuarioOut(BaseModel):
    id: int
    email: str
    nombre: str
    activo: bool

    model_config = {"from_attributes": True}

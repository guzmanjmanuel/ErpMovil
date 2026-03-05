from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

SECRET_KEY = "erpmovil-secret-key-cambiar-en-produccion"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 horas


def crear_token(data: dict) -> str:
    payload = data.copy()
    # sub debe ser string según el estándar JWT
    if "sub" in payload:
        payload["sub"] = str(payload["sub"])
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

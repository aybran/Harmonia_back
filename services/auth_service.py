from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from models.models import User
from Utils import verify_password, create_access_token, SECRET_KEY, ALGORITHM
from core.database import get_db


security = HTTPBearer()


# ============================================================
# AUTENTICAÇÃO POR EMAIL + SENHA
# ============================================================
def authenticate_user(db: Session, email: str, password: str):
    """
    Valida email e senha. Retorna o usuário se correto, senão None.
    """
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password):
        return None

    return user


# ============================================================
# PEGAR USUÁRIO PELO TOKEN
# ============================================================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """
    Valida o token recebido via Bearer e retorna o usuário correspondente.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decodifica o token
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Busca usuário no banco
    user = db.query(User).filter(User.email == email).first()

    if user is None:
        raise credentials_exception

    return user

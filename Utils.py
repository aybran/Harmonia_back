# Importações necessárias
import os
from datetime import datetime, date, timezone, timedelta
from passlib.context import CryptContext
from jose import jwt
from dotenv import load_dotenv


# ============================================================
# CARREGAMENTO DAS VARIÁVEIS DE AMBIENTE
# ============================================================
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY deve ser definida nas variáveis de ambiente")

ALGORITHM = os.getenv("ALGORITHM", "HS256")

try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
except (ValueError, TypeError):
    ACCESS_TOKEN_EXPIRE_MINUTES = 30


# ============================================================
# CONFIGURAÇÃO DE BCRYPT
# ============================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara uma senha em texto puro com o hash armazenado.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Gera o hash seguro de uma senha.
    """
    return pwd_context.hash(password[:72])


# ============================================================
# CRIAÇÃO DE JWT
# ============================================================
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Cria um token JWT contendo `data["sub"] = email do usuário`.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt


# ============================================================
# CALCULAR IDADE
# ============================================================
def calculate_age(birth_date: date) -> int:
    """
    Calcula a idade da pessoa (em anos) considerando se já fez aniversário.
    """
    today = date.today()
    age = today.year - birth_date.year

    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1

    return age

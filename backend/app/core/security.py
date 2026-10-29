"""Криптография: хэши паролей (bcrypt), JWT access-токены, refresh-токены, коды 2FA."""
import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import UnauthorizedError


# ---------- пароли ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


# Хэш-заглушка: проверяем пароль даже для несуществующего пользователя,
# чтобы время ответа не выдавало, существует ли логин.
DUMMY_HASH = hash_password("dummy-password-for-timing")


# ---------- хэш для токенов/кодов (в БД не храним открытые значения) ----------
def sha256(value: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


# ---------- JWT access ----------
def create_access_token(user_id: int, role: str) -> tuple[str, int]:
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + expires,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, int(expires.total_seconds())


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Срок действия токена истёк", code="token_expired")
    except jwt.PyJWTError:
        raise UnauthorizedError("Недействительный токен", code="invalid_token")
    if payload.get("type") != "access":
        raise UnauthorizedError("Неверный тип токена", code="invalid_token")
    return payload


# ---------- refresh / 2FA ----------
def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    visible = name[:2] if len(name) > 2 else name[:1]
    return f"{visible}{'*' * max(len(name) - len(visible), 1)}@{domain}"

"""Зависимости FastAPI: сессия БД, сервисы, текущий пользователь, проверка прав (OAuth2 scopes)."""
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.init_db import PERMISSIONS
from app.db.session import get_db
from app.models import User
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService
from app.services.item_service import ItemService
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", scopes=PERMISSIONS, auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


def get_item_service(db: DbSession) -> ItemService:
    return ItemService(db)


def get_user_service(db: DbSession) -> UserService:
    return UserService(db)


def get_current_user(security_scopes: SecurityScopes, db: DbSession,
                     token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    if not token:
        raise UnauthorizedError("Требуется авторизация", code="not_authenticated")
    payload = decode_access_token(token)
    user = UserRepository(db).get(int(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("Пользователь не найден или заблокирован", code="invalid_token")
    # Права берутся из БД, а не из токена: смена роли действует сразу
    missing = [s for s in security_scopes.scopes if not user.has_permission(s)]
    if missing:
        raise ForbiddenError(f"Недостаточно прав: {', '.join(missing)}")
    return user


def require(*perms: str):
    """Пользователь должен иметь все указанные права."""
    return Security(get_current_user, scopes=list(perms))


def require_any(*perms: str):
    """Пользователь должен иметь хотя бы одно из прав."""
    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not any(user.has_permission(p) for p in perms):
            raise ForbiddenError(f"Недостаточно прав: нужно одно из {', '.join(perms)}")
        return user
    return Depends(checker)


CurrentUser = Annotated[User, Depends(get_current_user)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
ItemSvc = Annotated[ItemService, Depends(get_item_service)]
UserSvc = Annotated[UserService, Depends(get_user_service)]

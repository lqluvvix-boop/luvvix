from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthSvc, CurrentUser
from app.api.responses import E401, E403, E404, E409, E423, E429, errors
from app.schemas.auth import ChallengeOut, LoginIn, RefreshIn, RegisterIn, ResendIn, TokenOut, VerifyCodeIn
from app.schemas.common import MessageOut
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post("/register", response_model=ChallengeOut, status_code=status.HTTP_201_CREATED,
             responses=errors(E409, E429), summary="Регистрация (шаг 1)")
def register(data: RegisterIn, svc: AuthSvc):
    """Создаёт учётную запись с ролью «Кладовщик» и отправляет код подтверждения на email.
    Код нужно подтвердить через `POST /auth/verify`."""
    return svc.register(data)


@router.post("/login", response_model=ChallengeOut, responses=errors(E401, E403, E423, E429),
             summary="Вход: логин и пароль (шаг 1)")
def login(data: LoginIn, svc: AuthSvc):
    """Проверяет логин/пароль и отправляет одноразовый 6-значный код на почту (2FA).
    После 5 неверных паролей учётная запись блокируется на 15 минут."""
    return svc.login(data.login, data.password)


@router.post("/verify", response_model=TokenOut, responses=errors(E401, E403, E429),
             summary="Подтверждение кода из письма (шаг 2)")
def verify(data: VerifyCodeIn, svc: AuthSvc):
    """Возвращает пару токенов: access (JWT, 15 мин) и refresh (7 дней, одноразовый)."""
    return svc.verify_code(data.challenge_id, data.code)


@router.post("/resend", response_model=ChallengeOut, responses=errors(E404, E429),
             summary="Отправить код повторно")
def resend(data: ResendIn, svc: AuthSvc):
    return svc.resend_code(data.challenge_id)


@router.post("/refresh", response_model=TokenOut, responses=errors(E401, E429),
             summary="Обновить токены по refresh-токену")
def refresh(data: RefreshIn, svc: AuthSvc):
    """Ротация: старый refresh-токен становится недействительным. Повторное использование
    старого токена считается кражей — отзывается вся цепочка сессии."""
    return svc.refresh(data.refresh_token)


@router.post("/logout", response_model=MessageOut, responses=errors(E429), summary="Выход")
def logout(data: RefreshIn, svc: AuthSvc):
    svc.logout(data.refresh_token)
    return MessageOut(message="Вы вышли из системы")


@router.post("/logout-all", response_model=MessageOut, responses=errors(E401),
             summary="Выйти на всех устройствах")
def logout_all(user: CurrentUser, svc: AuthSvc):
    svc.logout_all(user)
    return MessageOut(message="Все сессии завершены")


@router.get("/me", response_model=UserOut, responses=errors(E401), summary="Текущий пользователь")
def me(user: CurrentUser):
    return user


@router.post("/token", response_model=TokenOut, responses=errors(E401, E403, E423),
             summary="OAuth2 password grant (для кнопки Authorize в Swagger)")
def oauth2_token(form: Annotated[OAuth2PasswordRequestForm, Depends()], svc: AuthSvc):
    """Стандартный OAuth2 password flow с 2FA:
    1) Authorize с username/password — на почту придёт код (ответ 401 `2fa_required`);
    2) повторите Authorize, указав код в поле **client_secret**."""
    return svc.oauth2_password_grant(form.username, form.password, form.client_secret)

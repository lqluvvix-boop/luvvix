import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserOut

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, examples=["ivanov"])
    email: EmailStr
    full_name: str = Field(default="", max_length=150, examples=["Иванов Иван"])
    password: str = Field(min_length=8, max_length=128, examples=["Secret123!"])

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("Логин: латиница, цифры, _ . - (3–50 символов)")
        return v.lower()

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if not (re.search(r"[A-Za-zА-Яа-я]", v) and re.search(r"\d", v)):
            raise ValueError("Пароль должен содержать буквы и цифры")
        return v


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=255, description="Логин или email")
    password: str = Field(min_length=1, max_length=128)


class ChallengeOut(BaseModel):
    """Ответ шага 1: на почту отправлен код, нужно подтвердить его на шаге 2."""
    challenge_id: str
    purpose: str  # "login" — вход, "register" — подтверждение почты
    email_masked: str
    expires_in: int
    message: str


class VerifyCodeIn(BaseModel):
    challenge_id: str = Field(min_length=10, max_length=36)
    code: str = Field(pattern=r"^\d{6}$", examples=["123456"])


class ResendIn(BaseModel):
    challenge_id: str = Field(min_length=10, max_length=36)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=10)

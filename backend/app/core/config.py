"""Настройки приложения. Читаются из переменных окружения / файла .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Luvvix API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # База данных (SQLite по умолчанию, можно PostgreSQL: postgresql+psycopg://user:pass@host/db)
    DATABASE_URL: str = "sqlite:///./luvvix.db"

    # JWT
    SECRET_KEY: str = "CHANGE_ME_please_use_long_random_string_at_least_32_chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 2FA по почте
    TWO_FA_CODE_TTL_MINUTES: int = 5
    TWO_FA_MAX_ATTEMPTS: int = 5

    # Защита от перебора
    MAX_FAILED_LOGINS: int = 5
    LOCKOUT_MINUTES: int = 15
    RATE_LIMIT_PER_MINUTE: int = 20  # для /auth/*

    # SMTP. Если SMTP_HOST пустой — коды выводятся в консоль сервера (режим разработки)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "luvvix@example.com"
    SMTP_SSL: bool = True

    # Первый администратор (создаётся при старте, если его нет)
    ADMIN_EMAIL: str = "admin@luvvix.local"
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "Admin12345!"

    CORS_ORIGINS: list[str] = ["http://localhost", "http://127.0.0.1"]
    ALLOWED_HOSTS: list[str] = ["*"]
    MAX_BODY_BYTES: int = 1_000_000


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

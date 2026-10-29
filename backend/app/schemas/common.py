from pydantic import BaseModel


class ErrorOut(BaseModel):
    """Единый формат ошибки для всех ответов 4xx/5xx."""
    detail: str
    code: str
    errors: list[dict] | None = None


class MessageOut(BaseModel):
    message: str

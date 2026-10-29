"""Описание ошибок для Swagger, чтобы в документации были видны коды 400/401/403/404/409/500."""
from app.schemas.common import ErrorOut

E400 = {400: {"model": ErrorOut, "description": "Некорректный запрос / ошибка валидации"}}
E401 = {401: {"model": ErrorOut, "description": "Не авторизован / токен недействителен"}}
E403 = {403: {"model": ErrorOut, "description": "Недостаточно прав"}}
E404 = {404: {"model": ErrorOut, "description": "Не найдено"}}
E409 = {409: {"model": ErrorOut, "description": "Конфликт (дубликат)"}}
E423 = {423: {"model": ErrorOut, "description": "Учётная запись временно заблокирована"}}
E429 = {429: {"model": ErrorOut, "description": "Слишком много запросов"}}
E500 = {500: {"model": ErrorOut, "description": "Внутренняя ошибка сервера"}}


def errors(*codes: dict) -> dict:
    result: dict = {**E400, **E500}
    for c in codes:
        result.update(c)
    return result

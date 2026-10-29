"""Доменные исключения. Сервисы бросают их, а обработчики в main.py
превращают в JSON-ответ с нужным HTTP-кодом. Так бизнес-логика не знает про HTTP."""


class AppError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, detail: str = "Некорректный запрос", code: str | None = None):
        super().__init__(detail)
        self.detail = detail
        if code:
            self.code = code


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"


class UnauthorizedError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class LockedError(AppError):
    status_code = 423
    code = "locked"


class ServiceUnavailableError(AppError):
    status_code = 503
    code = "service_unavailable"


class TooManyRequestsError(AppError):
    status_code = 429
    code = "too_many_requests"

"""Точка входа FastAPI. Запуск: uvicorn app.main:app --host 0.0.0.0 --port 8000
Документация: http://localhost:8000/docs (Swagger) и /redoc."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routers import auth, categories, items, users
from app.core.config import settings
from app.core.errors import AppError
from app.core.middleware import AuthRateLimitMiddleware, BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.db.init_db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("luvvix")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    log.info("База данных готова")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API системы учёта ТМЦ **Luvvix**.\n\n"
        "**Авторизация (2FA):** `POST /auth/login` → код на почту → `POST /auth/verify` → токены. "
        "Access-токен передаётся в заголовке `Authorization: Bearer <token>`.\n\n"
        "**Роли:** Администратор, Бухгалтер, Кладовщик, Руководитель — права см. `GET /roles`.\n\n"
        "Все ошибки возвращаются в формате `{detail, code, errors?}`."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------- middleware (порядок: последний добавленный выполняется первым) ----------
app.add_middleware(AuthRateLimitMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=False,
                   allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)
app.add_middleware(SecurityHeadersMiddleware)


# ---------- обработчики ошибок ----------
@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse({"detail": exc.detail, "code": exc.code}, status_code=exc.status_code, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    errs = []
    for e in exc.errors():
        loc = ".".join(str(p) for p in e.get("loc", []) if p != "body")
        msg = str(e.get("msg", "")).removeprefix("Value error, ")
        errs.append({"field": loc, "message": msg})
    first = f"{errs[0]['field']}: {errs[0]['message']}" if errs else "Ошибка валидации"
    return JSONResponse({"detail": first, "code": "validation_error", "errors": errs}, status_code=400)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException):
    messages = {404: "Ресурс не найден", 405: "Метод не поддерживается"}
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail not in ("Not Found", "Method Not Allowed") \
        else messages.get(exc.status_code, str(exc.detail))
    return JSONResponse({"detail": detail, "code": f"http_{exc.status_code}"}, status_code=exc.status_code)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    rid = getattr(request.state, "request_id", "-")
    log.exception("Необработанная ошибка (request_id=%s): %s", rid, exc)
    return JSONResponse({"detail": f"Внутренняя ошибка сервера (id: {rid})", "code": "internal_error"},
                        status_code=500)


# ---------- маршруты ----------
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(items.router, prefix=API_PREFIX)
app.include_router(categories.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)


@app.get("/health", tags=["Служебное"], summary="Проверка работоспособности")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}

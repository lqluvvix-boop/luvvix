"""Адаптер к REST API (FastAPI). Все действия приложения выполняются только через него.

Без внешних зависимостей (urllib из стандартной библиотеки) — надёжно собирается в APK.
Методы синхронные: их вызывают из фонового потока (см. services/runner.py), чтобы не блокировать UI.
При истечении access-токена клиент сам обновляет его по refresh-токену и повторяет запрос.
"""
import json
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request

from app.config import API_PREFIX, REQUEST_TIMEOUT


class ApiError(Exception):
    """Ошибка API с HTTP-кодом. status=0 — нет связи с сервером."""

    def __init__(self, status: int, detail: str, code: str = "", errors: list | None = None):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.code = code
        self.errors = errors or []

    @property
    def is_auth_error(self) -> bool:
        return self.status == 401


STATUS_TEXT = {
    400: "Некорректные данные",
    401: "Требуется вход в систему",
    403: "Недостаточно прав",
    404: "Запись не найдена",
    409: "Такая запись уже существует",
    423: "Учётная запись временно заблокирована",
    429: "Слишком много запросов, подождите",
    500: "Ошибка на сервере, попробуйте позже",
    503: "Сервис временно недоступен",
}


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.on_tokens_changed = None    # callback(access, refresh) — сохранить сессию
        self.on_session_expired = None   # callback() — вернуть пользователя на вход
        self._refresh_lock = threading.Lock()

    # ---------------- низкий уровень ----------------
    def set_base_url(self, url: str) -> None:
        self.base_url = url.strip().rstrip("/")

    def _raw(self, method: str, path: str, body=None, params=None, auth=True):
        url = f"{self.base_url}{API_PREFIX}{path}"
        if params:
            clean = {k: v for k, v in params.items() if v not in (None, "")}
            if clean:
                url += "?" + urllib.parse.urlencode(clean)
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        if auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw = resp.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except urllib.error.HTTPError as e:
            raise self._to_api_error(e) from None
        except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as e:
            raise ApiError(0, f"Нет связи с сервером ({self.base_url}). Проверьте адрес и сеть.",
                           "network_error") from e
        except ValueError:
            raise ApiError(0, "Сервер вернул некорректный ответ", "bad_response") from None

    @staticmethod
    def _to_api_error(e: urllib.error.HTTPError) -> ApiError:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {}
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if not isinstance(detail, str) or not detail:
            detail = STATUS_TEXT.get(e.code, f"Ошибка {e.code}")
        return ApiError(e.code, detail, payload.get("code", ""), payload.get("errors"))

    def request(self, method: str, path: str, body=None, params=None, auth=True):
        try:
            return self._raw(method, path, body, params, auth)
        except ApiError as err:
            if not (auth and err.status == 401 and self.refresh_token):
                raise
            if not self._try_refresh():
                if self.on_session_expired:
                    self.on_session_expired()
                raise ApiError(401, "Сессия истекла. Войдите снова.", "session_expired") from None
            return self._raw(method, path, body, params, auth)

    def _try_refresh(self) -> bool:
        token_before = self.access_token
        with self._refresh_lock:
            if self.access_token != token_before:  # другой поток уже обновил
                return True
            try:
                data = self._raw("POST", "/auth/refresh", {"refresh_token": self.refresh_token}, auth=False)
            except ApiError:
                self.set_tokens(None, None)
                return False
            self.set_tokens(data["access_token"], data["refresh_token"])
            return True

    def set_tokens(self, access: str | None, refresh: str | None) -> None:
        self.access_token, self.refresh_token = access, refresh
        if self.on_tokens_changed:
            self.on_tokens_changed(access, refresh)

    # ---------------- аутентификация ----------------
    def register(self, username, email, full_name, password):
        return self._raw("POST", "/auth/register", {"username": username, "email": email,
                                                     "full_name": full_name, "password": password}, auth=False)

    def login(self, login, password):
        return self._raw("POST", "/auth/login", {"login": login, "password": password}, auth=False)

    def verify(self, challenge_id, code):
        data = self._raw("POST", "/auth/verify", {"challenge_id": challenge_id, "code": code}, auth=False)
        self.set_tokens(data["access_token"], data["refresh_token"])
        return data

    def resend(self, challenge_id):
        return self._raw("POST", "/auth/resend", {"challenge_id": challenge_id}, auth=False)

    def restore_session(self, refresh_token):
        self.refresh_token = refresh_token
        data = self._raw("POST", "/auth/refresh", {"refresh_token": refresh_token}, auth=False)
        self.set_tokens(data["access_token"], data["refresh_token"])
        return data

    def logout(self):
        token = self.refresh_token
        self.set_tokens(None, None)
        if token:
            try:
                self._raw("POST", "/auth/logout", {"refresh_token": token}, auth=False)
            except ApiError:
                pass  # локально сессия уже завершена

    def me(self):
        return self.request("GET", "/auth/me")

    # ---------------- ТМЦ ----------------
    def list_items(self, search=None, category_id=None, sort="updated_at", order="desc", skip=0, limit=20):
        return self.request("GET", "/items", params={"search": search, "category_id": category_id,
                                                     "sort": sort, "order": order, "skip": skip, "limit": limit})

    def get_item(self, item_id):
        return self.request("GET", f"/items/{item_id}")

    def create_item(self, data: dict):
        return self.request("POST", "/items", data)

    def update_item(self, item_id, data: dict):
        return self.request("PATCH", f"/items/{item_id}", data)

    def delete_item(self, item_id):
        return self.request("DELETE", f"/items/{item_id}")

    def item_history(self, item_id):
        return self.request("GET", f"/items/{item_id}/history")

    def categories(self):
        return self.request("GET", "/categories")

    # ---------------- пользователи ----------------
    def users_short(self):
        return self.request("GET", "/users/short")

    def users(self, search=None):
        return self.request("GET", "/users", params={"search": search})

    def update_user(self, user_id, data: dict):
        return self.request("PATCH", f"/users/{user_id}", data)

    def roles(self):
        return self.request("GET", "/roles")

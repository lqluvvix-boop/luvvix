"""ViewModel авторизации: вход, регистрация, 2FA, восстановление сессии, выход."""
import re

from kivy.properties import DictProperty, ListProperty, StringProperty

from app.viewmodels.base import BaseViewModel

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")


class AuthViewModel(BaseViewModel):
    user = DictProperty({})
    permissions = ListProperty([])
    challenge = DictProperty({})   # {challenge_id, purpose, email_masked, message}
    display_name = StringProperty("")
    role_title = StringProperty("")

    def __init__(self, api, store, **kwargs):
        super().__init__(api, **kwargs)
        self.store = store

    # ---------- права ----------
    def can(self, perm: str) -> bool:
        return perm in self.permissions

    @property
    def is_authenticated(self) -> bool:
        return bool(self.user)

    # ---------- сценарии ----------
    def login(self, login: str, password: str, on_code_sent):
        login, password = login.strip(), password
        if not login or not password:
            self.error = "Введите логин и пароль"
            return
        self.store.last_login = login

        def ok(ch):
            self.challenge = ch
            on_code_sent()

        self.call(lambda: self.api.login(login, password), ok)

    def register(self, username, email, full_name, password, password2, on_code_sent):
        username, email = username.strip(), email.strip()
        problems = []
        if not USERNAME_RE.match(username):
            problems.append("• логин: 3–50 символов, латиница, цифры, _ . -")
        if not EMAIL_RE.match(email):
            problems.append("• некорректный email")
        if len(password) < 8 or not re.search(r"\d", password) or not re.search(r"[^\d\W]", password):
            problems.append("• пароль: не короче 8 символов, буквы и цифры")
        if password != password2:
            problems.append("• пароли не совпадают")
        if problems:
            self.error = "Проверьте данные:\n" + "\n".join(problems)
            return

        def ok(ch):
            self.challenge = ch
            on_code_sent()

        self.call(lambda: self.api.register(username, email, full_name.strip(), password), ok)

    def verify(self, code: str, on_done):
        code = code.strip()
        if not re.fullmatch(r"\d{6}", code):
            self.error = "Код состоит из 6 цифр"
            return
        cid = self.challenge.get("challenge_id")

        def ok(data):
            self._set_user(data["user"])
            self.challenge = {}
            on_done()

        self.call(lambda: self.api.verify(cid, code), ok)

    def resend(self, on_done=None):
        cid = self.challenge.get("challenge_id")

        def ok(ch):
            self.challenge = ch
            if on_done:
                on_done()

        self.call(lambda: self.api.resend(cid), ok)

    def restore_session(self, on_success, on_fail):
        token = self.store.refresh_token
        if not token:
            on_fail()
            return

        def ok(data):
            self._set_user(data["user"])
            on_success()

        def fail(_err):
            self.error = ""
            self.store.refresh_token = None
            on_fail()

        self.call(lambda: self.api.restore_session(token), ok, fail)

    def refresh_profile(self):
        self.call(self.api.me, self._set_user)

    def logout(self, on_done):
        def ok(_):
            self.clear()
            on_done()
        self.call(self.api.logout, ok, lambda _e: ok(None))

    def clear(self):
        self.user = {}
        self.permissions = []
        self.display_name = ""
        self.role_title = ""
        self.challenge = {}
        self.error = ""

    def _set_user(self, user: dict):
        self.user = user
        self.permissions = user.get("permissions", [])
        self.display_name = user.get("full_name") or user.get("username", "")
        self.role_title = user.get("role", {}).get("title", "")

"""Luvvix — мобильный клиент учёта ТМЦ (Kivy).
Архитектура MVVM:
  View       — app/views (экраны + .kv-разметка), только отображение;
  ViewModel  — app/viewmodels, состояние и логика экранов;
  Model/API  — app/services/api_client.py, единственная точка обмена данными с сервером (FastAPI).
"""
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.utils import platform

from app.config import DEFAULT_SERVER
from app.services.api_client import ApiClient
from app.services.session_store import SessionStore
from app.viewmodels.auth_vm import AuthViewModel
from app.viewmodels.items_vm import ItemDetailViewModel, ItemFormViewModel, ItemsListViewModel, ReferenceData
from app.viewmodels.users_vm import UsersViewModel
from app.views import screens as S
from app.views.widgets import confirm, toast  # noqa: F401  (регистрация классов для kv)

KV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "views", "kv")
AUTH_SCREENS = {"login", "register", "code"}


class Navigator:
    """Навигация со стеком (кнопка «Назад» и аппаратная кнопка Android)."""

    def __init__(self, sm: ScreenManager):
        self.sm = sm
        self.stack: list[str] = []

    def go(self, name: str, **params):
        if self.sm.current:
            self.stack.append(self.sm.current)
        self._show(name, "left", params)

    def replace(self, name: str, **params):
        self._show(name, "left", params)

    def reset(self, name: str):
        self.stack.clear()
        self._show(name, "right", {})

    def back(self) -> bool:
        if not self.stack:
            return False
        self._show(self.stack.pop(), "right", {})
        return True

    def _show(self, name, direction, params):
        screen = self.sm.get_screen(name)
        if name == "item_detail" and "item_id" in params:
            screen.show(params["item_id"])
        if name == "item_form":
            screen.prepare(params.get("mode", "create"), params.get("item"))
        self.sm.transition.direction = direction
        self.sm.current = name


class LuvvixApp(App):
    title = "Luvvix"
    auth_vm = ObjectProperty(None)
    items_vm = ObjectProperty(None)
    detail_vm = ObjectProperty(None)
    form_vm = ObjectProperty(None)
    users_vm = ObjectProperty(None)
    refs = ObjectProperty(None)
    server_label = StringProperty("")

    def build(self):
        Window.clearcolor = (0.957, 0.965, 0.98, 1)
        if platform not in ("android", "ios"):
            Window.size = (420, 820)
        Window.softinput_mode = "below_target"

        # ---- Model / сервисы ----
        self.store = SessionStore(self.user_data_dir)
        self.api = ApiClient(self.store.server_url or DEFAULT_SERVER)
        self.server_label = self.api.base_url
        self.api.on_tokens_changed = lambda _a, refresh: setattr(self.store, "refresh_token", refresh)
        self.api.on_session_expired = lambda: Clock.schedule_once(lambda _dt: self._session_expired())

        # ---- ViewModels ----
        self.auth_vm = AuthViewModel(self.api, self.store)
        self.refs = ReferenceData(self.api)
        self.items_vm = ItemsListViewModel(self.api, self.refs)
        self.detail_vm = ItemDetailViewModel(self.api)
        self.form_vm = ItemFormViewModel(self.api)
        self.users_vm = UsersViewModel(self.api)

        # ---- Views ----
        for kv in ("widgets.kv", "auth.kv", "main.kv", "items.kv"):
            Builder.load_file(os.path.join(KV_DIR, kv))

        sm = ScreenManager(transition=SlideTransition(duration=0.18))
        for cls in (S.LoginScreen, S.RegisterScreen, S.CodeScreen, S.HomeScreen, S.ItemsScreen,
                    S.ItemDetailScreen, S.ItemFormScreen, S.UsersScreen):
            sm.add_widget(cls())
        self.nav = Navigator(sm)
        self.sm = sm
        Window.bind(on_keyboard=self._on_key)

        sm.current = "login"
        Clock.schedule_once(lambda _dt: self.auth_vm.restore_session(self.on_logged_in, lambda: None), 0)
        return sm

    # ---------- действия уровня приложения ----------
    def on_logged_in(self):
        self.items_vm.search = ""
        self.sm.get_screen("items").needs_reload = True
        self.refs.load()
        self.nav.reset("home")

    def open_item(self, item_id: int):
        self.nav.go("item_detail", item_id=item_id)

    def items_screen_dirty(self):
        self.items_vm.reload()

    def set_server(self, url: str):
        self.api.set_base_url(url)
        self.store.server_url = url
        self.server_label = self.api.base_url

    def confirm_logout(self):
        confirm("Выход", "Выйти из аккаунта на этом устройстве?", self.logout, confirm_text="Выйти")

    def logout(self):
        def done():
            self.items_vm.items = []
            self.refs.categories, self.refs.users = [], []
            self.nav.reset("login")
            toast("Вы вышли из системы")
        self.auth_vm.logout(done)

    def _session_expired(self):
        if self.sm.current not in AUTH_SCREENS:
            self.auth_vm.clear()
            self.nav.reset("login")
            toast("Сессия истекла, войдите снова")

    def _on_key(self, _window, key, *_):
        if key == 27:  # «Назад» на Android / Esc на ПК
            if self.sm.current == "login" or self.sm.current == "home":
                return False  # стандартное поведение — свернуть приложение
            return self.nav.back()
        return False


if __name__ == "__main__":
    LuvvixApp().run()

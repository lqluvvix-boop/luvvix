"""View-слой (MVVM): экраны только отображают состояние ViewModel и передают ей действия пользователя.
Разметка — в app/views/kv/*.kv."""
from decimal import Decimal

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.factory import Factory

from app.config import RESEND_COOLDOWN
from app.viewmodels.items_vm import ALL_CATEGORIES, NO_CATEGORY, NO_RESPONSIBLE, SORT_OPTIONS
from app.views.widgets import UserRow, confirm, toast


def app():
    return App.get_running_app()


def fmt_money(value) -> str:
    try:
        d = Decimal(str(value)).quantize(Decimal("0.01"))
    except Exception:
        return str(value)
    whole, _, frac = f"{d:.2f}".partition(".")
    whole = f"{int(whole):,}".replace(",", " ")
    return f"{whole},{frac} ₽"


def fmt_date(iso: str) -> str:
    if not iso:
        return ""
    date, _, time = iso.partition("T")
    y, m, d = (date.split("-") + ["", "", ""])[:3]
    return f"{d}.{m}.{y} {time[:5]}"


# ======================= Авторизация =======================
class LoginScreen(Screen):
    def on_pre_enter(self, *_):
        app().auth_vm.error = ""
        if not self.ids.login.text:
            self.ids.login.text = app().store.last_login or ""
        self.ids.password.text = ""

    def do_login(self):
        app().auth_vm.login(self.ids.login.text, self.ids.password.text,
                            on_code_sent=lambda: app().nav.go("code"))

    def open_server_settings(self):
        content = Factory.ServerSettings()
        content.ids.url.text = app().api.base_url
        popup = Popup(title="Адрес сервера", content=content, size_hint=(0.92, None), height=dp(250))

        def save(*_):
            url = content.ids.url.text.strip()
            if not url.startswith(("http://", "https://")):
                content.ids.err.text = "Адрес должен начинаться с http:// или https://"
                return
            app().set_server(url)
            popup.dismiss()
            toast("Адрес сервера сохранён")

        content.ids.save.bind(on_release=save)
        content.ids.cancel.bind(on_release=lambda *_: popup.dismiss())
        popup.open()


class RegisterScreen(Screen):
    def on_pre_enter(self, *_):
        app().auth_vm.error = ""

    def do_register(self):
        ids = self.ids
        app().auth_vm.register(ids.username.text, ids.email.text, ids.full_name.text,
                               ids.password.text, ids.password2.text,
                               on_code_sent=lambda: app().nav.go("code"))


class CodeScreen(Screen):
    cooldown = NumericProperty(0)
    bar_title = StringProperty("Подтверждение")
    hint = StringProperty("")
    _ev = None

    def on_kv_post(self, *_):
        app().auth_vm.bind(challenge=self._on_challenge)

    def _on_challenge(self, _vm, ch):
        if not ch:
            return
        self.bar_title = "Подтверждение входа" if ch.get("purpose") == "login" else "Подтверждение почты"
        minutes = max(1, int(ch.get("expires_in", 300)) // 60)
        self.hint = f"Мы отправили 6-значный код на {ch.get('email_masked', '')}. Код действует {minutes} мин."

    def on_pre_enter(self, *_):
        app().auth_vm.error = ""
        self.ids.code.text = ""
        self._start_cooldown()
        Clock.schedule_once(lambda _dt: setattr(self.ids.code, "focus", True), 0.3)

    def on_leave(self, *_):
        if self._ev:
            self._ev.cancel()

    def _start_cooldown(self):
        self.cooldown = RESEND_COOLDOWN
        if self._ev:
            self._ev.cancel()
        self._ev = Clock.schedule_interval(self._tick, 1)

    def _tick(self, _dt):
        self.cooldown = max(0, self.cooldown - 1)
        if self.cooldown == 0:
            return False

    def on_code_text(self, text):
        if len(text) == 6 and text.isdigit() and not app().auth_vm.busy:
            self.do_verify()

    def do_verify(self):
        app().auth_vm.verify(self.ids.code.text, on_done=app().on_logged_in)

    def do_resend(self):
        def done():
            self._start_cooldown()
            toast("Новый код отправлен")
        app().auth_vm.resend(done)


# ======================= Главный экран =======================
class HomeScreen(Screen):
    def on_pre_enter(self, *_):
        app().auth_vm.refresh_profile()


# ======================= Список ТМЦ =======================
class ItemsScreen(Screen):
    needs_reload = BooleanProperty(True)
    _search_ev = None

    def on_kv_post(self, *_):
        vm = app().items_vm
        vm.bind(items=self._on_items)

    def on_pre_enter(self, *_):
        refs = app().refs
        self.ids.category.values = refs.category_names(with_all=True)
        self.ids.sort.values = list(SORT_OPTIONS)
        if not refs.categories:
            refs.load(on_done=lambda: setattr(self.ids.category, "values", refs.category_names(with_all=True)))
        if self.needs_reload:
            self.needs_reload = False
            app().items_vm.reload()

    def _on_items(self, _vm, items):
        rows = []
        for it in items:
            sub = it["inventory_number"]
            if it.get("category"):
                sub += f" · {it['category']['name']}"
            if it.get("location"):
                sub += f" · {it['location']}"
            rows.append({"item_id": it["id"], "title": it["name"], "subtitle": sub,
                         "qty": f"{it['quantity']} {it['unit']}"})
        self.ids.rv.data = rows

    def on_search_text(self, text):
        app().items_vm.search = text
        if self._search_ev:
            self._search_ev.cancel()
        self._search_ev = Clock.schedule_once(lambda _dt: app().items_vm.reload(), 0.5)

    def on_filter(self, category_name):
        vm = app().items_vm
        if category_name and category_name != vm.category_name:
            vm.category_name = category_name
            vm.reload()

    def on_sort(self, sort_name):
        vm = app().items_vm
        if sort_name and sort_name != vm.sort_name:
            vm.sort_name = sort_name
            vm.reload()

    def reset_filters(self):
        vm = app().items_vm
        self.ids.search.text = ""
        vm.search = ""
        vm.category_name = ALL_CATEGORIES
        self.ids.category.text = ALL_CATEGORIES
        vm.reload()

    def on_scroll(self, rv):
        if rv.scroll_y <= 0.02:
            app().items_vm.load_more()


# ======================= Просмотр записи =======================
class ItemDetailScreen(Screen):
    item_id = NumericProperty(0)

    def on_kv_post(self, *_):
        app().detail_vm.bind(item=self._render, history=self._render_history)

    def show(self, item_id: int):
        self.item_id = item_id
        app().detail_vm.load(item_id, with_history=app().auth_vm.can("history:read"))

    def _render(self, _vm, item):
        box = self.ids.fields
        box.clear_widgets()
        self.ids.title.text = item.get("name", "Загрузка…") if item else "Загрузка…"
        if not item:
            return
        rows = [
            ("Инвентарный номер", item["inventory_number"]),
            ("Категория", (item.get("category") or {}).get("name") or "—"),
            ("Количество", f"{item['quantity']} {item['unit']}"),
            ("Цена за единицу", fmt_money(item["price"])),
            ("Сумма", fmt_money(Decimal(str(item["price"])) * item["quantity"])),
            ("Местонахождение", item.get("location") or "—"),
            ("Ответственный", ((item.get("responsible") or {}).get("full_name")
                               or (item.get("responsible") or {}).get("username") or "—")),
            ("Описание", item.get("description") or "—"),
            ("Создана", fmt_date(item["created_at"])),
            ("Изменена", fmt_date(item["updated_at"])),
        ]
        for caption, value in rows:
            row = Factory.InfoRow()
            row.caption, row.value = caption, str(value)
            box.add_widget(row)

    def _render_history(self, _vm, history):
        box = self.ids.history
        box.clear_widgets()
        for h in history:
            row = Factory.HistoryRow()
            who = (h.get("user") or {}).get("username", "система")
            action = "создание" if h["action"] == "create" else "изменение"
            row.caption = f"{fmt_date(h['created_at'])} · {who} · {action}"
            row.value = h["changes"]
            box.add_widget(row)

    def edit(self):
        app().nav.go("item_form", mode="edit", item=dict(app().detail_vm.item))

    def ask_delete(self):
        item = app().detail_vm.item
        confirm("Удаление ТМЦ",
                f"Удалить «{item.get('name')}» ({item.get('inventory_number')})?\nДействие нельзя отменить.",
                self._delete)

    def _delete(self):
        def done():
            toast("Запись удалена")
            app().items_screen_dirty()
            app().nav.back()
        app().detail_vm.delete(done)


# ======================= Создание / редактирование =======================
FACT_FIELDS = {"quantity", "location", "description"}
ALL_FIELDS = ("name", "inventory_number", "unit", "quantity", "price", "location", "description")


class ItemFormScreen(Screen):
    title = StringProperty("Новая ТМЦ")
    fact_only = BooleanProperty(False)

    def prepare(self, mode="create", item=None):
        vm, refs, ids = app().form_vm, app().refs, self.ids
        ids.category.values = refs.category_names(with_none=True)
        ids.responsible.values = refs.user_names()
        if not refs.categories or not refs.users:
            refs.load(on_done=lambda: (setattr(ids.category, "values", refs.category_names(with_none=True)),
                                       setattr(ids.responsible, "values", refs.user_names())))
        if mode == "edit" and item:
            vm.start_edit(item)
            self.title = "Редактирование"
            self.fact_only = not app().auth_vm.can("items:update")
            for f in ALL_FIELDS:
                ids[f].text = str(item.get(f, "") if item.get(f) is not None else "")
            ids.category.text = (item.get("category") or {}).get("name") or NO_CATEGORY
            resp = item.get("responsible")
            ids.responsible.text = refs.user_label(resp) if resp else NO_RESPONSIBLE
        else:
            vm.start_create()
            self.title = "Новая ТМЦ"
            self.fact_only = False
            for f in ALL_FIELDS:
                ids[f].text = ""
            ids.unit.text, ids.quantity.text, ids.price.text = "шт", "1", "0"
            ids.category.text = NO_CATEGORY
            ids.responsible.text = NO_RESPONSIBLE

    def save(self):
        ids, refs = self.ids, app().refs
        form = {f: ids[f].text for f in ALL_FIELDS}
        form["category_id"] = refs.category_id(ids.category.text)
        form["responsible_id"] = refs.user_id(ids.responsible.text)
        allowed = FACT_FIELDS if self.fact_only else None
        app().form_vm.save(form, allowed, self._saved)

    def _saved(self, item):
        vm = app().form_vm
        toast("ТМЦ создана" if vm.mode == "create" else "Изменения сохранены")
        app().items_screen_dirty()
        if vm.mode == "create":
            app().nav.replace("item_detail", item_id=item["id"])
        else:
            app().nav.back()
            app().detail_vm.load(item["id"], with_history=app().auth_vm.can("history:read"))


# ======================= Пользователи (администратор) =======================
class UsersScreen(Screen):
    def on_kv_post(self, *_):
        app().users_vm.bind(users=self._render)

    def on_pre_enter(self, *_):
        app().users_vm.load(self.ids.search.text)

    def _render(self, _vm, users):
        box = self.ids.user_list
        box.clear_widgets()
        vm = app().users_vm
        me = app().auth_vm.user.get("id")
        for u in users:
            status = "" if u["is_active"] else " · ЗАБЛОКИРОВАН"
            box.add_widget(UserRow(
                user_id=u["id"], title=f"{u['full_name'] or u['username']} (@{u['username']})",
                subtitle=f"{u['email']}{status}", role_title=u["role"]["title"],
                role_values=vm.role_titles(), active=u["is_active"], is_self=(u["id"] == me), screen=self,
            ))

    def change_role(self, row: UserRow, title: str):
        name = app().users_vm.role_name(title)
        app().users_vm.update(row.user_id, on_done=lambda u: toast(f"Роль изменена: {u['role']['title']}"),
                              role=name)

    def toggle_active(self, row: UserRow):
        new_state = not row.active
        verb = "Разблокировать" if new_state else "Заблокировать"

        def go():
            app().users_vm.update(row.user_id, is_active=new_state,
                                  on_done=lambda _u: toast("Пользователь " + ("разблокирован" if new_state
                                                                               else "заблокирован")))
        confirm(f"{verb} пользователя", f"{verb} {row.title}?", go, confirm_text=verb)


class InfoRow(BoxLayout):
    caption = StringProperty("")
    value = StringProperty("")


class HistoryRow(InfoRow):
    pass

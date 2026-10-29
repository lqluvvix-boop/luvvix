"""ViewModel администрирования: пользователи, роли, блокировка."""
from kivy.properties import ListProperty

from app.viewmodels.base import BaseViewModel


class UsersViewModel(BaseViewModel):
    users = ListProperty([])
    roles = ListProperty([])  # [{name, title, permission_codes}]

    def load(self, search: str = ""):
        def fetch():
            return self.api.users(search.strip() or None), self.api.roles()

        def ok(res):
            self.users, self.roles = res

        self.call(fetch, ok)

    def role_titles(self):
        return [r["title"] for r in self.roles]

    def role_name(self, title):
        return next((r["name"] for r in self.roles if r["title"] == title), None)

    def update(self, user_id: int, on_done=None, **changes):
        def ok(updated):
            self.users = [updated if u["id"] == user_id else u for u in self.users]
            if on_done:
                on_done(updated)

        def fail(_err):
            self.users = list(self.users)  # перерисовать исходное состояние
        self.call(lambda: self.api.update_user(user_id, changes), ok, fail)

"""Хранение сессии и настроек в приватной папке приложения (user_data_dir)."""
import os

from kivy.storage.jsonstore import JsonStore


class SessionStore:
    def __init__(self, data_dir: str):
        os.makedirs(data_dir, exist_ok=True)
        self._store = JsonStore(os.path.join(data_dir, "session.json"))

    def _get(self, key, default=None):
        try:
            return self._store.get(key)["value"] if self._store.exists(key) else default
        except Exception:
            return default

    def _put(self, key, value):
        try:
            if value is None:
                if self._store.exists(key):
                    self._store.delete(key)
            else:
                self._store.put(key, value=value)
        except Exception:
            pass

    @property
    def refresh_token(self):
        return self._get("refresh_token")

    @refresh_token.setter
    def refresh_token(self, value):
        self._put("refresh_token", value)

    @property
    def server_url(self):
        return self._get("server_url")

    @server_url.setter
    def server_url(self, value):
        self._put("server_url", value)

    @property
    def last_login(self):
        return self._get("last_login", "")

    @last_login.setter
    def last_login(self, value):
        self._put("last_login", value)

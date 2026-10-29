"""Базовая ViewModel (MVVM): состояние «загрузка/ошибка», к которому привязываются экраны."""
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, StringProperty

from app.services.api_client import ApiClient, ApiError
from app.services.runner import run_async


class BaseViewModel(EventDispatcher):
    busy = BooleanProperty(False)
    error = StringProperty("")

    def __init__(self, api: ApiClient, **kwargs):
        super().__init__(**kwargs)
        self.api = api

    def call(self, func, on_success=None, on_error=None):
        """Запустить запрос к API в фоне; busy/error обновляются автоматически."""
        self.busy = True
        self.error = ""

        def ok(result):
            self.busy = False
            if on_success:
                on_success(result)

        def fail(err: ApiError):
            self.busy = False
            self.error = self.format_error(err)
            if on_error:
                on_error(err)

        run_async(func, ok, fail)

    @staticmethod
    def format_error(err: ApiError) -> str:
        if err.status == 400 and err.errors:
            lines = [f"• {e.get('message', '')}" for e in err.errors[:4]]
            return "Проверьте данные:\n" + "\n".join(lines)
        return err.detail

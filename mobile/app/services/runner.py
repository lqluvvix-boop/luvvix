"""Выполнение запросов в фоновом потоке и возврат результата в UI-поток Kivy."""
import threading
import traceback

from kivy.clock import Clock

from app.services.api_client import ApiError


def run_async(func, on_success=None, on_error=None):
    def deliver(callback, value):
        if callback:
            Clock.schedule_once(lambda _dt, v=value: callback(v))

    def worker():
        try:
            result = func()
        except ApiError as exc:
            deliver(on_error, exc)
            return
        except Exception as exc:  # непредвиденная ошибка клиента
            traceback.print_exc()
            deliver(on_error, ApiError(-1, f"Ошибка приложения: {exc}", "client_error"))
            return
        deliver(on_success, result)

    threading.Thread(target=worker, daemon=True).start()

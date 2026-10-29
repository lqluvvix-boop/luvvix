"""Настройки клиента.
Адрес сервера можно поменять прямо в приложении (кнопка «Сервер» на экране входа).
  * эмулятор Android -> http://10.0.2.2:8000
  * телефон в той же Wi-Fi сети -> http://<IP компьютера>:8000
  * запуск на ПК -> http://127.0.0.1:8000
"""
from kivy.utils import platform

DEFAULT_SERVER = "http://10.0.2.2:8000" if platform == "android" else "http://127.0.0.1:8000"
API_PREFIX = "/api/v1"
REQUEST_TIMEOUT = 15
PAGE_SIZE = 20
RESEND_COOLDOWN = 30  # секунд между повторными отправками кода

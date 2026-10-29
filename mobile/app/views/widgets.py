"""Переиспользуемые виджеты: верхняя панель, строки списков, окно подтверждения, всплывающее сообщение."""
from kivy.animation import Animation
from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.recycleview.views import RecycleDataViewBehavior


class TopBar(BoxLayout):
    title = StringProperty("")
    show_back = BooleanProperty(False)
    show_logout = BooleanProperty(False)
    action_text = StringProperty("")

    def __init__(self, **kwargs):
        self.register_event_type("on_action")
        super().__init__(**kwargs)

    def on_action(self, *_):
        pass


class ItemRow(RecycleDataViewBehavior, ButtonBehavior, BoxLayout):
    item_id = NumericProperty(0)
    title = StringProperty("")
    subtitle = StringProperty("")
    qty = StringProperty("")

    def on_release(self):
        App.get_running_app().open_item(self.item_id)


class UserRow(BoxLayout):
    user_id = NumericProperty(0)
    title = StringProperty("")
    subtitle = StringProperty("")
    role_title = StringProperty("")
    role_values = ListProperty([])
    active = BooleanProperty(True)
    is_self = BooleanProperty(False)
    screen = ObjectProperty(None, allownone=True)

    def on_role_selected(self, title):
        if self.screen and title and title != self.role_title:
            self.screen.change_role(self, title)

    def toggle_active(self):
        if self.screen:
            self.screen.toggle_active(self)


class ConfirmPopup(Popup):
    message = StringProperty("")
    confirm_text = StringProperty("Удалить")
    callback = ObjectProperty(None, allownone=True)  # не "on_*": такие kwargs Kivy считает событиями

    def confirm(self):
        self.dismiss()
        if self.callback:
            self.callback()


def confirm(title: str, message: str, on_confirm, confirm_text="Удалить"):
    ConfirmPopup(title=title, message=message, callback=on_confirm, confirm_text=confirm_text).open()


def toast(text: str, duration: float = 2.2):
    """Короткое уведомление внизу экрана (аналог Android Toast)."""
    lbl = Label(text=text, size_hint=(None, None), font_size="15sp", color=(1, 1, 1, 1),
                halign="center", padding=(dp(16), dp(10)))
    lbl.text_size = (min(Window.width - dp(48), dp(420)), None)
    lbl.texture_update()
    lbl.size = lbl.texture_size
    lbl.pos = ((Window.width - lbl.width) / 2, dp(48))
    from kivy.graphics import Color, RoundedRectangle
    with lbl.canvas.before:
        Color(0.11, 0.14, 0.2, 0.92)
        rect = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(10)])
    lbl.bind(pos=lambda w, p: setattr(rect, "pos", p), size=lambda w, s: setattr(rect, "size", s))
    Window.add_widget(lbl)
    anim = Animation(opacity=1, duration=duration) + Animation(opacity=0, duration=0.4)
    anim.bind(on_complete=lambda *_: Window.remove_widget(lbl))
    anim.start(lbl)

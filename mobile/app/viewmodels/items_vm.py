"""ViewModel'и ТМЦ: список (поиск/фильтр/сортировка/пагинация), карточка, форма."""
from decimal import Decimal, InvalidOperation

from kivy.properties import BooleanProperty, DictProperty, ListProperty, NumericProperty, StringProperty

from app.config import PAGE_SIZE
from app.viewmodels.base import BaseViewModel

ALL_CATEGORIES = "Все категории"
NO_CATEGORY = "— без категории —"
NO_RESPONSIBLE = "— не назначен —"

SORT_OPTIONS = {
    "Сначала новые": ("updated_at", "desc"),
    "По названию А–Я": ("name", "asc"),
    "По названию Я–А": ("name", "desc"),
    "По инв. номеру": ("inventory_number", "asc"),
    "Количество ↑": ("quantity", "asc"),
    "Количество ↓": ("quantity", "desc"),
    "Цена ↓": ("price", "desc"),
}


class ReferenceData(BaseViewModel):
    """Справочники для форм и фильтров: категории и пользователи."""
    categories = ListProperty([])  # [{id, name}]
    users = ListProperty([])       # [{id, username, full_name}]

    def load(self, on_done=None):
        def fetch():
            cats = self.api.categories()
            try:
                users = self.api.users_short()
            except Exception:
                users = []
            return cats, users

        def ok(res):
            self.categories, self.users = res
            if on_done:
                on_done()

        self.call(fetch, ok)

    def category_names(self, with_all=False, with_none=False):
        names = [c["name"] for c in self.categories]
        if with_all:
            names = [ALL_CATEGORIES] + names
        if with_none:
            names = [NO_CATEGORY] + names
        return names

    def category_id(self, name):
        return next((c["id"] for c in self.categories if c["name"] == name), None)

    @staticmethod
    def user_label(u):
        return f"{u['full_name']} ({u['username']})" if u.get("full_name") else u["username"]

    def user_names(self):
        return [NO_RESPONSIBLE] + [self.user_label(u) for u in self.users]

    def user_id(self, label):
        return next((u["id"] for u in self.users if self.user_label(u) == label), None)


class ItemsListViewModel(BaseViewModel):
    items = ListProperty([])
    total = NumericProperty(0)
    search = StringProperty("")
    category_name = StringProperty(ALL_CATEGORIES)
    sort_name = StringProperty("Сначала новые")
    has_more = BooleanProperty(False)

    def __init__(self, api, refs: ReferenceData, **kwargs):
        super().__init__(api, **kwargs)
        self.refs = refs

    def reload(self):
        self._load(reset=True)

    def load_more(self):
        if self.has_more and not self.busy:
            self._load(reset=False)

    def _load(self, reset: bool):
        skip = 0 if reset else len(self.items)
        sort, order = SORT_OPTIONS.get(self.sort_name, ("updated_at", "desc"))
        cat_id = None if self.category_name == ALL_CATEGORIES else self.refs.category_id(self.category_name)
        search = self.search.strip() or None

        def ok(data):
            self.items = (data["items"] if reset else list(self.items) + data["items"])
            self.total = data["total"]
            self.has_more = len(self.items) < self.total

        self.call(lambda: self.api.list_items(search=search, category_id=cat_id, sort=sort,
                                              order=order, skip=skip, limit=PAGE_SIZE), ok)


class ItemDetailViewModel(BaseViewModel):
    item = DictProperty({})
    history = ListProperty([])

    def load(self, item_id: int, with_history: bool):
        def fetch():
            item = self.api.get_item(item_id)
            hist = self.api.item_history(item_id) if with_history else []
            return item, hist

        def ok(res):
            self.item, self.history = res

        self.item = {}
        self.history = []
        self.call(fetch, ok)

    def delete(self, on_done):
        item_id = self.item.get("id")
        self.call(lambda: self.api.delete_item(item_id), lambda _r: on_done())


class ItemFormViewModel(BaseViewModel):
    """Создание и редактирование. В режиме редактирования отправляются только изменённые поля (PATCH)."""
    mode = StringProperty("create")  # create | edit
    original = DictProperty({})

    REQUIRED = ("name", "inventory_number")

    def start_create(self):
        self.mode, self.original, self.error = "create", {}, ""

    def start_edit(self, item: dict):
        self.mode, self.original, self.error = "edit", dict(item), ""

    def validate(self, form: dict) -> dict | None:
        """form — сырые строки из полей. Возвращает данные для API или None (и выставляет error)."""
        problems, data = [], {}
        name = form["name"].strip()
        number = form["inventory_number"].strip()
        if not name:
            problems.append("• укажите наименование")
        if not number:
            problems.append("• укажите инвентарный номер")
        try:
            qty = int(form["quantity"].strip() or "0")
            if qty < 0:
                raise ValueError
        except ValueError:
            problems.append("• количество — целое число ≥ 0")
            qty = 0
        try:
            price = Decimal(form["price"].strip().replace(",", ".") or "0")
            if price < 0 or price.as_tuple().exponent < -2:
                raise InvalidOperation
        except InvalidOperation:
            problems.append("• цена — число ≥ 0, не более 2 знаков после запятой")
            price = Decimal("0")
        if problems:
            self.error = "Проверьте данные:\n" + "\n".join(problems)
            return None
        data.update(name=name, inventory_number=number, unit=form["unit"].strip() or "шт",
                    quantity=qty, price=str(price.quantize(Decimal("0.01"))),
                    location=form["location"].strip(), description=form["description"].strip(),
                    category_id=form["category_id"], responsible_id=form["responsible_id"])
        return data

    def diff(self, data: dict) -> dict:
        o = self.original
        current = {
            "name": o.get("name"), "inventory_number": o.get("inventory_number"), "unit": o.get("unit"),
            "quantity": o.get("quantity"), "price": str(Decimal(str(o.get("price", "0"))).quantize(Decimal("0.01"))),
            "location": o.get("location"), "description": o.get("description"),
            "category_id": (o.get("category") or {}).get("id"),
            "responsible_id": (o.get("responsible") or {}).get("id"),
        }
        return {k: v for k, v in data.items() if current.get(k) != v}

    def save(self, form: dict, allowed_fields: set | None, on_saved):
        data = self.validate(form)
        if data is None:
            return
        if self.mode == "create":
            self.call(lambda: self.api.create_item(data), on_saved)
            return
        changes = self.diff(data)
        if allowed_fields is not None:
            changes = {k: v for k, v in changes.items() if k in allowed_fields}
        if not changes:
            self.error = "Нет изменений для сохранения"
            return
        item_id = self.original["id"]
        self.call(lambda: self.api.update_item(item_id, changes), on_saved)

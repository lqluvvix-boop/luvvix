"""Репозиторий ТМЦ и категорий: CRUD, поиск, фильтрация, сортировка, пагинация — всё через ORM."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Category, InventoryItem, ItemHistory

SORT_FIELDS = {
    "name": InventoryItem.name,
    "inventory_number": InventoryItem.inventory_number,
    "quantity": InventoryItem.quantity,
    "price": InventoryItem.price,
    "created_at": InventoryItem.created_at,
    "updated_at": InventoryItem.updated_at,
}


class ItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, item_id: int) -> InventoryItem | None:
        return self.db.get(InventoryItem, item_id)

    def get_by_number(self, number: str) -> InventoryItem | None:
        stmt = select(InventoryItem).where(func.lower(InventoryItem.inventory_number) == number.lower())
        return self.db.scalars(stmt).first()

    def list(self, *, search: str | None, category_id: int | None, responsible_id: int | None,
             sort: str, order: str, skip: int, limit: int) -> tuple[list[InventoryItem], int]:
        stmt = select(InventoryItem)
        if search:
            like = f"%{search.strip().lower()}%"
            stmt = stmt.where(or_(
                func.lower(InventoryItem.name).like(like),
                func.lower(InventoryItem.inventory_number).like(like),
                func.lower(InventoryItem.location).like(like),
            ))
        if category_id is not None:
            stmt = stmt.where(InventoryItem.category_id == category_id)
        if responsible_id is not None:
            stmt = stmt.where(InventoryItem.responsible_id == responsible_id)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        column = SORT_FIELDS.get(sort, InventoryItem.updated_at)
        stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), InventoryItem.id)
        items = list(self.db.scalars(stmt.offset(skip).limit(limit)).unique())
        return items, total

    def add(self, item: InventoryItem) -> InventoryItem:
        self.db.add(item)
        self.db.flush()
        return item

    def delete(self, item: InventoryItem) -> None:
        self.db.delete(item)

    def add_history(self, entry: ItemHistory) -> None:
        self.db.add(entry)

    def history(self, item_id: int, limit: int = 50) -> list[ItemHistory]:
        stmt = (select(ItemHistory).where(ItemHistory.item_id == item_id)
                .order_by(ItemHistory.created_at.desc(), ItemHistory.id.desc()).limit(limit))
        return list(self.db.scalars(stmt).unique())


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, category_id: int) -> Category | None:
        return self.db.get(Category, category_id)

    def get_by_name(self, name: str) -> Category | None:
        return self.db.scalars(select(Category).where(func.lower(Category.name) == name.lower())).first()

    def list(self) -> list[Category]:
        return list(self.db.scalars(select(Category).order_by(Category.name)))

    def add(self, category: Category) -> Category:
        self.db.add(category)
        self.db.flush()
        return category

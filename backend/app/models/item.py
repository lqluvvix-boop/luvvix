"""Основная сущность — ТМЦ (InventoryItem), категории и история изменений."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, utcnow


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    items: Mapped[list["InventoryItem"]] = relationship(back_populates="category")


class InventoryItem(TimestampMixin, Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    inventory_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="шт")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    location: Mapped[str] = mapped_column(String(150), default="")
    description: Mapped[str] = mapped_column(Text, default="")

    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    responsible_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    category: Mapped[Category | None] = relationship(back_populates="items", lazy="joined")
    responsible: Mapped["User | None"] = relationship(foreign_keys=[responsible_id], lazy="joined")  # noqa: F821
    created_by: Mapped["User | None"] = relationship(foreign_keys=[created_by_id])  # noqa: F821
    history: Mapped[list["ItemHistory"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", order_by="ItemHistory.created_at.desc()"
    )


class ItemHistory(Base):
    """Журнал операций над ТМЦ (Vision: «Ведение истории изменений и операций»)."""

    __tablename__ = "item_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # create / update
    changes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    item: Mapped[InventoryItem] = relationship(back_populates="history")
    user: Mapped["User | None"] = relationship(lazy="joined")  # noqa: F821

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import UserShort


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class _ItemFields(BaseModel):
    @field_validator("name", "inventory_number", check_fields=False)
    @classmethod
    def _strip(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Поле не может быть пустым")
        return v


class ItemCreate(_ItemFields):
    name: str = Field(min_length=1, max_length=200, examples=["Ноутбук Lenovo"])
    inventory_number: str = Field(min_length=1, max_length=50, examples=["INV-0001"])
    unit: str = Field(default="шт", max_length=20)
    quantity: int = Field(default=1, ge=0, le=1_000_000)
    price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    location: str = Field(default="", max_length=150)
    description: str = Field(default="", max_length=2000)
    category_id: int | None = None
    responsible_id: int | None = None


class ItemUpdate(_ItemFields):
    """PATCH: передаются только изменяемые поля."""
    name: str | None = Field(default=None, min_length=1, max_length=200)
    inventory_number: str | None = Field(default=None, min_length=1, max_length=50)
    unit: str | None = Field(default=None, max_length=20)
    quantity: int | None = Field(default=None, ge=0, le=1_000_000)
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    location: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    category_id: int | None = None
    responsible_id: int | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    inventory_number: str
    unit: str
    quantity: int
    price: Decimal
    location: str
    description: str
    category: CategoryOut | None
    responsible: UserShort | None
    created_at: datetime
    updated_at: datetime


class ItemListOut(BaseModel):
    items: list[ItemOut]
    total: int
    skip: int
    limit: int


class HistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    action: str
    changes: str
    created_at: datetime
    user: UserShort | None

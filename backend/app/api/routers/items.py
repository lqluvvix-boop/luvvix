from typing import Annotated, Literal

from fastapi import APIRouter, Query, Response, status

from app.api.deps import ItemSvc, require, require_any
from app.api.responses import E401, E403, E404, E409, errors
from app.models import User
from app.schemas.item import HistoryOut, ItemCreate, ItemListOut, ItemOut, ItemUpdate

router = APIRouter(prefix="/items", tags=["ТМЦ (основная сущность)"])


@router.get("", response_model=ItemListOut, responses=errors(E401, E403),
            summary="Список ТМЦ с поиском, фильтрацией и пагинацией")
def list_items(
    svc: ItemSvc,
    _: Annotated[User, require("items:read")],
    search: Annotated[str | None, Query(max_length=100, description="Поиск по названию, номеру, месту")] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    responsible_id: Annotated[int | None, Query(ge=1)] = None,
    sort: Annotated[str, Query(description="name | inventory_number | quantity | price | created_at | updated_at")]
    = "updated_at",
    order: Literal["asc", "desc"] = "desc",
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    return svc.list(search=search, category_id=category_id, responsible_id=responsible_id,
                    sort=sort, order=order, skip=skip, limit=limit)


@router.get("/{item_id}", response_model=ItemOut, responses=errors(E401, E403, E404),
            summary="Получить одну ТМЦ")
def get_item(item_id: int, svc: ItemSvc, _: Annotated[User, require("items:read")]):
    return svc.get(item_id)


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED,
             responses=errors(E401, E403, E409), summary="Создать ТМЦ")
def create_item(data: ItemCreate, svc: ItemSvc, user: Annotated[User, require("items:create")]):
    return svc.create(data, user)


@router.patch("/{item_id}", response_model=ItemOut, responses=errors(E401, E403, E404, E409),
              summary="Изменить ТМЦ (частично)")
def update_item(item_id: int, data: ItemUpdate, svc: ItemSvc,
                user: Annotated[User, require_any("items:update", "items:update_fact")]):
    """Бухгалтер/администратор (`items:update`) меняют любые поля.
    Кладовщик (`items:update_fact`) — только quantity, location, description."""
    return svc.update(item_id, data, user)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT,
               responses=errors(E401, E403, E404), summary="Удалить ТМЦ")
def delete_item(item_id: int, svc: ItemSvc, _: Annotated[User, require("items:delete")]):
    svc.delete(item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{item_id}/history", response_model=list[HistoryOut], responses=errors(E401, E403, E404),
            summary="История изменений ТМЦ")
def item_history(item_id: int, svc: ItemSvc, _: Annotated[User, require("history:read")]):
    return svc.history(item_id)

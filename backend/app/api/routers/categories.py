from typing import Annotated

from fastapi import APIRouter, status

from app.api.deps import ItemSvc, require
from app.api.responses import E401, E403, E409, errors
from app.models import User
from app.schemas.item import CategoryIn, CategoryOut

router = APIRouter(prefix="/categories", tags=["Категории"])


@router.get("", response_model=list[CategoryOut], responses=errors(E401, E403), summary="Список категорий")
def list_categories(svc: ItemSvc, _: Annotated[User, require("items:read")]):
    return svc.list_categories()


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED,
             responses=errors(E401, E403, E409), summary="Создать категорию")
def create_category(data: CategoryIn, svc: ItemSvc, _: Annotated[User, require("categories:manage")]):
    return svc.create_category(data)

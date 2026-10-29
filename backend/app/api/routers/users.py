from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict

from app.api.deps import UserSvc, require
from app.api.responses import E401, E403, E404, errors
from app.models import User
from app.schemas.user import UserAdminUpdate, UserOut, UserShort

router = APIRouter(tags=["Пользователи и роли"])


class RoleWithPerms(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    title: str
    permission_codes: list[str]


@router.get("/users/short", response_model=list[UserShort], responses=errors(E401, E403),
            summary="Краткий список пользователей (выбор ответственного)")
def users_short(svc: UserSvc, _: Annotated[User, require("users:read")]):
    return [u for u in svc.list() if u.is_active]


@router.get("/users", response_model=list[UserOut], responses=errors(E401, E403),
            summary="Все пользователи (администратор)")
def list_users(svc: UserSvc, _: Annotated[User, require("users:manage")],
               search: Annotated[str | None, Query(max_length=100)] = None):
    return svc.list(search)


@router.patch("/users/{user_id}", response_model=UserOut, responses=errors(E401, E403, E404),
              summary="Сменить роль / заблокировать пользователя")
def update_user(user_id: int, data: UserAdminUpdate, svc: UserSvc,
                actor: Annotated[User, require("users:manage")]):
    return svc.update(user_id, data, actor)


@router.get("/roles", response_model=list[RoleWithPerms], responses=errors(E401, E403),
            summary="Роли и их права")
def list_roles(svc: UserSvc, _: Annotated[User, require("users:read")]):
    return [RoleWithPerms(name=r.name, title=r.title, permission_codes=sorted(p.code for p in r.permissions))
            for r in svc.list_roles()]

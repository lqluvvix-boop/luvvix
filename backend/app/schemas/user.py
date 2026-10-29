from pydantic import BaseModel, ConfigDict, Field


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    title: str


class UserShort(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    full_name: str
    is_active: bool
    is_email_verified: bool
    role: RoleOut
    permissions: list[str]


class UserAdminUpdate(BaseModel):
    """PATCH /users/{id} — изменение роли и блокировка (только администратор)."""
    role: str | None = Field(default=None, examples=["accountant"])
    is_active: bool | None = None

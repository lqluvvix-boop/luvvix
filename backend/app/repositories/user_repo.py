"""Репозиторий пользователей и ролей — только доступ к данным через ORM (select)."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Permission, Role, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_login(self, login: str) -> User | None:
        login = login.strip().lower()
        stmt = select(User).where(or_(func.lower(User.username) == login, func.lower(User.email) == login))
        return self.db.scalars(stmt).first()

    def exists(self, username: str, email: str) -> tuple[bool, bool]:
        u = self.db.scalar(select(func.count()).select_from(User).where(func.lower(User.username) == username.lower()))
        e = self.db.scalar(select(func.count()).select_from(User).where(func.lower(User.email) == email.lower()))
        return bool(u), bool(e)

    def list(self, search: str | None = None) -> list[User]:
        stmt = select(User).order_by(User.id)
        if search:
            like = f"%{search.lower()}%"
            stmt = stmt.where(or_(func.lower(User.username).like(like), func.lower(User.full_name).like(like)))
        return list(self.db.scalars(stmt).unique())

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user


class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str) -> Role | None:
        return self.db.scalars(select(Role).where(Role.name == name)).first()

    def list(self) -> list[Role]:
        return list(self.db.scalars(select(Role).order_by(Role.id)))

    def get_or_create_permission(self, code: str, description: str = "") -> Permission:
        perm = self.db.scalars(select(Permission).where(Permission.code == code)).first()
        if perm is None:
            perm = Permission(code=code, description=description)
            self.db.add(perm)
            self.db.flush()
        return perm

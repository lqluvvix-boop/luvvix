"""Создание таблиц и начальных данных: права, роли, категории, первый администратор."""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.db.uow import transaction
from app.models import Category, Role, User
from app.repositories.item_repo import CategoryRepository
from app.repositories.user_repo import RoleRepository, UserRepository

PERMISSIONS = {
    "items:read": "Просмотр ТМЦ",
    "items:create": "Создание ТМЦ",
    "items:update": "Редактирование всех полей ТМЦ",
    "items:update_fact": "Изменение фактических данных ТМЦ (количество, место, примечание)",
    "items:delete": "Удаление ТМЦ",
    "categories:manage": "Управление категориями",
    "history:read": "Просмотр истории изменений",
    "users:read": "Просмотр списка пользователей",
    "users:manage": "Управление пользователями и ролями",
}

ROLES = {
    "admin": ("Администратор", list(PERMISSIONS)),
    "accountant": ("Бухгалтер", ["items:read", "items:create", "items:update", "items:delete",
                                "categories:manage", "history:read", "users:read"]),
    "storekeeper": ("Кладовщик", ["items:read", "items:update_fact", "history:read", "users:read"]),
    "manager": ("Руководитель", ["items:read", "history:read", "users:read"]),
}
DEFAULT_ROLE = "storekeeper"  # роль при самостоятельной регистрации (минимальные права)

CATEGORIES = ["Оборудование", "Мебель", "Инструменты", "Оргтехника", "Расходные материалы"]


def seed(db: Session) -> None:
    roles_repo = RoleRepository(db)
    with transaction(db):
        perms = {code: roles_repo.get_or_create_permission(code, desc) for code, desc in PERMISSIONS.items()}
        for name, (title, codes) in ROLES.items():
            role = roles_repo.get_by_name(name)
            if role is None:
                role = Role(name=name, title=title)
                db.add(role)
            role.permissions = [perms[c] for c in codes]

        cat_repo = CategoryRepository(db)
        for cname in CATEGORIES:
            if cat_repo.get_by_name(cname) is None:
                cat_repo.add(Category(name=cname))

    users = UserRepository(db)
    if users.get_by_login(settings.ADMIN_USERNAME) is None:
        with transaction(db):
            users.add(User(
                username=settings.ADMIN_USERNAME.lower(),
                email=settings.ADMIN_EMAIL.lower(),
                full_name="Администратор системы",
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                is_email_verified=True,
                role=roles_repo.get_by_name("admin"),
            ))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()

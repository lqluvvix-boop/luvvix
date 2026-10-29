"""Единица работы: commit при успехе, rollback при любой ошибке."""
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError


@contextmanager
def transaction(db: Session, conflict_message: str = "Конфликт данных"):
    try:
        yield
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(conflict_message) from exc
    except Exception:
        db.rollback()
        raise

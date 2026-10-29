from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import RefreshToken, VerificationCode


class TokenRepository:
    def __init__(self, db: Session):
        self.db = db

    # refresh-токены
    def add_refresh(self, token: RefreshToken) -> None:
        self.db.add(token)

    def get_refresh_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.db.scalars(select(RefreshToken).where(RefreshToken.token_hash == token_hash)).first()

    def revoke_family(self, family: str) -> None:
        self.db.execute(update(RefreshToken).where(RefreshToken.family == family).values(revoked=True))

    def revoke_all_for_user(self, user_id: int) -> None:
        self.db.execute(update(RefreshToken).where(RefreshToken.user_id == user_id).values(revoked=True))

    # коды 2FA
    def add_code(self, code: VerificationCode) -> None:
        self.db.add(code)

    def get_code(self, challenge_id: str) -> VerificationCode | None:
        return self.db.scalars(select(VerificationCode).where(VerificationCode.challenge_id == challenge_id)).first()

    def latest_active_code(self, user_id: int) -> VerificationCode | None:
        stmt = (select(VerificationCode)
                .where(VerificationCode.user_id == user_id, VerificationCode.used.is_(False))
                .order_by(VerificationCode.id.desc()))
        return self.db.scalars(stmt).first()

    def invalidate_codes(self, user_id: int, purpose) -> None:
        self.db.execute(
            update(VerificationCode)
            .where(VerificationCode.user_id == user_id, VerificationCode.purpose == purpose,
                   VerificationCode.used.is_(False))
            .values(used=True)
        )

    def purge_expired(self, now: datetime) -> None:
        self.db.execute(update(VerificationCode).where(VerificationCode.expires_at < now).values(used=True))

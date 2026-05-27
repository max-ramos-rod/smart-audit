from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repositories import SQLAlchemyRepository
from app.db.models.password_reset_tokens import PasswordResetToken
from app.db.models.users import User


class AuthRepository(SQLAlchemyRepository[User]):
    model = User

    async def get_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return await self._get_one(db, statement)

    async def get_user_by_id(self, db: AsyncSession, user_id: str) -> User | None:
        statement = select(User).where(User.id == user_id)
        return await self._get_one(db, statement)

    async def create_reset_token(
        self, db: AsyncSession, reset_token: PasswordResetToken
    ) -> PasswordResetToken:
        return await self._save(db, reset_token)

    async def get_valid_reset_token(
        self, db: AsyncSession, token: str, now: datetime
    ) -> PasswordResetToken | None:
        statement = (
            select(PasswordResetToken)
            .where(
                PasswordResetToken.token == token,
                PasswordResetToken.expires_at > now,
                PasswordResetToken.used_at.is_(None),
            )
            .options(selectinload(PasswordResetToken.user))
        )
        return await self._get_one(db, statement)

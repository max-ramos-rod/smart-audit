from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repositories import SQLAlchemyRepository
from app.db.models.users import User


class AuthRepository(SQLAlchemyRepository[User]):
    model = User

    async def get_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return await self._get_one(db, statement)

    async def get_user_by_id(self, db: AsyncSession, user_id: str) -> User | None:
        statement = select(User).where(User.id == user_id)
        return await self._get_one(db, statement)

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.companies import Company
from app.db.models.memberships import Membership
from app.db.models.users import User


class UserRepository(SQLAlchemyRepository[User]):
    model = User

    async def list_users_by_company(
        self, db: AsyncSession, company_id: str, params: PaginationParams
    ) -> tuple[list[Membership], int]:
        statement = (
            select(Membership)
            .where(Membership.company_id == company_id, Membership.revoked_at.is_(None))
            .options(selectinload(Membership.user), selectinload(Membership.company))
            .order_by(User.name.asc())
            .join(Membership.user)
        )
        return await self._paginate_select(db, statement, params)

    async def get_company_user(
        self, db: AsyncSession, company_id: str, user_id: str
    ) -> Membership | None:
        statement = (
            select(Membership)
            .where(
                Membership.company_id == company_id,
                Membership.user_id == user_id,
                Membership.revoked_at.is_(None),
            )
            .options(selectinload(Membership.user), selectinload(Membership.company))
        )
        return await self._get_one(db, statement)

    async def get_user_by_email(self, db: AsyncSession, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return await self._get_one(db, statement)

    async def create_user(self, db: AsyncSession, user: User) -> User:
        return await self._save(db, user)

    async def create_membership(self, db: AsyncSession, membership: Membership) -> Membership:
        return await self._save(db, membership)

    async def get_company_by_id(self, db: AsyncSession, company_id: str) -> Company | None:
        statement = select(Company).where(Company.id == company_id)
        return await self._get_one(db, statement)

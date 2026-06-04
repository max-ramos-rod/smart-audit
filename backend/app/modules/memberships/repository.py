from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repositories import SQLAlchemyRepository
from app.db.models.memberships import Membership


class MembershipRepository(SQLAlchemyRepository[Membership]):
    model = Membership

    async def list_by_user_id(self, db: AsyncSession, user_id: str) -> list[Membership]:
        statement = (
            select(Membership)
            .where(Membership.user_id == user_id, Membership.revoked_at.is_(None))
            .options(selectinload(Membership.company))
        )
        return await self._list_from_stmt(db, statement)

    async def get_by_user_and_company(
        self, db: AsyncSession, user_id: str, company_id: str
    ) -> Membership | None:
        statement = select(Membership).where(
            Membership.user_id == user_id,
            Membership.company_id == company_id,
            Membership.revoked_at.is_(None),
        )
        return await self._get_one(db, statement)

    async def revoke(self, db: AsyncSession, membership: Membership) -> None:
        membership.revoked_at = datetime.now(UTC)
        await self._save(db, membership)

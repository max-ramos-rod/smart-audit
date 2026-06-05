from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repositories import SQLAlchemyRepository
from app.db.models.companies import Company
from app.db.models.forms import Form
from app.db.models.memberships import Membership
from app.db.models.submissions import Submission
from app.db.models.teams import Team


class CompanyRepository(SQLAlchemyRepository[Company]):
    model = Company

    async def get_by_id(self, db: AsyncSession, company_id: str) -> Company | None:
        statement = select(Company).where(Company.id == company_id)
        return await self._get_one(db, statement)

    async def update_company(self, db: AsyncSession, company: Company, data: dict) -> Company:
        return await self.update_fields(db, company, data)

    async def deactivate_company(self, db: AsyncSession, company_id: str) -> None:
        """Soft-delete: deactivate company + cascade to memberships and teams."""
        await db.execute(
            update(Company)
            .where(Company.id == company_id)
            .values(is_active=False)
        )
        await db.execute(
            update(Membership)
            .where(Membership.company_id == company_id, Membership.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await db.execute(
            update(Team)
            .where(Team.company_id == company_id, Team.is_active.is_(True))
            .values(is_active=False)
        )

    async def count_members(self, db: AsyncSession, company_id: str) -> int:
        result = await db.scalar(
            select(func.count()).where(
                Membership.company_id == company_id,
                Membership.revoked_at.is_(None),
            )
        )
        return result or 0

    async def count_forms(self, db: AsyncSession, company_id: str) -> int:
        result = await db.scalar(
            select(func.count()).where(Form.company_id == company_id, Form.is_active.is_(True))
        )
        return result or 0

    async def count_submissions_this_month(self, db: AsyncSession, company_id: str) -> int:
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await db.scalar(
            select(func.count()).where(
                Submission.company_id == company_id,
                Submission.created_at >= month_start,
            )
        )
        return result or 0

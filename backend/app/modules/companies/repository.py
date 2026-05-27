from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repositories import SQLAlchemyRepository
from app.db.models.companies import Company


class CompanyRepository(SQLAlchemyRepository[Company]):
    model = Company

    async def get_by_id(self, db: AsyncSession, company_id: str) -> Company | None:
        statement = select(Company).where(Company.id == company_id)
        return await self._get_one(db, statement)

    async def update_company(self, db: AsyncSession, company: Company, data: dict) -> Company:
        return await self.update_fields(db, company, data)

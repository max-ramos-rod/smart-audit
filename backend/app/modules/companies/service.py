from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memberships import Membership
from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import CompanyResponse, CompanyUpdateRequest


class CompanyService:
    def __init__(self, repository: CompanyRepository | None = None) -> None:
        self.repository = repository or CompanyRepository()

    async def get_company(self, db: AsyncSession, membership: Membership) -> CompanyResponse:
        company = await self.repository.get_by_id(db, str(membership.company_id))
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa nao encontrada.")
        return self._serialize(company)

    async def update_company(
        self,
        db: AsyncSession,
        membership: Membership,
        payload: CompanyUpdateRequest,
    ) -> CompanyResponse:
        company = await self.repository.get_by_id(db, str(membership.company_id))
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa nao encontrada.")

        data = payload.model_dump(exclude_none=True)
        if data:
            await self.repository.update_company(db, company, data)
            await db.commit()

        company = await self.repository.get_by_id(db, str(membership.company_id))
        return self._serialize(company)

    @staticmethod
    def _serialize(company) -> CompanyResponse:
        return CompanyResponse(
            id=str(company.id),
            name=company.name,
            slug=company.slug,
            plan=company.plan,
            is_active=company.is_active,
            cnpj=company.cnpj,
            timezone=company.timezone,
            contact_email=company.contact_email,
            phone=company.phone,
        )

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memberships import Membership
from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import CompanyResponse, CompanyUpdateRequest, UsageResponse, UsageStat


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

    # Limits per plan. Unknown plans fall back to "starter".
    _PLAN_LIMITS: dict[str, dict[str, int]] = {
        "starter":    {"users": 10,  "forms": 20,  "submissions": 100},
        "pro":        {"users": 50,  "forms": 100, "submissions": 500},
        "enterprise": {"users": 999, "forms": 999, "submissions": 9999},
    }
    _DEFAULT_LIMITS = {"users": 10, "forms": 20, "submissions": 100}

    async def get_usage(self, db: AsyncSession, membership: Membership) -> UsageResponse:
        cid = str(membership.company_id)
        company = await self.repository.get_by_id(db, cid)
        plan = (company.plan if company else "starter") or "starter"
        limits = self._PLAN_LIMITS.get(plan, self._DEFAULT_LIMITS)

        users_used, forms_used, subs_used = (
            await self.repository.count_members(db, cid),
            await self.repository.count_forms(db, cid),
            await self.repository.count_submissions_this_month(db, cid),
        )
        return UsageResponse(
            users=UsageStat(used=users_used, limit=limits["users"]),
            forms=UsageStat(used=forms_used, limit=limits["forms"]),
            submissions_this_month=UsageStat(used=subs_used, limit=limits["submissions"]),
        )

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

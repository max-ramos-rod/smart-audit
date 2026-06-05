from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_response
from app.db.models.memberships import Membership
from app.db.session import get_db
from app.modules.companies.schemas import CompanyUpdateRequest
from app.modules.companies.service import CompanyService
from app.modules.memberships.dependencies import get_current_membership
from app.modules.memberships.permissions import get_admin_membership, get_owner_membership

router = APIRouter(prefix="/companies", tags=["companies"])


def get_company_service() -> CompanyService:
    return CompanyService()


@router.get("/me")
async def get_my_company(
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    service: CompanyService = Depends(get_company_service),
) -> dict[str, object]:
    data = await service.get_company(db, membership)
    return success_response(data.model_dump(mode="json"))


@router.patch("/me")
async def update_my_company(
    payload: CompanyUpdateRequest,
    membership: Membership = Depends(get_admin_membership),
    db: AsyncSession = Depends(get_db),
    service: CompanyService = Depends(get_company_service),
) -> dict[str, object]:
    data = await service.update_company(db, membership, payload)
    return success_response(data.model_dump(mode="json"))


@router.delete("/me")
async def deactivate_my_company(
    membership: Membership = Depends(get_owner_membership),
    db: AsyncSession = Depends(get_db),
    service: CompanyService = Depends(get_company_service),
) -> dict[str, object]:
    await service.deactivate_company(db, membership)
    return success_response(None)

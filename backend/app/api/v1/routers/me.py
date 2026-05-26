from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_response
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.memberships.dependencies import get_current_membership
from app.modules.memberships.service import MembershipService
from app.modules.submissions.service import SubmissionService

router = APIRouter(prefix="/me", tags=["me"])


def get_membership_service() -> MembershipService:
    return MembershipService()


def get_submission_service() -> SubmissionService:
    return SubmissionService()


@router.get("/companies")
async def list_my_companies(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    membership_service: MembershipService = Depends(get_membership_service),
) -> dict[str, object]:
    data = await membership_service.list_user_companies(db, current_user)
    return success_response([item.model_dump(mode="json") for item in data])


@router.get("/context")
async def get_my_context(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    membership_service: MembershipService = Depends(get_membership_service),
    company_id: str | None = Header(default=None, alias="X-Company-Id"),
) -> dict[str, object]:
    data = await membership_service.get_user_context(db, current_user, company_id)
    return success_response(data.model_dump(mode="json"))


@router.get("/stats")
async def get_my_stats(
    membership=Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> dict[str, object]:
    data = await submission_service.get_company_stats(db, membership)
    return success_response(data.model_dump(mode="json"))

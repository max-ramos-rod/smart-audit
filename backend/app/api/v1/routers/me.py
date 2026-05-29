from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success_response
from app.db.models.users import User
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.memberships.dependencies import get_current_membership
from app.modules.memberships.schemas import MeUpdateRequest
from app.modules.memberships.service import MembershipService
from app.modules.notifications.repository import NotificationReadRepository
from app.modules.notifications.schemas import MarkAllReadRequest, MarkReadRequest
from app.modules.submissions.service import SubmissionService

router = APIRouter(prefix="/me", tags=["me"])


def get_membership_service() -> MembershipService:
    return MembershipService()


def get_submission_service() -> SubmissionService:
    return SubmissionService()


def get_notification_read_repository() -> NotificationReadRepository:
    return NotificationReadRepository()


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


@router.patch("")
async def update_me(
    payload: MeUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    membership_service: MembershipService = Depends(get_membership_service),
) -> dict[str, object]:
    data = await membership_service.update_me(db, current_user, payload)
    return success_response(data.model_dump(mode="json"))


@router.get("/stats")
async def get_my_stats(
    period: str | None = Query(default=None),
    membership=Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
) -> dict[str, object]:
    data = await submission_service.get_company_stats(db, membership, period=period)
    return success_response(data.model_dump(mode="json"))


@router.get("/notifications")
async def get_my_notifications(
    current_user: User = Depends(get_current_user),
    membership=Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    submission_service: SubmissionService = Depends(get_submission_service),
    notif_repo: NotificationReadRepository = Depends(get_notification_read_repository),
) -> dict[str, object]:
    read_keys = await notif_repo.get_read_keys(db, str(current_user.id))
    data = await submission_service.get_notifications(db, membership, read_keys=read_keys)
    return success_response([item.model_dump(mode="json") for item in data])


@router.post("/notifications/read")
async def mark_notification_read(
    payload: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    notif_repo: NotificationReadRepository = Depends(get_notification_read_repository),
) -> dict[str, object]:
    await notif_repo.mark_read(db, str(current_user.id), payload.key)
    await db.commit()
    return success_response({"key": payload.key, "read": True})


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    payload: MarkAllReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    notif_repo: NotificationReadRepository = Depends(get_notification_read_repository),
) -> dict[str, object]:
    await notif_repo.mark_many_read(db, str(current_user.id), payload.keys)
    await db.commit()
    return success_response({"marked": len(payload.keys)})

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.responses import paginated_response, success_response
from app.db.models.memberships import Membership
from app.db.models.users import User
from app.db.session import get_db
from app.modules.attachments.schemas import AttachmentCreateRequest
from app.modules.attachments.service import AttachmentService
from app.modules.auth.dependencies import get_current_user
from app.modules.memberships.dependencies import get_current_membership

router = APIRouter(prefix="/submissions/{submission_id}/attachments", tags=["attachments"])


def get_attachment_service() -> AttachmentService:
    return AttachmentService()


@router.get("")
async def list_attachments(
    submission_id: str,
    params: PaginationParams = Depends(),
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    attachment_service: AttachmentService = Depends(get_attachment_service),
) -> dict[str, object]:
    data, meta = await attachment_service.list_attachments(db, membership, submission_id, params)
    return paginated_response([item.model_dump(mode="json") for item in data], meta)


@router.post("")
async def create_attachment(
    submission_id: str,
    payload: AttachmentCreateRequest,
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
    attachment_service: AttachmentService = Depends(get_attachment_service),
) -> dict[str, object]:
    data = await attachment_service.create_attachment(
        db, membership, current_user, submission_id, payload
    )
    return success_response(data.model_dump(mode="json"))

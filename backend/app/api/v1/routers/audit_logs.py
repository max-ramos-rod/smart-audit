from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.responses import paginated_response
from app.db.models.memberships import Membership
from app.db.session import get_db
from app.modules.audit_logs.service import AuditLogService
from app.modules.memberships.permissions import get_admin_membership

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


def get_audit_log_service() -> AuditLogService:
    return AuditLogService()


@router.get("")
async def list_audit_logs(
    action: str | None = Query(default=None),
    params: PaginationParams = Depends(),
    membership: Membership = Depends(get_admin_membership),
    db: AsyncSession = Depends(get_db),
    service: AuditLogService = Depends(get_audit_log_service),
) -> dict[str, object]:
    data, meta = await service.list_logs(db, membership, params, action)
    return paginated_response([item.model_dump(mode="json") for item in data], meta)

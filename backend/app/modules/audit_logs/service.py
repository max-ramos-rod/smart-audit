from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageMeta, PaginationMetaBuilder, PaginationParams
from app.db.models.memberships import Membership
from app.modules.audit_logs.repository import AuditLogRepository
from app.modules.audit_logs.schemas import AuditLogResponse


class AuditLogService:
    def __init__(self, repository: AuditLogRepository | None = None) -> None:
        self.repository = repository or AuditLogRepository()

    async def list_logs(
        self,
        db: AsyncSession,
        membership: Membership,
        params: PaginationParams,
        action_filter: str | None = None,
    ) -> tuple[list[AuditLogResponse], PageMeta]:
        logs, total = await self.repository.list_by_company(
            db, str(membership.company_id), params, action_filter
        )
        meta = PaginationMetaBuilder.build(total, params)
        return [self._serialize(log) for log in logs], meta

    @staticmethod
    def _serialize(log) -> AuditLogResponse:
        return AuditLogResponse(
            id=str(log.id),
            company_id=str(log.company_id),
            actor_id=str(log.actor_id),
            target_user_id=str(log.target_user_id) if log.target_user_id else None,
            action=log.action,
            meta=log.meta,
            created_at=log.created_at.isoformat(),
        )

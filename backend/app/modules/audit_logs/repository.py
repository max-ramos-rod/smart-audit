from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.core.repositories import SQLAlchemyRepository
from app.db.models.audit_logs import AuditLog


class AuditLogRepository(SQLAlchemyRepository[AuditLog]):
    model = AuditLog

    async def log(
        self,
        db: AsyncSession,
        *,
        company_id: str,
        actor_id: str,
        action: str,
        target_user_id: str | None = None,
        meta: dict | None = None,
    ) -> None:
        entry = AuditLog(
            company_id=company_id,
            actor_id=actor_id,
            action=action,
            target_user_id=target_user_id,
            meta=meta,
        )
        await self._save(db, entry)

    async def list_by_company(
        self,
        db: AsyncSession,
        company_id: str,
        params: PaginationParams,
        action_filter: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        statement = (
            select(AuditLog)
            .where(AuditLog.company_id == company_id)
            .order_by(AuditLog.created_at.desc())
        )
        if action_filter:
            statement = statement.where(AuditLog.action == action_filter)
        return await self._paginate_select(db, statement, params)

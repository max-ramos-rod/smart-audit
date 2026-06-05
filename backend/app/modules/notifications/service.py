from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.memberships import Membership
from app.db.models.users import User
from app.modules.notifications.repository import NotificationReadRepository
from app.modules.submissions.schemas import NotificationItem
from app.modules.submissions.service import SubmissionService


class NotificationService:
    def __init__(
        self,
        repository: NotificationReadRepository | None = None,
        submission_service: SubmissionService | None = None,
    ) -> None:
        self.repository = repository or NotificationReadRepository()
        self.submission_service = submission_service or SubmissionService()

    async def list_notifications(
        self, db: AsyncSession, current_user: User, membership: Membership
    ) -> list[NotificationItem]:
        user_id = str(current_user.id)
        read_keys = await self.repository.get_read_keys(db, user_id)
        dismissed_keys = await self.repository.get_dismissed_keys(db, user_id)
        return await self.submission_service.get_notifications(
            db, membership, read_keys=read_keys, dismissed_keys=dismissed_keys
        )

    async def mark_read(self, db: AsyncSession, user_id: str, key: str) -> None:
        await self.repository.mark_read(db, user_id, key)
        await db.commit()

    async def mark_many_read(self, db: AsyncSession, user_id: str, keys: list[str]) -> int:
        await self.repository.mark_many_read(db, user_id, keys)
        await db.commit()
        return len(keys)

    async def dismiss(self, db: AsyncSession, user_id: str, key: str) -> None:
        await self.repository.dismiss(db, user_id, key)
        await db.commit()

    async def dismiss_many(self, db: AsyncSession, user_id: str, keys: list[str]) -> int:
        await self.repository.dismiss_many(db, user_id, keys)
        await db.commit()
        return len(keys)

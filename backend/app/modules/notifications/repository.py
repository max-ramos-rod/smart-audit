from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repositories import SQLAlchemyRepository
from app.db.models.notification_reads import NotificationRead


class NotificationReadRepository(SQLAlchemyRepository[NotificationRead]):
    model = NotificationRead

    async def get_read_keys(self, db: AsyncSession, user_id: str) -> set[str]:
        result = await db.scalars(
            select(NotificationRead.notification_key).where(
                NotificationRead.user_id == user_id,
                NotificationRead.dismissed.is_(False),
            )
        )
        return set(result.all())

    async def get_dismissed_keys(self, db: AsyncSession, user_id: str) -> set[str]:
        result = await db.scalars(
            select(NotificationRead.notification_key).where(
                NotificationRead.user_id == user_id,
                NotificationRead.dismissed.is_(True),
            )
        )
        return set(result.all())

    async def mark_read(self, db: AsyncSession, user_id: str, key: str) -> None:
        stmt = (
            insert(NotificationRead)
            .values(user_id=user_id, notification_key=key, dismissed=False)
            .on_conflict_do_nothing(constraint="uq_notification_reads_user_key")
        )
        await db.execute(stmt)

    async def mark_many_read(self, db: AsyncSession, user_id: str, keys: list[str]) -> None:
        if not keys:
            return
        stmt = (
            insert(NotificationRead)
            .values([{"user_id": user_id, "notification_key": k, "dismissed": False} for k in keys])
            .on_conflict_do_nothing(constraint="uq_notification_reads_user_key")
        )
        await db.execute(stmt)

    async def dismiss(self, db: AsyncSession, user_id: str, key: str) -> None:
        stmt = (
            insert(NotificationRead)
            .values(user_id=user_id, notification_key=key, dismissed=True)
            .on_conflict_do_update(
                constraint="uq_notification_reads_user_key",
                set_={"dismissed": True},
            )
        )
        await db.execute(stmt)

    async def dismiss_many(self, db: AsyncSession, user_id: str, keys: list[str]) -> None:
        if not keys:
            return
        for key in keys:
            await self.dismiss(db, user_id, key)

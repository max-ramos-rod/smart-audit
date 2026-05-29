from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import Base


class NotificationRead(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notification_reads"
    __table_args__ = (
        UniqueConstraint("user_id", "notification_key", name="uq_notification_reads_user_key"),
        Index("ix_notification_reads_user_id", "user_id"),
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    notification_key: Mapped[str] = mapped_column(String(100), nullable=False)

    user = relationship("User")
